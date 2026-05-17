from __future__ import annotations

import re
from typing import Any

from .armour_config import ARMOUR_ITEM_CLASSES, armour_subtype_meta, armour_subtype_meta_by_slug
from .mod_pool_parser import (
    compare_mod_pools,
    parse_modifiers_calc_corrupted_dropdown,
    parse_modifiers_calc_corrupted_modsview_json,
    parse_static_vaal_corrupted_reference,
)
from .normalize import parse_requirement_line
from .text import clean_display_text, get_page_lines_from_html, slug_from_url

SUBTYPE_META: dict[str, dict[str, Any]] = armour_subtype_meta_by_slug()


DEFENCE_LABELS = {
    "Armour": "armour",
    "Evasion Rating": "evasion",
    "Energy Shield": "energyShield",
}

FOOTER_STARTS = {"Edit", "* * *"}


def _visible_text_from_anchor_line(line: str) -> str:
    line = re.sub(r"【\d+†Image:[^】]+】", "", line)
    line = re.sub(r"【\d+†([^】†]+)】", r"\1", line)
    line = re.sub(r"【\d+†([^】]+)†[^】]+】", r"\1", line)
    return clean_display_text(line)


def _parse_defence_line(line: str) -> tuple[str, int] | None:
    line = _visible_text_from_anchor_line(line)
    for label, key in DEFENCE_LABELS.items():
        if line.startswith(label + ":"):
            if m := re.search(r":\s*(\d+)", line):
                return key, int(m.group(1))
    return None


def _parse_defence_at(lines: list[str], index: int) -> tuple[str, int, int] | None:
    """Parse both normal and tokenized PoE2DB defence rows.

    Depending on how PoE2DB renders a table, BeautifulSoup may produce either
    `Armour: 29` or three separate lines: `Armour`, `:`, `29`.  The older
    parser only handled the single-line form, which is why live Helmet pages
    produced an empty base item list even though `Helmet BaseItem /20` was
    present in the HTML.
    """
    if index >= len(lines):
        return None
    one_line = _parse_defence_line(lines[index])
    if one_line:
        key, value = one_line
        return key, value, index + 1

    label = _visible_text_from_anchor_line(lines[index])
    key = DEFENCE_LABELS.get(label)
    if key and index + 2 < len(lines):
        colon = _visible_text_from_anchor_line(lines[index + 1])
        value_text = _visible_text_from_anchor_line(lines[index + 2])
        if colon == ":" and re.fullmatch(r"\d+", value_text):
            return key, int(value_text), index + 3
    return None


def _parse_requirements_at(lines: list[str], index: int) -> tuple[dict[str, int | None], int] | None:
    if index >= len(lines):
        return None
    line = _visible_text_from_anchor_line(lines[index])
    if line.startswith("Requires:") and line != "Requires:":
        return parse_requirement_line(line), index + 1
    if line != "Requires:":
        return None

    parts: list[str] = []
    i = index + 1
    while i < len(lines):
        token = _visible_text_from_anchor_line(lines[i])
        if token == ",":
            i += 1
            continue
        if re.fullmatch(r"Level\s+\d+", token) or re.fullmatch(r"\d+\s+(Str|Dex|Int)", token):
            parts.append(token)
            i += 1
            continue
        break
    if not parts:
        return {"level": None, "str": None, "dex": None, "int": None}, index + 1
    return parse_requirement_line("Requires: " + ", ".join(parts)), i


def _looks_like_section_header(line: str) -> bool:
    return bool(
        line in FOOTER_STARTS
        or line.startswith("##### ")
        or re.fullmatch(r"(?:[A-Za-z ]+ )?Item Level", line)
        or line in {"Modifier weight", "Version history", "Item", "Total", "Close"}
    )


def parse_base_items_from_lines(lines: list[str]) -> list[dict[str, Any]]:
    clean_lines = [_visible_text_from_anchor_line(line) for line in lines]
    header_indices = [
        i for i, line in enumerate(clean_lines)
        if (" BaseItem" in line or re.search(r"\bItem\s*/\d+", line))
        and re.search(r"/\d+", line)
    ]
    if not header_indices:
        return []

    # The page also has a navigation/table-of-contents occurrence near the top.
    # The real data section is the last BaseItem header.
    start = header_indices[-1] + 1

    base_items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    i = start
    while i < len(clean_lines):
        line = clean_lines[i]
        if not line:
            i += 1
            continue
        if line.startswith("##### ") or line == "Edit" or line == "Version history":
            break
        if line.startswith("Image:") or line == "Image":
            i += 1
            continue
        if line.startswith("[DNT-") or line.startswith("DNT-") or "[DNT-" in line or "DNT-UNUSED" in line or " per level" in line:
            if current and current.get("defences"):
                base_items.append(current)
            current = None
            i += 1
            continue
        if line.startswith("local "):
            i += 1
            continue

        defence = _parse_defence_at(clean_lines, i)
        if defence:
            if current is not None:
                key, value, next_i = defence
                current.setdefault("defences", {})[key] = value
                i = next_i
                continue
            i = defence[2]
            continue

        requirements = _parse_requirements_at(clean_lines, i)
        if requirements:
            if current is not None:
                req, next_i = requirements
                current["requirements"] = req
                i = next_i
                continue
            i = requirements[1]
            continue

        # Stop once the base item list is finished and another PoE2DB section starts.
        # Do not treat these generic labels as item names.
        if _looks_like_section_header(line):
            if current and current.get("defences"):
                base_items.append(current)
            current = None
            break

        if current and current.get("defences"):
            base_items.append(current)
        current = {
            "name": line,
            "requirements": {"level": None, "str": None, "dex": None, "int": None},
            "defences": {},
        }
        i += 1

    if current and current.get("defences"):
        base_items.append(current)

    return [item for item in base_items if item.get("name") and item.get("defences")]

def _info(code: str, message: str) -> dict[str, Any]:
    return {"severity": "info", "code": code, "message": message, "actionRequired": False}


def parse_subtype_page(source_url: str, html: str) -> dict[str, Any]:
    slug = slug_from_url(source_url)
    meta = SUBTYPE_META.get(slug)
    if not meta:
        matching_class = next((item_class for item_class in ARMOUR_ITEM_CLASSES if slug.startswith(f"{item_class}_")), None)
        item_class = matching_class or slug.split("_", 1)[0] or "Unknown"
        suffix = slug.removeprefix(f"{item_class}_")
        meta = armour_subtype_meta(item_class, suffix)

    item_class = str(meta.get("itemClass") or "Gloves")
    lines = get_page_lines_from_html(html)
    base_items = parse_base_items_from_lines(lines)

    reference = parse_static_vaal_corrupted_reference(
        html,
        source_url=source_url,
        item_class=item_class,
        subtype=meta["subtype"],
    )
    dropdown_primary = parse_modifiers_calc_corrupted_dropdown(
        html,
        source_url=source_url,
        item_class=item_class,
        subtype=meta["subtype"],
    )
    modsview_primary = parse_modifiers_calc_corrupted_modsview_json(
        html,
        source_url=source_url,
        item_class=item_class,
        subtype=meta["subtype"],
    )
    primary = dropdown_primary or modsview_primary or {
        **reference,
        "id": f"poe2db:{slug_from_url(source_url)}:modifiers_calc:corrupted",
        "kind": "planner_corrupted_enchantment_pool",
        "sourceUrl": source_url + "#ModifiersCalc",
        "sourceSection": "ModifiersCalc",
        "sourceGroup": "Corrupted",
        "plannerPrimary": True,
        "mods": [
            {**mod, "sourceGroup": "Corrupted", "tags": [*mod.get("tags", []), "Corruption"] if "Corruption" not in mod.get("tags", []) else mod.get("tags", [])}
            for mod in reference.get("mods", [])
        ],
    }

    comparison = compare_mod_pools(primary, reference)
    diagnostics: list[dict[str, Any]] = []
    if dropdown_primary is None:
        diagnostics.append(_info(
            "MODIFIERS_CALC_DROPDOWN_NOT_EMBEDDED",
            "ModifiersCalc dropdown HTML was not embedded in fetched page; used embedded ModsView JSON or static Vaal reference fallback.",
        ))
    if comparison["status"] != "same":
        diagnostics.append(_info(
            "CORRUPTION_POOL_PRIMARY_SUPERSET" if comparison["status"] == "primary_superset" else "CORRUPTION_POOL_DIFFERS",
            f"Planner corrupted pool differs from static Vaal reference: {comparison['status']}.",
        ))

    return {
        "id": f"poe2db:{slug}",
        "slug": slug,
        "source": "poe2db",
        "sourceUrl": source_url,
        "kind": "item_subtype",
        "itemClass": item_class,
        "subtype": meta["subtype"],
        "label": meta["label"],
        "attributeProfile": meta["attributeProfile"],
        "defenceProfile": meta["defenceProfile"],
        "baseItems": base_items,
        "modGroups": [primary, reference],
        "modPoolComparisons": [comparison],
        "parseStatus": "ok",
        "warnings": [],
        "diagnostics": diagnostics,
    }
