from __future__ import annotations

from pathlib import Path

import pytest
import requests

from poe2db_scraper.fetcher import FetchClient, FetchPolicy, cache_path_for_url, fetch_many_html
from poe2db_scraper.utils import ordered_unique_strings


class FakeResponse:
    def __init__(self, status_code: int, text: str = "ok") -> None:
        self.status_code = status_code
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[str] = []
        self.closed = False

    def get(self, url: str, *, headers: dict[str, str], timeout: float) -> FakeResponse:
        self.calls.append(url)
        if not self.responses:
            raise requests.ConnectionError("no fake response")
        return self.responses.pop(0)

    def close(self) -> None:
        self.closed = True


def test_ordered_unique_strings_preserves_first_seen_order() -> None:
    assert ordered_unique_strings([" a ", "b", "a", "", None, "c", "b"]) == ["a", "b", "c"]


def test_fetch_client_retries_retryable_status_with_shared_session(tmp_path: Path) -> None:
    session = FakeSession([FakeResponse(503, "temporary"), FakeResponse(200, "fresh")])
    client = FetchClient(
        session=session,  # type: ignore[arg-type]
        policy=FetchPolicy(delay_seconds=0, backoff_seconds=0, max_retries=1),
    )

    fetched = client.fetch_html("https://example.test/page", cache_dir=tmp_path, force_refresh=True)

    assert fetched.html == "fresh"
    assert fetched.status_code == 200
    assert fetched.attempts == 2
    assert session.calls == ["https://example.test/page", "https://example.test/page"]
    assert any("HTTP 503" in warning for warning in fetched.warnings)


def test_fetch_client_can_disable_stale_cache_fallback(tmp_path: Path) -> None:
    session = FakeSession([FakeResponse(503, "temporary")])
    client = FetchClient(
        session=session,  # type: ignore[arg-type]
        policy=FetchPolicy(delay_seconds=0, backoff_seconds=0, max_retries=0, allow_stale_cache_on_error=False),
    )
    cache_path_for_url("https://example.test/page", tmp_path).write_text("stale", encoding="utf-8")

    with pytest.raises(RuntimeError, match="stale cache fallback is disabled"):
        client.fetch_html("https://example.test/page", cache_dir=tmp_path, force_refresh=True)


def test_fetch_many_html_deduplicates_urls_and_preserves_order(tmp_path: Path) -> None:
    session = FakeSession([FakeResponse(200, "a"), FakeResponse(200, "b")])
    results = fetch_many_html(
        ["https://example.test/a", "https://example.test/a", "https://example.test/b"],
        cache_dir=tmp_path,
        delay_seconds=0,
        max_workers=1,
        session=session,  # type: ignore[arg-type]
    )

    assert list(results) == ["https://example.test/a", "https://example.test/b"]
    assert [page.html for page in results.values()] == ["a", "b"]
    assert session.closed is False
