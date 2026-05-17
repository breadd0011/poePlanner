from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup, Tag

from .normalize import parse_int_range, parse_requirement_line
from .text import clean_display_text, slug_from_url
from .unique_gloves_parser import normalize_poe2db_item_url, stable_slug

DEFENCE_PROPERTY_LABELS = {
    "Armour": "armour",
    "Evasion": "evasion",
    "Evasion Rating": "evasion",
    "Energy Shield": "energyShield",
}
WEAPON_PROPERTY_LABELS = {
    "Physical Damage": "physicalDamage",
    "Critical Hit Chance": "criticalHitChance",
    "Attacks per Second": "attacksPerSecond",
    "Weapon Range": "weaponRange",
}
SKIP_NAME_MARKERS = ("[DNT-", "DNT-", "DNT-UNUSED")


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _compact_class_id(item_class: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", item_class)


def _node_text(node: Tag | None) -> str:
    return clean_display_text(node.get_text(" ", strip=True)) if node is not None else ""


def _item_pane(soup: BeautifulSoup, item_class: str) -> Tag | None:
    compact = _compact_class_id(item_class)
    for selector in (f"#{compact}Item", f"#{compact}Items"):
        pane = soup.select_one(selector)
        if isinstance(pane, Tag):
            return pane
    for pattern in (rf"{re.escape(item_class)}\s+Item\s*/\d+", r"\bItem\s*/\d+"):
        heading = soup.find(string=re.compile(pattern, re.I))
        current = heading.parent if heading and isinstance(heading.parent, Tag) else None
        while current is not None:
            if current.select("a.whiteitem[href]"):
                return current
            current = current.parent if isinstance(current.parent, Tag) else None
    return None


def _item_rows(pane: Tag) -> list[Tag]:
    rows: list[Tag] = []
    seen_ids: set[int] = set()
    for anchor in pane.select("a.whiteitem[href]"):
        if not _node_text(anchor):
            continue
        row = anchor.find_parent("div", class_="d-flex")
        if not isinstance(row, Tag):
            continue
        row_id = id(row)
        if row_id in seen_ids:
            continue
        seen_ids.add(row_id)
        rows.append(row)
    return rows


def _row_name_anchor(row: Tag) -> Tag | None:
    anchors = [anchor for anchor in row.select("a.whiteitem[href]") if _node_text(anchor)]
    return anchors[-1] if anchors else None


def _icon_from_row(row: Tag) -> str | None:
    img = row.select_one("img[src]")
    src = str(img.get("src") or "") if isinstance(img, Tag) else ""
    if not src:
        return None
    path = unquote(urlparse(src).path)
    if "/image/" in path:
        asset = path.split("/image/", 1)[1]
        asset = re.sub(r"\.(webp|png|jpg|jpeg)$", "", asset, flags=re.I)
        if asset.startswith("Art/"):
            return asset
    return src


def _lines(row: Tag, selector: str) -> list[str]:
    out: list[str] = []
    for node in row.select(selector):
        text = _node_text(node)
        if text and text not in out:
            out.append(text)
    return out


def _property_key(line: str) -> tuple[str, str] | None:
    text = clean_display_text(line)
    if ":" not in text:
        return None
    raw_label, raw_value = text.split(":", 1)
    label = clean_display_text(raw_label)
    value = clean_display_text(raw_value)
    if not label or not value:
        return None
    return label, value


def _parse_defences(property_lines: list[str]) -> dict[str, int]:
    defences: dict[str, int] = {}
    for line in property_lines:
        parsed = _property_key(line)
        if not parsed:
            continue
        label, value = parsed
        key = DEFENCE_PROPERTY_LABELS.get(label)
        if not key:
            continue
        value_range = parse_int_range(value)
        if value_range:
            parsed_value = value_range.get("max") if value_range.get("max") is not None else value_range.get("min")
            if parsed_value is not None:
                defences[key] = int(parsed_value)
    return defences


def _parse_properties(property_lines: list[str]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    for line in property_lines:
        parsed = _property_key(line)
        if not parsed:
            continue
        label, value = parsed
        if label in DEFENCE_PROPERTY_LABELS:
            continue
        key = WEAPON_PROPERTY_LABELS.get(label) or stable_slug(label)
        if label == "Physical Damage":
            properties[key] = parse_int_range(value) or value
        elif label == "Critical Hit Chance" and (match := re.search(r"([\d.]+)%", value)):
            properties[key] = float(match.group(1))
        elif label in {"Attacks per Second", "Weapon Range"} and (match := re.search(r"([\d.]+)", value)):
            properties[key] = float(match.group(1))
        elif (match := re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value)):
            parsed_number = float(match.group(0))
            properties[key] = int(parsed_number) if parsed_number.is_integer() else parsed_number
        else:
            properties[key] = value
    return properties


def _base_item_from_row(source_url: str, row: Tag, *, item_class: str) -> dict[str, Any] | None:
    name_anchor = _row_name_anchor(row)
    name = _node_text(name_anchor)
    if not name or any(marker in name for marker in SKIP_NAME_MARKERS) or " per level" in name:
        return None
    href = str(name_anchor.get("href") or "") if isinstance(name_anchor, Tag) else ""
    item_url = normalize_poe2db_item_url(source_url, href) or source_url
    slug = slug_from_url(item_url) or stable_slug(name)
    property_lines = _lines(row, ".property")
    requirement_line = next(iter(_lines(row, ".requirements")), None)
    implicit_mods = [
        {"id": f"poe2db:base:{stable_slug(item_class)}:{stable_slug(name)}:implicit:{index}", "text": text}
        for index, text in enumerate(_lines(row, ".implicitMod"))
    ]
    diagnostics: list[dict[str, Any]] = []
    if not item_url or item_url == source_url:
        diagnostics.append({
            "severity": "warning",
            "code": "BASE_ITEM_SOURCE_URL_FALLBACK",
            "message": "Could not normalize the base item detail URL from the class catalogue row.",
            "actionRequired": False,
        })
    return {
        "id": f"poe2db:base:{stable_slug(item_class)}:{stable_slug(name)}",
        "slug": slug,
        "source": "poe2db",
        "sourceUrl": item_url,
        "kind": "base_item",
        "itemClass": item_class,
        "name": name,
        "icon": _icon_from_row(row),
        "requirements": parse_requirement_line(requirement_line),
        "defences": _parse_defences(property_lines),
        "properties": _parse_properties(property_lines),
        "propertyLines": property_lines,
        "implicitMods": implicit_mods,
        "parseStatus": "warning" if diagnostics else "ok",
        "warnings": [],
        "diagnostics": diagnostics,
    }


def parse_base_items_from_class_page(source_url: str, html: str, *, item_class: str) -> list[dict[str, Any]]:
    """Parse the generic PoE2DB class-page Item catalogue into top-level base items."""
    soup = _soup(html)
    pane = _item_pane(soup, item_class)
    if not isinstance(pane, Tag):
        return []
    def score(item: dict[str, Any]) -> int:
        return (
            len(item.get("propertyLines") or []) * 4
            + len(item.get("implicitMods") or []) * 3
            + sum(1 for value in (item.get("requirements") or {}).values() if value is not None) * 2
            + (1 if item.get("icon") else 0)
        )

    by_id: dict[str, dict[str, Any]] = {}
    for row in _item_rows(pane):
        item = _base_item_from_row(source_url, row, item_class=item_class)
        if item is None:
            continue
        key = str(item["id"])
        current = by_id.get(key)
        if current is None or score(item) > score(current):
            by_id[key] = item
    return sorted(by_id.values(), key=lambda item: str(item.get("name") or ""))


def base_item_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name") or "",
        "requirements": dict(item.get("requirements") or {}),
        "defences": dict(item.get("defences") or {}),
        "implicitMods": list(item.get("implicitMods") or []),
        "icon": item.get("icon"),
        "properties": dict(item.get("properties") or {}),
        "propertyLines": list(item.get("propertyLines") or []),
        "sourceUrl": item.get("sourceUrl"),
        "itemClass": item.get("itemClass"),
    }
