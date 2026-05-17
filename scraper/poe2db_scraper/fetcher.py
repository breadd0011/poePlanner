from __future__ import annotations

import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import requests

HEADERS = {
    "User-Agent": "poe2-planner-data-poc/0.8 (+https://local.dev; respectful-cache-poc; contact: local)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchPolicy:
    """HTTP/cache policy shared by single and batch fetches."""

    delay_seconds: float = 0.75
    timeout_seconds: float = 20.0
    max_retries: int = 2
    backoff_seconds: float = 1.0
    allow_stale_cache_on_error: bool = True


@dataclass(frozen=True)
class FetchedPage:
    url: str
    html: str
    cache_path: Path
    from_cache: bool
    attempts: int = 0
    status_code: int | None = None
    warnings: list[str] = field(default_factory=list)
    elapsed_seconds: float | None = None


def cache_path_for_url(url: str, cache_dir: Path) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir / f"{digest}.html"


class FetchClient:
    """Small session-backed PoE2DB fetch client.

    The old module-level function remains as a compatibility wrapper, but this
    class is the preferred surface for future batch/parallel scraper flows. A
    single requests.Session keeps connection pooling and retry logging in one
    place instead of scattering direct requests.get calls through builders.
    """

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        policy: FetchPolicy | None = None,
        headers: dict[str, str] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.policy = policy or FetchPolicy()
        self.headers = dict(headers or HEADERS)
        self.logger = logger or LOGGER

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "FetchClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def fetch_html(
        self,
        url: str,
        *,
        cache_dir: Path,
        force_refresh: bool = False,
    ) -> FetchedPage:
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_path_for_url(url, cache_dir)
        started_at = time.monotonic()

        if path.exists() and not force_refresh:
            self.logger.debug("Using cached PoE2DB page", extra={"url": url, "cache_path": str(path)})
            return FetchedPage(
                url=url,
                html=path.read_text(encoding="utf-8"),
                cache_path=path,
                from_cache=True,
                elapsed_seconds=round(time.monotonic() - started_at, 6),
            )

        warnings: list[str] = []
        last_error: Exception | None = None
        last_status: int | None = None
        total_attempts = max(self.policy.max_retries, 0) + 1

        for attempt in range(1, total_attempts + 1):
            try:
                response = self.session.get(url, headers=self.headers, timeout=self.policy.timeout_seconds)
                last_status = response.status_code
                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt < total_attempts:
                        warning = f"HTTP {response.status_code} on attempt {attempt}; retrying"
                        warnings.append(warning)
                        self.logger.warning(warning, extra={"url": url, "attempt": attempt, "status_code": response.status_code})
                        time.sleep(self.policy.backoff_seconds * attempt)
                        continue
                    warnings.append(f"HTTP {response.status_code} on final attempt; no retries left")
                response.raise_for_status()
                html = response.text
                path.write_text(html, encoding="utf-8")
                time.sleep(self.policy.delay_seconds)
                return FetchedPage(
                    url=url,
                    html=html,
                    cache_path=path,
                    from_cache=False,
                    attempts=attempt,
                    status_code=response.status_code,
                    warnings=warnings,
                    elapsed_seconds=round(time.monotonic() - started_at, 6),
                )
            except requests.RequestException as exc:
                last_error = exc
                if attempt < total_attempts:
                    warning = f"Request error on attempt {attempt}: {exc}; retrying"
                    warnings.append(warning)
                    self.logger.warning(warning, extra={"url": url, "attempt": attempt})
                    time.sleep(self.policy.backoff_seconds * attempt)
                    continue
                break

        if path.exists() and self.policy.allow_stale_cache_on_error:
            warning = f"Live fetch failed; using stale cache for {url}"
            warnings.append(warning)
            self.logger.warning(warning, extra={"url": url, "status_code": last_status})
            return FetchedPage(
                url=url,
                html=path.read_text(encoding="utf-8"),
                cache_path=path,
                from_cache=True,
                attempts=total_attempts,
                status_code=last_status,
                warnings=warnings,
                elapsed_seconds=round(time.monotonic() - started_at, 6),
            )

        if path.exists():
            reason = last_error or f"HTTP {last_status}"
            raise RuntimeError(f"Failed to fetch {url}; stale cache fallback is disabled: {reason}") from last_error

        if last_error is not None:
            raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error
        raise RuntimeError(f"Failed to fetch {url}: HTTP {last_status}")

    def fetch_many_html(
        self,
        urls: Iterable[str],
        *,
        cache_dir: Path,
        force_refresh: bool = False,
        max_workers: int = 1,
    ) -> dict[str, FetchedPage]:
        """Fetch URLs with a shared session and deterministic result ordering.

        max_workers defaults to 1 to preserve the scraper's respectful fetch
        cadence. Callers can opt into a small worker count for fixture refreshes
        once they have considered rate limits.
        """
        ordered_urls: list[str] = []
        seen_urls: set[str] = set()
        for url in urls:
            if url is None:
                continue
            text = str(url).strip()
            if not text or text in seen_urls:
                continue
            seen_urls.add(text)
            ordered_urls.append(text)
        if max_workers <= 1 or len(ordered_urls) <= 1:
            return {url: self.fetch_html(url, cache_dir=cache_dir, force_refresh=force_refresh) for url in ordered_urls}

        results: dict[str, FetchedPage] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_by_url = {
                url: executor.submit(self.fetch_html, url, cache_dir=cache_dir, force_refresh=force_refresh)
                for url in ordered_urls
            }
            for url in ordered_urls:
                results[url] = future_by_url[url].result()
        return results


def fetch_html(
    url: str,
    *,
    cache_dir: Path,
    force_refresh: bool = False,
    delay_seconds: float = 0.75,
    timeout_seconds: float = 20.0,
    max_retries: int = 2,
    backoff_seconds: float = 1.0,
    allow_stale_cache_on_error: bool = True,
    session: requests.Session | None = None,
) -> FetchedPage:
    policy = FetchPolicy(
        delay_seconds=delay_seconds,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
        allow_stale_cache_on_error=allow_stale_cache_on_error,
    )
    client = FetchClient(session=session, policy=policy)
    try:
        return client.fetch_html(url, cache_dir=cache_dir, force_refresh=force_refresh)
    finally:
        if session is None:
            client.close()


def fetch_many_html(
    urls: Iterable[str],
    *,
    cache_dir: Path,
    force_refresh: bool = False,
    delay_seconds: float = 0.75,
    timeout_seconds: float = 20.0,
    max_retries: int = 2,
    backoff_seconds: float = 1.0,
    allow_stale_cache_on_error: bool = True,
    max_workers: int = 1,
    session: requests.Session | None = None,
) -> dict[str, FetchedPage]:
    policy = FetchPolicy(
        delay_seconds=delay_seconds,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
        allow_stale_cache_on_error=allow_stale_cache_on_error,
    )
    client = FetchClient(session=session, policy=policy)
    try:
        return client.fetch_many_html(urls, cache_dir=cache_dir, force_refresh=force_refresh, max_workers=max_workers)
    finally:
        if session is None:
            client.close()
