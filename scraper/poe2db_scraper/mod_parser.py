from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from .text import clean_display_text, clean_stat_text, to_int

NON_MOD_TITLE_PARTS = (
    "Attr /",
    "Version history",
    "Forge Recipe",
    "Forge recipe",
    "Recipe /",
    "Sites",
    "News",
    "About Site",
    "Community",
)


def parse_internal_stat_line(line: str) -> dict[str, Any]:
    raw = clean_stat_text(line)
    body = raw
    scope: str | None = None
    for known_scope in ("Global", "Local"):
        suffix = f" {known_scope}"
        if body.endswith(suffix):
            scope = known_scope
            body = body[: -len(suffix)].strip()
            break

    match = re.match(r"(.+?)\s+(-?\d+)\s+—\s+(-?\d+)$", body)
    if match:
        return {
            "id": match.group(1).strip(),
            "min": int(match.group(2)),
            "max": int(match.group(3)),
            "scope": scope,
            "raw": raw,
        }

    return {"id": body, "min": None, "max": None, "scope": scope, "raw": raw}


def _row_label_and_cell(row: Tag) -> tuple[str, Tag] | None:
    th = row.find("th")
    td = row.find("td")
    if th is None or td is None:
        return None
    label = clean_display_text(th.get_text(" ", strip=True))
    if not label:
        return None
    return label, td


def _table_row_map(table: Tag) -> dict[str, Tag]:
    rows: dict[str, Tag] = {}
    for row in table.find_all("tr"):
        parsed = _row_label_and_cell(row)
        if parsed is None:
            continue
        label, cell = parsed
        rows[label] = cell
    return rows


def collect_mod_blocks_raw(soup: BeautifulSoup) -> list[dict[str, Any]]:
    raw_blocks: list[dict[str, Any]] = []

    for header in soup.select("h5.card-header"):
        title = clean_display_text(header.get_text(" ", strip=True))
        if not title or any(part in title for part in NON_MOD_TITLE_PARTS):
            continue
        card = header.find_parent("div", class_="card")
        table = card.find("table") if card else header.find_next("table")
        if table is None:
            continue
        row_map = _table_row_map(table)
        if "Family" not in row_map:
            continue

        raw_row_map: dict[str, Any] = {}
        for label, cell in row_map.items():
            if label == "Stats":
                raw_row_map[label] = [clean_stat_text(li.get_text(" ", strip=True)) for li in cell.find_all("li")]
            elif label == "Craft Tags":
                badges = [clean_display_text(badge.get_text(" ", strip=True)) for badge in cell.select(".badge")]
                raw_row_map[label] = [badge for badge in badges if badge]
            else:
                raw_row_map[label] = clean_display_text(cell.get_text(" ", strip=True))
        raw_blocks.append({"title": title, "rows": raw_row_map})

    return raw_blocks


def parse_mod_blocks(soup: BeautifulSoup) -> list[dict[str, Any]]:
    mods: list[dict[str, Any]] = []
    for block in collect_mod_blocks_raw(soup):
        rows = block["rows"]
        stats = [parse_internal_stat_line(line) for line in rows.get("Stats", [])]
        raw_req_level = rows.get("Req. level")
        req_level = to_int(raw_req_level) if raw_req_level is not None else None
        craft_tags = rows.get("Craft Tags", [])
        if isinstance(craft_tags, str):
            craft_tags = craft_tags.split()

        mods.append(
            {
                "text": block["title"],
                "family": rows.get("Family"),
                "domains": rows.get("Domains"),
                "generationType": rows.get("GenerationType"),
                "requiredLevel": req_level,
                "stats": stats,
                "craftTags": craft_tags,
            }
        )
    return mods
