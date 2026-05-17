from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from .text import clean_display_text, get_page_lines_from_html, slug_from_url



# No game-stat text is hardcoded here. Corrupted/Vaal pools are parsed from
# PoE2DB HTML in this order:
# 1) ModifiersCalc dropdown DOM, when the rendered control is present.
# 2) Embedded ModsView JSON, which is present in full PoE2DB subtype pages.
# 3) The static #VaalOrbCorruptedEnchantment DOM/text section as a reference.


def _canonical(text: str) -> str:
    text = clean_display_text(text).replace("-", "—")
    text = re.sub(r"\(([-+]?\d+)—([-+]?\d+)\)", r"(\1—\2)", text)
    return text


def _mod_from_text(text: str, *, source_group: str, tags: list[str] | None = None, keywords: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": "mod:" + re.sub(r"[^a-z0-9]+", "_", _canonical(text).lower()).strip("_"),
        "text": _canonical(text),
        "sourceGroup": source_group,
        "tags": tags or [],
        "keywords": keywords or [],
    }


def _text_without_tag(option: Tag) -> tuple[str, list[str], list[str]]:
    clone = BeautifulSoup(str(option), "html.parser")
    tags = [clean_display_text(t.get_text(" ", strip=True)) for t in clone.find_all(class_="poe2-tag")]
    keywords = [clean_display_text(t.get_text(" ", strip=True)) for t in clone.find_all(class_="poe2-keyword")]
    for tag in clone.find_all(class_="poe2-tag"):
        tag.decompose()
    text = clean_display_text(clone.get_text(" ", strip=True))
    return text, [t for t in tags if t], [k for k in keywords if k]


def parse_modifiers_calc_corrupted_dropdown(html: str, *, source_url: str, item_class: str, subtype: str) -> dict[str, Any] | None:
    """Parse the interactive ModifiersCalc select menu when it is present in the HTML.

    This is the planner-primary corruption pool because it matches the in-editor list
    users actually pick from. The static Vaal section remains a reference pool.
    """
    if "ui-Select-group" not in html or "poe2-modOption" not in html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    groups = [
        li for li in soup.find_all("li", class_="ui-Select-group")
        if "depth-0" in (li.get("class") or [])
    ]
    for group in groups:
        if clean_display_text(group.get_text(" ", strip=True)) != "Corrupted":
            continue
        mods: list[dict[str, Any]] = []
        for sibling in group.find_next_siblings("li"):
            classes = sibling.get("class") or []
            if "ui-Select-group" in classes:
                break
            if "ui-Select-option" not in classes:
                continue
            option = sibling.find(class_="poe2-modOption") or sibling
            text, tags, keywords = _text_without_tag(option)
            if text:
                mods.append(_mod_from_text(text, source_group="Corrupted", tags=tags, keywords=keywords))
        return {
            "id": f"poe2db:{slug_from_url(source_url)}:modifiers_calc:corrupted",
            "kind": "planner_corrupted_enchantment_pool",
            "sourceUrl": source_url + "#ModifiersCalc",
            "itemClass": item_class,
            "subtype": subtype,
            "sourceSection": "ModifiersCalc",
            "sourceGroup": "Corrupted",
            "plannerPrimary": True,
            "mods": mods,
        }
    return None


def _extract_modsview_data(html: str) -> dict[str, Any] | None:
    match = re.search(r"new\s+ModsView\((\{.*?\})\);", html, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _text_from_html_fragment(raw: Any, *, keep_values: bool) -> str:
    soup = BeautifulSoup(str(raw or ""), "html.parser")
    for badge in soup.find_all("span", class_="badge"):
        badge.decompose()
    for icon in soup.find_all(class_="fa-info-circle"):
        icon.decompose()
    if not keep_values:
        for value in soup.find_all("span", class_="mod-value"):
            value.string = "#"
    text = clean_display_text(soup.get_text(" ", strip=True))
    text = text.replace("# %", "#%")
    text = re.sub(r"\s+%", "%", text)
    return _canonical(text)


def _tags_from_modsview_row(row: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for raw in row.get("mod_no") or []:
        soup = BeautifulSoup(str(raw), "html.parser")
        for badge in soup.find_all("span", class_="badge"):
            label = clean_display_text(badge.get_text(" ", strip=True))
            if label and label not in tags:
                tags.append(label)
    return tags


def parse_modifiers_calc_corrupted_modsview_json(html: str, *, source_url: str, item_class: str, subtype: str) -> dict[str, Any] | None:
    """Parse planner-primary Corrupted options from PoE2DB's embedded ModsView JSON."""
    data = _extract_modsview_data(html)
    if not data:
        return None
    rows = data.get("corrupted") or []
    if not isinstance(rows, list):
        return None
    mods: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = _text_from_html_fragment(row.get("str"), keep_values=True)
        if not text:
            continue
        mods.append(_mod_from_text(text, source_group="Corrupted", tags=_tags_from_modsview_row(row)))
    if not mods:
        return None
    return {
        "id": f"poe2db:{slug_from_url(source_url)}:modifiers_calc:corrupted",
        "kind": "planner_corrupted_enchantment_pool",
        "sourceUrl": source_url + "#ModifiersCalc",
        "itemClass": item_class,
        "subtype": subtype,
        "sourceSection": "ModifiersCalc",
        "sourceGroup": "Corrupted",
        "plannerPrimary": True,
        "mods": mods,
    }


def _display_text_from_static_mod_title(mod_div: Tag) -> str:
    return _text_from_html_fragment(mod_div, keep_values=False)


def _display_text_from_static_modal(modal_by_id: dict[str, Tag], mod_div: Tag) -> str | None:
    target = clean_display_text(mod_div.get("data-bs-target")) or ""
    if not target.startswith("#"):
        return None
    modal = modal_by_id.get(target[1:])
    if modal is None:
        return None
    table = modal.find("table", class_="orig")
    row = table.find("tr") if table else modal.find("tr")
    if row is None:
        return None
    # The static modal contains a concrete value row. Its invalid nested table
    # markup makes td slicing brittle, so remove obvious non-stat cells/noise and
    # normalize the remaining text.
    clone = BeautifulSoup(str(row), "html.parser")
    for badge in clone.find_all("span", class_="badge"):
        badge.decompose()
    for icon in clone.find_all(class_="fa-info-circle"):
        icon.decompose()
    text = clean_display_text(clone.get_text(" ", strip=True))
    text = re.sub(r"^\d+\s*", "", text)
    text = re.sub(r"\s+\d+$", "", text)
    text = re.sub(r"\s+%", "%", text)
    return _canonical(text) if text else None


def _static_vaal_texts_from_dom(html: str) -> tuple[list[str], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    section = soup.find(id="VaalOrbCorruptedEnchantment")
    if section is None or not isinstance(section, Tag):
        return [], None
    header_tag = section.find("h5", class_="card-header")
    header = clean_display_text(header_tag.get_text(" ", strip=True)) if header_tag else None
    texts: list[str] = []
    modal_by_id = {str(modal.get("id")): modal for modal in soup.find_all("div", id=True, class_="modal")}
    for mod_div in section.find_all("div", class_="mod-title"):
        text = _display_text_from_static_modal(modal_by_id, mod_div) or _display_text_from_static_mod_title(mod_div)
        if text and text not in texts:
            texts.append(text)
    return texts, header


def _static_vaal_texts_from_plain_lines(html: str) -> tuple[list[str], str | None]:
    lines = get_page_lines_from_html(html)
    header_indices = [i for i, line in enumerate(lines) if "Vaal Orb Corrupted Enchantment" in line]
    if not header_indices:
        return [], None
    # Prefer the content heading over the nav-tab label when both are present in
    # plain-text fixtures.
    header_index = header_indices[-1]
    header = lines[header_index]
    texts: list[str] = []
    stop_markers = ("BaseItem", "Modifiers Calc")
    for raw in lines[header_index + 1:]:
        line = clean_display_text(raw)
        if not line:
            continue
        if line.startswith("#####"):
            line = clean_display_text(line.removeprefix("#####"))
            if "Vaal Orb Corrupted Enchantment" in line:
                continue
        if any(marker in line for marker in stop_markers) and "Vaal Orb Corrupted Enchantment" not in line:
            break
        if line in {"Close", "Item Level Local Weight", "Item Level Global Weight"}:
            continue
        if line.endswith("Total"):
            break
        # Fixture text rows look like:
        # "1 Damage Penetrates (10—15)% Fire Resistance Damage Elemental Fire 1".
        # Keep the actual stat text and remove leading ilvl, trailing weight, and
        # trailing tag words that are represented elsewhere in full DOM/JSON.
        line = re.sub(r"^\d+", "", line).strip()
        line = re.sub(r"\s+\d+$", "", line).strip()
        for suffix in (" Damage Elemental Lightning", " Damage Elemental Cold", " Damage Elemental Fire", " Attack"):
            if line.endswith(suffix):
                line = line[: -len(suffix)].strip()
        line = re.sub(r"(?<=\d)\+", " +", line)
        line = _canonical(line)
        if line and line not in texts and "Vaal Orb Corrupted Enchantment" not in line:
            texts.append(line)
    return texts, header


def parse_static_vaal_corrupted_reference(html: str, *, source_url: str, item_class: str, subtype: str) -> dict[str, Any]:
    """Parse the static Vaal Orb Corrupted Enchantment reference section from PoE2DB."""
    texts, header = _static_vaal_texts_from_dom(html)
    if not texts:
        texts, header = _static_vaal_texts_from_plain_lines(html)
    return {
        "id": f"poe2db:{slug_from_url(source_url)}:section:vaal_orb_corrupted_enchantment",
        "kind": "reference_vaal_orb_corrupted_enchantment",
        "sourceUrl": source_url + "#VaalOrbCorruptedEnchantment",
        "itemClass": item_class,
        "subtype": subtype,
        "sourceSection": header or f"Vaal Orb Corrupted Enchantment /{len(texts)}",
        "sourceGroup": "Vaal Orb Corrupted Enchantment",
        "plannerPrimary": False,
        "mods": [_mod_from_text(text, source_group="Vaal Orb Corrupted Enchantment") for text in texts],
    }


def compare_mod_pools(primary: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    primary_texts = {m["text"] for m in primary.get("mods", [])}
    reference_texts = {m["text"] for m in reference.get("mods", [])}
    extra = sorted(primary_texts - reference_texts)
    missing = sorted(reference_texts - primary_texts)
    if extra and not missing:
        status = "primary_superset"
    elif not extra and not missing:
        status = "same"
    else:
        status = "differs"
    return {
        "primary": primary["id"],
        "reference": reference["id"],
        "status": status,
        "extraInPrimary": extra,
        "missingFromPrimary": missing,
    }


