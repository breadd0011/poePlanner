from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from .mod_parser import parse_mod_blocks
from .object_parser import parse_object_data
from .normalize import entity_id, normalized_item_fields, slug
from .text import (
    clean_display_text,
    extract_trade_json_if_present,
    get_page_lines_from_html,
    node_lines,
    node_text,
    slice_tooltip_lines,
    title_from_url,
)

ITEM_CLASS_FROM_URL_FALLBACK = {
    "Treefingers": "Gloves",
    "Crude_Claw": "Claws",
}


def _find_popup(soup: BeautifulSoup, expected_name: str | None = None) -> Tag | None:
    popups = soup.select(".newItemPopup")
    if not popups:
        return None
    if expected_name:
        for popup in popups:
            texts = [node_text(node) for node in popup.select(".itemHeader .itemName")]
            if expected_name in texts:
                return popup
    return popups[0]


def _title_lines_from_popup(popup: Tag | None) -> list[str]:
    if popup is None:
        return []
    lines: list[str] = []
    for node in popup.select(".itemHeader .itemName"):
        text = node_text(node)
        if text and text not in lines:
            lines.append(text)
    return lines


def _direct_stat_divs(stats: Tag | None, class_name: str) -> list[Tag]:
    if stats is None:
        return []
    return [node for node in stats.find_all("div", class_=class_name, recursive=False)]


def _tooltip_sections_from_popup(popup: Tag | None, *, name: str, base_type: str | None) -> list[dict[str, Any]]:
    if popup is None:
        title_lines = [name]
        if base_type and base_type != name:
            title_lines.append(base_type)
        return [{"kind": "title", "lines": title_lines}]

    title_lines = _title_lines_from_popup(popup) or [name]
    stats = popup.select_one(".Stats")
    property_lines = [node_text(node) for node in _direct_stat_divs(stats, "property")]
    requirement_lines = [node_text(node) for node in _direct_stat_divs(stats, "requirements")]
    explicit_lines = [node_text(node) for node in _direct_stat_divs(stats, "explicitMod")]

    flavour_lines: list[str] = []
    flavour = stats.find("div", class_="FlavourText", recursive=False) if stats else None
    if flavour is not None:
        flavour_lines = node_lines(flavour)

    sections: list[dict[str, Any]] = [{"kind": "title", "lines": [line for line in title_lines if line]}]
    if property_lines:
        sections.append({"kind": "property", "lines": [line for line in property_lines if line]})
    if requirement_lines:
        sections.append({"kind": "requirement", "lines": [line for line in requirement_lines if line]})
    if explicit_lines:
        sections.append({"kind": "explicit", "lines": [line for line in explicit_lines if line]})
    if flavour_lines:
        sections.append({"kind": "flavour", "lines": flavour_lines})
    return sections


def _property_lines(sections: list[dict[str, Any]]) -> list[str]:
    for section in sections:
        if section.get("kind") == "property":
            return list(section.get("lines") or [])
    return []


def _infer_item_class(
    *,
    object_data: dict[str, Any],
    sections: list[dict[str, Any]],
    trade_json: dict[str, Any] | None,
    source_url: str,
) -> str | None:
    if object_data.get("class"):
        return str(object_data["class"])

    for line in _property_lines(sections):
        if ":" not in line and not line.startswith("Stack Size"):
            return line

    if trade_json:
        props = trade_json.get("properties") or []
        if props and isinstance(props[0], dict) and props[0].get("name"):
            return clean_display_text(props[0].get("name"))

    slug = source_url.rstrip("/").split("/")[-1]
    return ITEM_CLASS_FROM_URL_FALLBACK.get(slug)


def _infer_rarity(trade_json: dict[str, Any] | None, popup: Tag | None, mods: list[dict[str, Any]]) -> str | None:
    if trade_json and trade_json.get("rarity"):
        return str(trade_json["rarity"])
    if popup is not None and "uniquePopup" in (popup.get("class") or []):
        return "Unique"
    if any("Unique" in str(mod.get("generationType") or "") for mod in mods):
        return "Unique"
    return None


def _fallback_name(
    *,
    tooltip_title: list[str],
    trade_json: dict[str, Any] | None,
    object_data: dict[str, Any],
    source_url: str,
) -> str:
    if tooltip_title and tooltip_title[0]:
        return tooltip_title[0]
    if trade_json and trade_json.get("name"):
        return clean_display_text(trade_json.get("name"))
    if object_data.get("baseType"):
        return str(object_data["baseType"])
    return title_from_url(source_url)


def _fallback_base_type(
    *,
    name: str,
    tooltip_title: list[str],
    trade_json: dict[str, Any] | None,
    object_data: dict[str, Any],
) -> str | None:
    if object_data.get("baseType"):
        return str(object_data["baseType"])
    if trade_json:
        base = trade_json.get("baseType") or trade_json.get("typeLine")
        if base:
            return clean_display_text(base)
    if len(tooltip_title) >= 2:
        return tooltip_title[1]
    return name


def parse_item_page(source_url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    trade_json = extract_trade_json_if_present(html)
    object_data, _object_data_raw = parse_object_data(soup)
    popup = _find_popup(soup)
    tooltip_title = _title_lines_from_popup(popup)

    name = _fallback_name(
        tooltip_title=tooltip_title,
        trade_json=trade_json,
        object_data=object_data,
        source_url=source_url,
    )
    base_type = _fallback_base_type(
        name=name,
        tooltip_title=tooltip_title,
        trade_json=trade_json,
        object_data=object_data,
    )
    sections = _tooltip_sections_from_popup(popup, name=name, base_type=base_type)
    if trade_json and not any(section.get("kind") == "flavour" for section in sections):
        trade_flavour = [clean_display_text(line) for line in trade_json.get("flavourText") or [] if clean_display_text(line)]
        if trade_flavour:
            sections.append({"kind": "flavour", "lines": trade_flavour})
    mods = parse_mod_blocks(soup)
    item_class = _infer_item_class(
        object_data=object_data,
        sections=sections,
        trade_json=trade_json,
        source_url=source_url,
    )

    frame_type = trade_json.get("frameType") if trade_json else None
    rarity = _infer_rarity(trade_json, popup, mods)

    # Text-slice fallback is intentionally secondary. It keeps the POC useful if the
    # PoE2DB tooltip classes change, but structured DOM parsing is cleaner today.
    if not any(section.get("kind") == "property" for section in sections):
        fallback_lines = slice_tooltip_lines(get_page_lines_from_html(html), name)
        if len(fallback_lines) > 1:
            sections.append({"kind": "property", "lines": fallback_lines[1:]})

    return {
        "id": entity_id(source_url),
        "slug": slug(source_url),
        "sourceUrl": source_url,
        "source": "poe2db",
        "kind": "item",
        "name": name,
        "baseType": base_type,
        "itemClass": item_class,
        "rarity": rarity,
        "icon": object_data.get("icon") or (trade_json.get("icon") if trade_json else None),
        "frameType": frame_type,
        "tooltipSections": sections,
        "mods": mods,
        "objectData": object_data,
        "normalized": normalized_item_fields(sections, object_data),
        "parseStatus": "ok",
        "warnings": [],
    }
