"""Archived legacy static Boots data.

The production pipeline now parses Boots/base/modifier data from PoE2DB class,
subtype and ModifiersCalc sources. This module intentionally no longer exports
static game data, so new scraper work cannot accidentally reintroduce checked-in
Boots fixtures as runtime truth.

Historical context is kept in docs/HARD_CODED_DATA_AUDIT.md and older repository
revisions. Do not add new consumers to this module.
"""

from __future__ import annotations

__all__: list[str] = []
