from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def ordered_unique_strings(values: Iterable[Any], *, strip: bool = True) -> list[str]:
    """Return non-empty strings deduplicated in first-seen order.

    This is intentionally tiny, but centralising it prevents repeated O(n)
    membership checks across payload assembly code and keeps the JSON contract
    stable: source URL ordering remains deterministic while duplicates are
    dropped with set-like performance.
    """
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if strip:
            text = text.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
