from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from .augment_classification import classify_augment_name
from .mod_tag_config import COMPOUND_TAG_TOKENS, TAG_TEXT_BY_DATA_TAG, TAG_TOKENS
from .text import clean_display_text

SECTION_HEADINGS = {
    "Base Prefix": "base_prefix",
    "Base Suffix": "base_suffix",
    "desecratedsymbolDesecrated Modifiers Prefix": "desecrated_prefix",
    "desecratedsymbolDesecrated Modifiers Suffix": "desecrated_suffix",
    "EssenceEssence Prefix": "essence_prefix",
    "EssenceEssence Suffix": "essence_suffix",
    "EssencePerfect Essence Prefix": "perfect_essence_prefix",
    "EssencePerfect Essence Suffix": "perfect_essence_suffix",
    "FireRuneAugment": "augment",
    "ShamanRunesTalismansBonded Modifiers": "bonded",
    "CurrencyVaalCorrupted": "vaal_corrupted",
}

# Plain-text snapshot tag fallback config lives in mod_tag_config.py.

SECTION_LABELS = {
    "base_prefix": "Base Prefix",
    "base_suffix": "Base Suffix",
}


def split_snapshot_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = clean_display_text(raw)
        if not line:
            continue
        if line in SECTION_HEADINGS:
            current = SECTION_HEADINGS[line]
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def _strip_leading_weight(line: str) -> tuple[str | None, str]:
    match = re.match(r"^(\d+)(.*)$", line)
    if not match:
        return None, line.strip()
    weight, rest = match.groups()
    return weight, rest.strip()


def _expand_tag_token(token: str) -> list[str]:
    if token in COMPOUND_TAG_TOKENS:
        return COMPOUND_TAG_TOKENS[token]
    return [token]


def _split_tags(rest: str) -> tuple[str, list[str]]:
    working = rest.strip()
    for token in TAG_TOKENS:
        if working.endswith(token):
            text = working[: -len(token)].strip()
            return clean_display_text(text), _expand_tag_token(token)
    return clean_display_text(working), []


def _normalize_mod_text(text: str) -> str:
    text = clean_display_text(text)
    # PoE2DB sometimes renders multi-line affixes in one inline span, e.g.
    # "# to Armour# to Evasion Rating" or
    # "#% increased Armour and Evasion# to maximum Life". Keep it as one
    # selectable family-level affix, but make the display readable.
    text = re.sub(r"(?<=[A-Za-z])(?=#(?:%| to ))", " / ", text)
    text = text.replace("Fire damage", "Fire Damage")
    text = text.replace("Cold damage", "Cold Damage")
    text = text.replace("Lightning damage", "Lightning Damage")
    text = text.replace("enemy", "Enemy") if text.startswith("Gain # Life per enemy") else text
    return text


def _family_from_generation_group(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"^\d+", "", value).strip() or value


def _affix_id(item_class: str, subtype: str, affix_type: str, index: int, text: str, family: str | None = None) -> str:
    base = family or text
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return f"poe2db:{item_class.lower()}:{subtype}:normal_explicit:{affix_type}:{index}:{slug}"


def parse_snapshot_mods(lines: list[str], *, group_key: str, source_url: str, item_class: str, subtype: str, affix_type: str) -> list[dict[str, Any]]:
    mods: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if line.endswith("Total"):
            continue
        weight, rest = _strip_leading_weight(line)
        if not rest:
            continue
        text, tags = _split_tags(rest)
        text = _normalize_mod_text(text)
        if not text or text == "Total":
            continue
        if text in TAG_TOKENS:
            continue
        mods.append({
            "id": _affix_id(item_class, subtype, affix_type, index, text),
            "text": text,
            "textTemplate": text,
            "displayRangeText": None,
            "editableValues": [],
            "affixType": affix_type,
            "sourceGroup": SECTION_LABELS.get(group_key, group_key),
            "family": None,
            "generationGroup": None,
            "weightRaw": weight,
            "weightPercent": None,
            "level": None,
            "tierCount": None,
            "detailStatus": "not_available_from_snapshot",
            "tags": tags,
            "keywords": [],
            "sourceUrl": source_url,
        })
    return mods


def _content_span(mod_div):
    for child in mod_div.find_all("span", recursive=False):
        classes = child.get("class") or []
        if "float-end" not in classes:
            return child
    return None



def _parse_number(raw: str) -> int | float:
    value = float(raw)
    return int(value) if value.is_integer() else value


def _format_number(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return f"{value:g}"


def _parse_mod_value_range(value_text: str) -> dict[str, Any] | None:
    value_text = clean_display_text(value_text).replace("-", "—")
    number = r"-?\d+(?:\.\d+)?"
    match = re.search(rf"([+\-]?)\(?\s*({number})\s*—\s*({number})\s*\)?", value_text)
    if not match:
        single = re.search(rf"([+\-]?)\(?\s*({number})\s*\)?", value_text)
        if not single:
            return None
        sign, raw = single.groups()
        low = high = _parse_number(raw)
    else:
        sign, raw_min, raw_max = match.groups()
        low, high = _parse_number(raw_min), _parse_number(raw_max)
    if low > high:
        low, high = high, low
    return {"sign": sign or "", "min": low, "max": high}


def _range_text(sign: str, low: int | float | None, high: int | float | None) -> str | None:
    if low is None or high is None:
        return None
    if low == high:
        return f"{sign}{_format_number(low)}"
    return f"{sign}({_format_number(low)}—{_format_number(high)})"


def _replace_hashes(template: str, values: list[dict[str, Any]]) -> str | None:
    if not values or "#" not in template:
        return None
    output = template
    for value in values:
        replacement = value.get("rangeText") or "#"
        output = output.replace("#", replacement, 1)
    return output


def _read_aggregate_value_ranges(mod_div, soup: BeautifulSoup, template: str) -> tuple[list[dict[str, Any]], str | None]:
    target = clean_display_text(mod_div.get("data-bs-target")) or ""
    if not target.startswith("#"):
        return [], None
    # Avoid CSS selector lookup here: PoE2DB pages contain large modal tables and
    # soupsieve select_one("#id") can be extremely slow on Python 3.13.
    modal = soup.find(id=target[1:])
    if modal is None:
        return [], None

    by_position: dict[int, dict[str, Any]] = {}
    for row in modal.select("table.orig tbody tr"):
        spans = row.select("span.mod-value")
        if not spans:
            continue
        for index, span in enumerate(spans):
            parsed = _parse_mod_value_range(span.get_text(" ", strip=True))
            if not parsed:
                continue
            current = by_position.setdefault(index, {
                "index": index,
                "min": None,
                "max": None,
                "value": None,
                "rangeText": None,
                "valuePrefix": parsed.get("sign") or "",
                "valueSuffix": "",
            })
            current["min"] = parsed["min"] if current["min"] is None else min(current["min"], parsed["min"])
            current["max"] = parsed["max"] if current["max"] is None else max(current["max"], parsed["max"])
            if not current.get("valuePrefix") and parsed.get("sign"):
                current["valuePrefix"] = parsed["sign"]

    values = [by_position[key] for key in sorted(by_position)]
    hash_count = template.count("#")
    if hash_count and len(values) > hash_count:
        values = values[:hash_count]
    for value in values:
        value["rangeText"] = _range_text(value.get("valuePrefix") or "", value.get("min"), value.get("max"))
    display = _replace_hashes(template, values)
    return values, display

def _read_metric_badges(mod_div) -> tuple[str | None, str | None, int | None, int | None]:
    """Return weight, weight percent, max level, tier count from list-row badges.

    PoE2DB order in the row is danger=weight, secondary=max level, success=tier count.
    We store them as descriptive fields; we do not use them for odds/crafting.
    """
    weight_raw: str | None = None
    weight_percent: str | None = None
    level: int | None = None
    tier_count: int | None = None

    danger = mod_div.select_one("span.float-end span.badge.bg-danger")
    if danger is not None:
        weight_raw = clean_display_text(danger.get_text(" ", strip=True)) or None
        weight_percent = clean_display_text(danger.get("data-bs-title")) or None

    secondary = mod_div.select_one("span.float-end span.badge.bg-secondary")
    if secondary is not None:
        raw = clean_display_text(secondary.get_text(" ", strip=True))
        level = int(raw) if raw and raw.isdigit() else None

    success = mod_div.select_one("span.float-end span.badge.bg-success")
    if success is not None:
        raw = clean_display_text(success.get_text(" ", strip=True))
        tier_count = int(raw) if raw and raw.isdigit() else None

    return weight_raw, weight_percent, level, tier_count


def _read_tags(mod_div) -> list[str]:
    content_span = _content_span(mod_div)
    if content_span is None:
        return []
    tags: list[str] = []
    for badge in content_span.select("span.badge[data-tag]"):
        tag_key = str(badge.get("data-tag") or "").strip().lower()
        label = TAG_TEXT_BY_DATA_TAG.get(tag_key) or clean_display_text(badge.get_text(" ", strip=True))
        if label and label not in tags:
            tags.append(label)
    return tags


def _read_display_text_from_mod_div(mod_div) -> str:
    content_span = _content_span(mod_div)
    if content_span is None:
        return ""
    clone = BeautifulSoup(str(content_span), "html.parser")
    for badge in clone.select("span.badge"):
        badge.decompose()
    return _normalize_mod_text(clone.get_text(" ", strip=True))


def parse_mods_from_html_block(block_html: str, *, group_key: str, source_url: str, item_class: str, subtype: str, affix_type: str, root_soup: BeautifulSoup | None = None) -> list[dict[str, Any]]:
    soup = BeautifulSoup(block_html, "html.parser")
    mods: list[dict[str, Any]] = []
    for index, mod_div in enumerate(soup.select("div.mod-title.explicitMod")):
        text = _read_display_text_from_mod_div(mod_div)
        if not text:
            continue
        weight_raw, weight_percent, level, tier_count = _read_metric_badges(mod_div)
        editable_values, display_range_text = _read_aggregate_value_ranges(mod_div, root_soup or soup, text)
        tags = _read_tags(mod_div)
        generation_group = clean_display_text(mod_div.get("data-gengroup")) or None
        family = _family_from_generation_group(generation_group)
        mods.append({
            "id": _affix_id(item_class, subtype, affix_type, index, text, family),
            "text": text,
            "textTemplate": text,
            "displayRangeText": display_range_text,
            "editableValues": editable_values,
            "affixType": affix_type,
            "sourceGroup": SECTION_LABELS.get(group_key, group_key),
            "family": family,
            "generationGroup": generation_group,
            "weightRaw": weight_raw,
            "weightPercent": weight_percent,
            "level": level,
            "tierCount": tier_count,
            "detailStatus": "available",
            "tags": tags,
            "keywords": [],
            "sourceUrl": source_url,
        })
    return mods


def parse_normal_affix_sources(
    snapshot_text: str,
    *,
    source_url: str,
    item_class: str,
    subtype: str,
    slug: str,
    prefix_html: str | None = None,
    suffix_html: str | None = None,
    validation_source: str = "user_supplied_modifiers_calc_snapshot",
    confidence: str = "medium",
) -> dict[str, Any]:
    sections = split_snapshot_sections(snapshot_text)
    diagnostics: list[dict[str, Any]] = []

    if prefix_html:
        prefixes = parse_mods_from_html_block(
            prefix_html,
            group_key="base_prefix",
            source_url=source_url,
            item_class=item_class,
            subtype=subtype,
            affix_type="prefix",
        )
        diagnostics.append({
            "severity": "info",
            "code": "NORMAL_PREFIX_DOM_SOURCE_USED",
            "message": "Base Prefix affixes were parsed from PoE2DB DOM HTML, preserving display text, tags, family, level, weight, and tier count.",
            "actionRequired": False,
        })
    else:
        prefixes = parse_snapshot_mods(
            sections.get("base_prefix", []),
            group_key="base_prefix",
            source_url=source_url,
            item_class=item_class,
            subtype=subtype,
            affix_type="prefix",
        )
        diagnostics.append({
            "severity": "info",
            "code": "NORMAL_PREFIX_TXT_FALLBACK_USED",
            "message": "Base Prefix affixes were parsed from text snapshot fallback.",
            "actionRequired": False,
        })

    if suffix_html:
        suffixes = parse_mods_from_html_block(
            suffix_html,
            group_key="base_suffix",
            source_url=source_url,
            item_class=item_class,
            subtype=subtype,
            affix_type="suffix",
        )
        diagnostics.append({
            "severity": "info",
            "code": "NORMAL_SUFFIX_DOM_SOURCE_USED",
            "message": "Base Suffix affixes were parsed from PoE2DB DOM HTML.",
            "actionRequired": False,
        })
    else:
        suffixes = parse_snapshot_mods(
            sections.get("base_suffix", []),
            group_key="base_suffix",
            source_url=source_url,
            item_class=item_class,
            subtype=subtype,
            affix_type="suffix",
        )
        diagnostics.append({
            "severity": "info",
            "code": "NORMAL_SUFFIX_TXT_FALLBACK_USED",
            "message": "Base Suffix affixes were parsed from text snapshot fallback until a suffix DOM fixture is supplied.",
            "actionRequired": False,
        })

    if not prefixes or not suffixes:
        diagnostics.append({
            "severity": "warning",
            "code": "NORMAL_AFFIX_SNAPSHOT_INCOMPLETE",
            "message": "Normal explicit snapshot did not contain both Base Prefix and Base Suffix sections.",
            "actionRequired": True,
        })

    raw_sources = ["snapshot_txt"]
    if prefix_html:
        raw_sources.append("prefix_dom_html")
    if suffix_html:
        raw_sources.append("suffix_dom_html")

    return {
        "id": f"poe2db:{slug}:normal_explicit",
        "slug": f"{slug}:normal_explicit",
        "source": "poe2db",
        "sourceUrl": source_url,
        "kind": "normal_explicit_pool",
        "itemClass": item_class,
        "subtype": subtype,
        "sourceSection": "ModifiersCalc",
        "sourceGroups": ["Base Prefix", "Base Suffix"],
        "plannerPrimary": True,
        "validationSource": validation_source,
        "confidence": confidence,
        "prefixes": prefixes,
        "suffixes": suffixes,
        "diagnostics": diagnostics,
        "rawSectionNames": list(sections.keys()),
        "rawSources": raw_sources,
    }


def parse_normal_affix_snapshot(
    snapshot_text: str,
    *,
    source_url: str,
    item_class: str,
    subtype: str,
    slug: str,
    validation_source: str = "user_supplied_modifiers_calc_snapshot",
    confidence: str = "medium",
) -> dict[str, Any]:
    return parse_normal_affix_sources(
        snapshot_text,
        source_url=source_url,
        item_class=item_class,
        subtype=subtype,
        slug=slug,
        validation_source=validation_source,
        confidence=confidence,
    )


def load_normal_affix_snapshot(path: Path, *, source_url: str, item_class: str, subtype: str, slug: str, validation_source: str, confidence: str, prefix_html_path: Path | None = None, suffix_html_path: Path | None = None) -> dict[str, Any]:
    prefix_html = prefix_html_path.read_text(encoding="utf-8") if prefix_html_path and prefix_html_path.exists() else None
    suffix_html = suffix_html_path.read_text(encoding="utf-8") if suffix_html_path and suffix_html_path.exists() else None
    return parse_normal_affix_sources(
        path.read_text(encoding="utf-8"),
        source_url=source_url,
        item_class=item_class,
        subtype=subtype,
        slug=slug,
        prefix_html=prefix_html,
        suffix_html=suffix_html,
        validation_source=validation_source,
        confidence=confidence,
    )


SOURCE_MECHANICS: list[dict[str, Any]] = [
    {"id": "normal", "label": "Normal", "order": 0},
    {"id": "corrupted", "label": "Corrupted", "order": 1},
    {"id": "essence", "label": "Essence", "order": 2},
    {"id": "perfect_essence", "label": "Perfect Essence", "order": 3},
    {"id": "desecrated", "label": "Desecrated", "order": 4},
    {"id": "augment", "label": "Augment-compatible", "order": 5},
    {"id": "bonded", "label": "Bonded-compatible", "order": 6},
]


def source_mechanic_metadata() -> list[dict[str, Any]]:
    return [dict(item) for item in SOURCE_MECHANICS]


def source_mechanic_labels() -> dict[str, str]:
    return {str(item["id"]): str(item["label"]) for item in SOURCE_MECHANICS}


def source_mechanic_order() -> list[str]:
    return [str(item["id"]) for item in sorted(SOURCE_MECHANICS, key=lambda item: int(item["order"]))]

EDITOR_GROUP_CONFIG: dict[str, dict[str, Any]] = {
    "Base Prefix": {"sourceMechanic": "normal", "affixType": "prefix", "plannerPrimary": True},
    "Base Suffix": {"sourceMechanic": "normal", "affixType": "suffix", "plannerPrimary": True},
    "Desecrated Modifiers Prefix": {"sourceMechanic": "desecrated", "affixType": "prefix", "plannerPrimary": True},
    "Desecrated Modifiers Suffix": {"sourceMechanic": "desecrated", "affixType": "suffix", "plannerPrimary": True},
    "Essence Prefix": {"sourceMechanic": "essence", "affixType": "prefix", "plannerPrimary": True},
    "Essence Suffix": {"sourceMechanic": "essence", "affixType": "suffix", "plannerPrimary": True},
    "Perfect Essence Prefix": {"sourceMechanic": "perfect_essence", "affixType": "prefix", "plannerPrimary": True},
    "Perfect Essence Suffix": {"sourceMechanic": "perfect_essence", "affixType": "suffix", "plannerPrimary": True},
    "Augment": {"sourceMechanic": "augment", "affixType": None, "plannerPrimary": True},
    "Bonded Modifiers": {"sourceMechanic": "bonded", "affixType": None, "plannerPrimary": True},
    "Corrupted": {"sourceMechanic": "corrupted", "affixType": None, "plannerPrimary": True},
}


def _editor_mod_id(
    item_class: str,
    subtype: str,
    source_mechanic: str,
    source_group: str,
    index: int,
    text: str,
    family: str | None = None,
) -> str:
    base = family or text
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    group_slug = re.sub(r"[^a-z0-9]+", "-", source_group.lower()).strip("-")
    return f"poe2db:{item_class.lower()}:{subtype}:editor_modifier:{source_mechanic}:{group_slug}:{index}:{slug}"


def parse_editor_mods_from_html_block(
    block_html: str,
    *,
    source_url: str,
    item_class: str,
    subtype: str,
    source_group: str,
    source_mechanic: str,
    affix_type: str | None,
    root_soup: BeautifulSoup | None = None,
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(block_html, "html.parser")
    mods: list[dict[str, Any]] = []
    for index, mod_div in enumerate(soup.select("div.mod-title.explicitMod")):
        text = _read_display_text_from_mod_div(mod_div)
        if not text:
            continue
        weight_raw, weight_percent, level, tier_count = _read_metric_badges(mod_div)
        editable_values, display_range_text = _read_aggregate_value_ranges(mod_div, root_soup or soup, text)
        tags = _read_tags(mod_div)
        generation_group = clean_display_text(mod_div.get("data-gengroup")) or None
        family = _family_from_generation_group(generation_group)
        mods.append({
            "id": _editor_mod_id(item_class, subtype, source_mechanic, source_group, index, text, family),
            "text": text,
            "textTemplate": text,
            "displayRangeText": display_range_text,
            "editableValues": editable_values,
            "sourceGroup": source_group,
            "sourceMechanic": source_mechanic,
            "affixType": affix_type,
            "family": family,
            "generationGroup": generation_group,
            "weightRaw": weight_raw,
            "weightPercent": weight_percent,
            "level": level,
            "tierCount": tier_count,
            "detailStatus": "available",
            "tags": tags,
            "keywords": [],
            "sourceUrl": source_url,
        })
    return mods



MODSVIEW_GROUPS: list[tuple[str, str, str | None, str, str | None]] = [
    ("Base Prefix", "normal", "prefix", "normal", "1"),
    ("Base Suffix", "normal", "suffix", "normal", "2"),
    ("Desecrated Modifiers Prefix", "desecrated", "prefix", "desecrated", "1"),
    ("Desecrated Modifiers Suffix", "desecrated", "suffix", "desecrated", "2"),
    ("Essence Prefix", "essence", "prefix", "essence", "1"),
    ("Essence Suffix", "essence", "suffix", "essence", "2"),
    ("Perfect Essence Prefix", "perfect_essence", "prefix", "perfect_essence", "1"),
    ("Perfect Essence Suffix", "perfect_essence", "suffix", "perfect_essence", "2"),
    ("Augment", "augment", None, "socketable", None),
    ("Bonded Modifiers", "bonded", None, "bonded", None),
    ("Corrupted", "corrupted", None, "corrupted", None),
]


def _extract_modsview_data(html: str) -> dict[str, Any] | None:
    match = re.search(r"new\s+ModsView\((\{.*?\})\);", html, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _clean_modview_name(raw: Any) -> str | None:
    if raw is None:
        return None
    text = BeautifulSoup(str(raw), "html.parser").get_text(" ", strip=True)
    return clean_display_text(text) or None



def _modview_name_href(raw: Any) -> str | None:
    if raw is None:
        return None
    soup = BeautifulSoup(str(raw), "html.parser")
    link = soup.find("a", href=True)
    if link is None:
        return None
    href = str(link.get("href") or "").strip()
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return "https://poe2db.tw/us/" + href.lstrip("/")

def _template_from_modview_str(raw: Any) -> tuple[str, list[dict[str, Any]], str | None]:
    soup = BeautifulSoup(str(raw or ""), "html.parser")
    parsed_values: list[dict[str, Any]] = []
    for index, span in enumerate(soup.select("span.mod-value")):
        parsed = _parse_mod_value_range(span.get_text(" ", strip=True))
        if parsed:
            low = parsed["min"]
            high = parsed["max"]
            parsed_values.append({
                "index": index,
                "min": low,
                "max": high,
                "value": None,
                "rangeText": _range_text(parsed.get("sign") or "", low, high),
                "valuePrefix": parsed.get("sign") or "",
                "valueSuffix": "",
            })
        span.string = "#"
    for badge in soup.select("span.badge"):
        badge.decompose()
    text = _normalize_mod_text(soup.get_text(" ", strip=True))
    # Browser-rendered DOM has no space before percent in templates.
    text = text.replace("# %", "#%")
    display = _replace_hashes(text, parsed_values)
    return text, parsed_values, display


def _tags_from_modview_row(row: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for raw in row.get("mod_no") or []:
        soup = BeautifulSoup(str(raw), "html.parser")
        for badge in soup.select("span.badge[data-tag]"):
            tag_key = str(badge.get("data-tag") or "").strip().lower()
            label = TAG_TEXT_BY_DATA_TAG.get(tag_key) or clean_display_text(badge.get_text(" ", strip=True))
            if label and label not in tags:
                tags.append(label)
        # Some rows only have text once loaded from JSON.
        if not tags:
            label = clean_display_text(soup.get_text(" ", strip=True))
            if label and label not in tags:
                tags.append(label)
    return tags


def _family_from_modview_row(row: dict[str, Any]) -> str | None:
    families = row.get("ModFamilyList") or []
    if not families:
        return None
    first = families[0]
    return clean_display_text(str(first)) or None


def _merge_mod_values(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_index: dict[int, dict[str, Any]] = {int(v.get("index") or i): dict(v) for i, v in enumerate(existing)}
    for i, value in enumerate(incoming):
        index = int(value.get("index") or i)
        current = by_index.setdefault(index, dict(value))
        if value.get("min") is not None:
            current["min"] = value["min"] if current.get("min") is None else min(current["min"], value["min"])
        if value.get("max") is not None:
            current["max"] = value["max"] if current.get("max") is None else max(current["max"], value["max"])
        if not current.get("valuePrefix") and value.get("valuePrefix"):
            current["valuePrefix"] = value.get("valuePrefix")
    merged = [by_index[key] for key in sorted(by_index)]
    for value in merged:
        value["rangeText"] = _range_text(value.get("valuePrefix") or "", value.get("min"), value.get("max"))
    return merged


def _modview_rows_for_group(data: dict[str, Any], data_key: str, affix_type: str | None, gen_id: str | None) -> list[dict[str, Any]]:
    rows = list(data.get(data_key) or [])
    if data_key == "essence":
        rows = [row for row in rows if str(row.get("IsPerfect")) in {"0", "False", "false", "None", ""}]
    if data_key == "perfect_essence":
        rows = [row for row in rows if str(row.get("IsPerfect")) in {"1", "True", "true"}]
    if gen_id is not None:
        rows = [row for row in rows if str(row.get("ModGenerationTypeID")) == gen_id]
    return rows



def normalize_fixed_value_text(text: str | None) -> str:
    text = clean_display_text(text or "")
    text = text.replace("#%", "#%")
    text = re.sub(r"\s+%", "%", text)
    text = re.sub(r"^\+\s+", "+", text)
    text = re.sub(r"^(-)\s+", r"\1", text)
    return _normalize_mod_text(text)


def _parse_editor_mods_from_modsview_rows(
    rows: list[dict[str, Any]],
    *,
    source_url: str,
    item_class: str,
    subtype: str,
    source_group: str,
    source_mechanic: str,
    affix_type: str | None,
) -> list[dict[str, Any]]:
    # Augment socket options are fixed-value items, not editable range families.
    # PoE2DB exposes each rune tier as a separate ModsView row with Name + str.
    # Keep these rows ungrouped so the planner can show e.g.
    # "Lesser Desert Rune - +10% to Fire Resistance" instead of one editable
    # "#% to Fire Resistance" aggregate.
    if source_mechanic == "augment":
        mods: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            template, _values, display = _template_from_modview_str(row.get("str"))
            stat_text = normalize_fixed_value_text(display or template)
            raw_name = row.get("Name")
            rune_name = _clean_modview_name(raw_name)
            augment_source_url = _modview_name_href(raw_name)
            if not stat_text or not rune_name:
                continue
            family = _family_from_modview_row(row)
            level_raw = row.get("Level")
            try:
                level = int(level_raw)
            except (TypeError, ValueError):
                level = None
            weight = row.get("DropChance")
            try:
                weight_raw = str(int(weight)) if weight is not None else None
            except (TypeError, ValueError):
                weight_raw = str(weight) if weight is not None else None
            label = f"{rune_name} - {stat_text}"
            mods.append({
                "id": _editor_mod_id(item_class, subtype, source_mechanic, source_group, index, rune_name, family),
                "text": stat_text,
                "textTemplate": stat_text,
                "displayRangeText": stat_text,
                "editableValues": [],
                "sourceGroup": source_group,
                "sourceMechanic": source_mechanic,
                "affixType": affix_type,
                "family": family,
                "generationGroup": family,
                "weightRaw": weight_raw,
                "weightPercent": None,
                "level": level,
                "tierCount": 1,
                "detailStatus": "available",
                "tags": _tags_from_modview_row(row),
                "keywords": [],
                "sourceUrl": source_url,
                "runeName": rune_name,
                "augmentName": rune_name,
                "augmentCategory": classify_augment_name(rune_name),
                "augmentSourceUrl": augment_source_url,
                "socketStatText": stat_text,
                "pickerLabel": label,
                "fixedValue": True,
            })
        return mods

    grouped: dict[tuple[str | None, str], dict[str, Any]] = {}
    for row in rows:
        template, values, _display = _template_from_modview_str(row.get("str"))
        if not template:
            continue
        family = _family_from_modview_row(row)
        key = (family, template)
        current = grouped.setdefault(key, {
            "template": template,
            "family": family,
            "generationGroup": family,
            "editableValues": [],
            "tags": [],
            "keywords": [],
            "weightRaw": None,
            "level": None,
            "tierCount": 0,
            "names": [],
        })
        current["editableValues"] = _merge_mod_values(current["editableValues"], values)
        for tag in _tags_from_modview_row(row):
            if tag not in current["tags"]:
                current["tags"].append(tag)
        name = _clean_modview_name(row.get("Name"))
        if name and name not in current["names"]:
            current["names"].append(name)
        level_raw = row.get("Level")
        try:
            level = int(level_raw)
        except (TypeError, ValueError):
            level = None
        if level is not None:
            current["level"] = level if current["level"] is None else max(current["level"], level)
        weight = row.get("DropChance")
        if weight is not None:
            try:
                current_weight = int(current["weightRaw"] or 0)
                current["weightRaw"] = str(current_weight + int(weight))
            except (TypeError, ValueError):
                current["weightRaw"] = str(weight)
        current["tierCount"] = int(current.get("tierCount") or 0) + 1

    mods: list[dict[str, Any]] = []
    for index, current in enumerate(grouped.values()):
        text = current["template"]
        display_range_text = _replace_hashes(text, current["editableValues"])
        mods.append({
            "id": _editor_mod_id(item_class, subtype, source_mechanic, source_group, index, text, current.get("family")),
            "text": text,
            "textTemplate": text,
            "displayRangeText": display_range_text,
            "editableValues": current["editableValues"],
            "sourceGroup": source_group,
            "sourceMechanic": source_mechanic,
            "affixType": affix_type,
            "family": current.get("family"),
            "generationGroup": current.get("generationGroup"),
            "weightRaw": current.get("weightRaw"),
            "weightPercent": None,
            "level": current.get("level"),
            "tierCount": current.get("tierCount"),
            "detailStatus": "available",
            "tags": current.get("tags") or [],
            "keywords": current.get("keywords") or [],
            "sourceUrl": source_url,
        })
    return mods


def parse_editor_modifier_pools_from_modsview_json(
    html: str,
    *,
    source_url: str,
    item_class: str,
    subtype: str,
    slug: str,
    validation_source: str = "poe2db_modsview_json",
    confidence: str = "high",
) -> list[dict[str, Any]]:
    data = _extract_modsview_data(html)
    if not data:
        return []
    pools: list[dict[str, Any]] = []
    for label, source_mechanic, affix_type, data_key, gen_id in MODSVIEW_GROUPS:
        config = EDITOR_GROUP_CONFIG[label]
        rows = _modview_rows_for_group(data, data_key, affix_type, gen_id)
        mods = _parse_editor_mods_from_modsview_rows(
            rows,
            source_url=source_url,
            item_class=item_class,
            subtype=subtype,
            source_group=label,
            source_mechanic=source_mechanic,
            affix_type=affix_type,
        )
        affix_part = affix_type or "none"
        group_slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        diagnostics = [{
            "severity": "info",
            "code": "EDITOR_MODIFIER_POOL_MODSVIEW_JSON_SOURCE_USED",
            "message": f"{label} was parsed from PoE2DB ModsView JSON embedded in the subtype HTML.",
            "actionRequired": False,
        }]
        if not mods:
            diagnostics.append({
                "severity": "info",
                "code": "EDITOR_MODIFIER_POOL_EMPTY",
                "message": f"{label} exists in ModsView JSON but contains no selectable mods for this subtype.",
                "actionRequired": False,
            })
        pools.append({
            "id": f"poe2db:{slug}:editor_pool:{source_mechanic}:{affix_part}:{group_slug}",
            "slug": f"{slug}:editor_pool:{source_mechanic}:{affix_part}:{group_slug}",
            "source": "poe2db",
            "sourceUrl": source_url,
            "kind": "editor_modifier_pool",
            "itemClass": item_class,
            "subtype": subtype,
            "sourceSection": "ModifiersCalc",
            "sourceGroup": label,
            "sourceMechanic": source_mechanic,
            "affixType": affix_type,
            "plannerPrimary": bool(config.get("plannerPrimary", True)),
            "validationSource": validation_source,
            "confidence": confidence,
            "mods": mods,
            "diagnostics": diagnostics,
            "rawSource": "modsview_json",
        })
    return pools

def parse_editor_modifier_pools_from_html(
    html: str,
    *,
    source_url: str,
    item_class: str,
    subtype: str,
    slug: str,
    validation_source: str = "user_uploaded_full_modifiers_calc_html",
    confidence: str = "high",
) -> list[dict[str, Any]]:
    # Prefer the embedded ModsView JSON when available: it carries the actual
    # selectable row name for fixed augment socketables (Lesser Desert Rune,
    # Desert Rune, Greater Desert Rune, etc.). The rendered DOM aggregate merges
    # those rows into one editable "#% to Fire Resistance" family, which is not
    # the planner UX we want for socketed runes.
    if _extract_modsview_data(html):
        return parse_editor_modifier_pools_from_modsview_json(
            html,
            source_url=source_url,
            item_class=item_class,
            subtype=subtype,
            slug=slug,
            validation_source="poe2db_modsview_json_preferred",
            confidence=confidence,
        )

    soup = BeautifulSoup(html, "html.parser")
    pools: list[dict[str, Any]] = []
    for h5 in soup.select("h5.identify-title"):
        raw_label = clean_display_text(h5.get_text(" ", strip=True)) or ""
        # FontAwesome icons have no text, so raw_label should already be clean.
        label = raw_label.strip()
        if label not in EDITOR_GROUP_CONFIG:
            continue
        config = EDITOR_GROUP_CONFIG[label]
        block = h5.find_parent("div", class_="col-lg-6") or h5.find_parent("div")
        block_html = str(block) if block is not None else ""
        source_mechanic = str(config["sourceMechanic"])
        affix_type = config["affixType"]
        mods = parse_editor_mods_from_html_block(
            block_html,
            source_url=source_url,
            item_class=item_class,
            subtype=subtype,
            source_group=label,
            source_mechanic=source_mechanic,
            affix_type=affix_type,
            root_soup=soup,
        )
        affix_part = affix_type or "none"
        group_slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        diagnostics = [{
            "severity": "info",
            "code": "EDITOR_MODIFIER_POOL_DOM_SOURCE_USED",
            "message": f"{label} was parsed from full PoE2DB ModifiersCalc HTML.",
            "actionRequired": False,
        }]
        if not mods:
            diagnostics.append({
                "severity": "info",
                "code": "EDITOR_MODIFIER_POOL_EMPTY",
                "message": f"{label} exists in the source HTML but contains no selectable mods for this subtype.",
                "actionRequired": False,
            })
        pools.append({
            "id": f"poe2db:{slug}:editor_pool:{source_mechanic}:{affix_part}:{group_slug}",
            "slug": f"{slug}:editor_pool:{source_mechanic}:{affix_part}:{group_slug}",
            "source": "poe2db",
            "sourceUrl": source_url,
            "kind": "editor_modifier_pool",
            "itemClass": item_class,
            "subtype": subtype,
            "sourceSection": "ModifiersCalc",
            "sourceGroup": label,
            "sourceMechanic": source_mechanic,
            "affixType": affix_type,
            "plannerPrimary": bool(config.get("plannerPrimary", True)),
            "validationSource": validation_source,
            "confidence": confidence,
            "mods": mods,
            "diagnostics": diagnostics,
            "rawSource": "full_html",
        })
    if pools:
        return pools
    return parse_editor_modifier_pools_from_modsview_json(
        html,
        source_url=source_url,
        item_class=item_class,
        subtype=subtype,
        slug=slug,
        validation_source="poe2db_modsview_json_fallback",
        confidence=confidence,
    )


def normal_pool_from_editor_pools(
    editor_pools: list[dict[str, Any]],
    *,
    source_url: str,
    item_class: str,
    subtype: str,
    slug: str,
    validation_source: str = "derived_from_full_modifiers_calc_html",
    confidence: str = "high",
) -> dict[str, Any]:
    prefix_pool = next((pool for pool in editor_pools if pool.get("sourceGroup") == "Base Prefix"), None)
    suffix_pool = next((pool for pool in editor_pools if pool.get("sourceGroup") == "Base Suffix"), None)
    def convert(mod: dict[str, Any], affix_type: str) -> dict[str, Any]:
        return {
            "id": mod["id"].replace(":editor_modifier:", ":normal_explicit:"),
            "text": mod["text"],
            "textTemplate": mod.get("textTemplate"),
            "displayRangeText": mod.get("displayRangeText"),
            "editableValues": list(mod.get("editableValues") or []),
            "affixType": affix_type,
            "sourceGroup": mod["sourceGroup"],
            "family": mod.get("family"),
            "generationGroup": mod.get("generationGroup"),
            "weightRaw": mod.get("weightRaw"),
            "weightPercent": mod.get("weightPercent"),
            "level": mod.get("level"),
            "tierCount": mod.get("tierCount"),
            "detailStatus": mod.get("detailStatus") or "available",
            "tags": list(mod.get("tags") or []),
            "keywords": list(mod.get("keywords") or []),
            "sourceUrl": mod.get("sourceUrl") or source_url,
        }
    prefixes = [convert(mod, "prefix") for mod in (prefix_pool or {}).get("mods", [])]
    suffixes = [convert(mod, "suffix") for mod in (suffix_pool or {}).get("mods", [])]
    diagnostics: list[dict[str, Any]] = [{
        "severity": "info",
        "code": "NORMAL_EXPLICIT_POOL_DERIVED_FROM_FULL_HTML",
        "message": "Base Prefix/Base Suffix were derived from full ModifiersCalc HTML.",
        "actionRequired": False,
    }]
    if not prefixes or not suffixes:
        diagnostics.append({
            "severity": "warning",
            "code": "NORMAL_EXPLICIT_POOL_INCOMPLETE",
            "message": "Could not derive both Base Prefix and Base Suffix from full ModifiersCalc HTML.",
            "actionRequired": True,
        })
    return {
        "id": f"poe2db:{slug}:normal_explicit",
        "slug": f"{slug}:normal_explicit",
        "source": "poe2db",
        "sourceUrl": source_url,
        "kind": "normal_explicit_pool",
        "itemClass": item_class,
        "subtype": subtype,
        "sourceSection": "ModifiersCalc",
        "sourceGroups": ["Base Prefix", "Base Suffix"],
        "plannerPrimary": True,
        "validationSource": validation_source,
        "confidence": confidence,
        "prefixes": prefixes,
        "suffixes": suffixes,
        "diagnostics": diagnostics,
        "rawSectionNames": [pool.get("sourceGroup") for pool in editor_pools],
        "rawSources": sorted({str(pool.get("rawSource") or "full_html") for pool in editor_pools if pool.get("rawSource")}),
    }


def load_editor_modifier_pools_from_full_html(
    path: Path,
    *,
    source_url: str,
    item_class: str,
    subtype: str,
    slug: str,
    validation_source: str = "user_uploaded_full_modifiers_calc_html",
    confidence: str = "high",
) -> list[dict[str, Any]]:
    return parse_editor_modifier_pools_from_html(
        path.read_text(encoding="utf-8"),
        source_url=source_url,
        item_class=item_class,
        subtype=subtype,
        slug=slug,
        validation_source=validation_source,
        confidence=confidence,
    )
