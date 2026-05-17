from __future__ import annotations

from copy import copy
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .augment_classification import classify_augment_catalogue_entry
from .object_parser import parse_object_data
from .normalize import entity_id, normalized_augment_effects, slug
from .text import clean_display_text, node_text, title_from_url

CONDITION_LABELS = {
    "Martial Weapon": "martial_weapon",
    "Wand or Staff": "wand_or_staff",
    "Armour": "armour",
    "All Equipment": "all_equipment",
}

AUGMENT_INDEX_URL = "https://poe2db.tw/us/Augment"
AUGMENT_ITEM_SECTION_LABEL = "Augment Item"
RUNE_ITEM_SECTION_LABEL = "Rune Item"
CATALOGUE_SECTION_LABELS = {
    "Augment Item",
    "Augment Ref",
    "Rune Item",
    "Rune Ref",
    "SoulCore Ref",
}
EXPECTED_RUNE_AUGMENT_COUNT = 42


def _find_popup(soup: BeautifulSoup, expected_name: str | None = None) -> Tag | None:
    popups = soup.select(".newItemPopup")
    if not popups:
        return None
    if expected_name:
        for popup in popups:
            title = node_text(popup.select_one(".itemHeader .itemName"))
            if title == expected_name:
                return popup
    return popups[0]


def _direct_stat_divs(stats: Tag | None, class_name: str) -> list[Tag]:
    if stats is None:
        return []
    return [node for node in stats.find_all("div", class_=class_name, recursive=False)]


def _split_effect(text: str) -> tuple[str, str] | None:
    if ":" not in text:
        return None
    label, value = text.split(":", 1)
    label = clean_display_text(label)
    value = clean_display_text(value)
    if not label or not value:
        return None
    return CONDITION_LABELS.get(label, label.lower().replace(" ", "_")), value


def _description_lines(popup: Tag | None) -> list[str]:
    if popup is None:
        return []
    description = popup.select_one(".default.fst-italic") or popup.select_one(".default")
    if description is None:
        return []
    text = clean_display_text(description.get_text(" ", strip=True))
    if not text:
        return []

    parts: list[str] = []
    for sentence in text.split(". "):
        sentence = sentence.strip()
        if not sentence:
            continue
        if not sentence.endswith("."):
            sentence += "."
        if sentence == "Shift click to unstack.":
            continue
        parts.append(sentence)
    return parts


def _fallback_name(*, popup: Tag | None, object_data: dict[str, Any], source_url: str) -> str:
    title = node_text(popup.select_one(".itemHeader .itemName")) if popup else ""
    if title:
        return title
    if object_data.get("baseType"):
        return str(object_data["baseType"])
    return title_from_url(source_url)


def _augment_label_for_condition(condition: str) -> str:
    for label, key in CONDITION_LABELS.items():
        if key == condition:
            return label
    return condition.replace("_", " ").title()


def parse_augment_page(source_url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    object_data, _object_data_raw = parse_object_data(soup)
    popup = _find_popup(soup, expected_name=object_data.get("baseType"))
    name = _fallback_name(popup=popup, object_data=object_data, source_url=source_url)

    item_class = object_data.get("class") or "Augment"
    stats = popup.select_one(".Stats") if popup else None

    property_texts = [node_text(node) for node in _direct_stat_divs(stats, "property")]
    title_lines = [name]
    property_lines: list[str] = []
    for line in property_texts:
        if line == item_class and line not in title_lines:
            title_lines.append(line)
        else:
            property_lines.append(line)

    requirement_lines = [node_text(node) for node in _direct_stat_divs(stats, "requirements")]

    sections: list[dict[str, Any]] = [{"kind": "title", "lines": title_lines}]
    if property_lines:
        sections.append({"kind": "property", "lines": [line for line in property_lines if line]})
    if requirement_lines:
        sections.append({"kind": "requirement", "lines": [line for line in requirement_lines if line]})

    for node in _direct_stat_divs(stats, "implicitMod"):
        parsed = _split_effect(node_text(node))
        if parsed is None:
            continue
        condition, line = parsed
        sections.append(
            {
                "kind": "augment_effect",
                "condition": condition,
                "bonded": False,
                "lines": [line],
            }
        )

    for node in _direct_stat_divs(stats, "bondedMod"):
        text = node_text(node)
        if text == "Bonded:":
            continue
        parsed = _split_effect(text)
        if parsed is None:
            continue
        condition, line = parsed
        sections.append(
            {
                "kind": "augment_effect",
                "condition": condition,
                "bonded": True,
                "lines": [line],
            }
        )

    descriptions = _description_lines(popup)
    if descriptions:
        sections.append({"kind": "description", "lines": descriptions})

    effects = normalized_augment_effects(sections)
    for effect in effects:
        effect.setdefault("label", _augment_label_for_condition(str(effect.get("condition") or "")))

    return {
        "id": entity_id(source_url),
        "slug": slug(source_url),
        "sourceUrl": source_url,
        "source": "poe2db",
        "kind": "augment",
        "name": name,
        "itemClass": item_class,
        "baseType": object_data.get("baseType") or name,
        "icon": object_data.get("icon"),
        "tooltipSections": sections,
        "objectData": object_data,
        "augmentEffects": effects,
        "parseStatus": "ok",
        "warnings": [],
    }


def _section_key(text: str) -> str:
    return clean_display_text(text).split("/", 1)[0].strip()


def _top_level_section_headers(root: Tag) -> set[Tag]:
    headers: set[Tag] = set()
    for node in root.find_all(["h2", "h3", "h4", "h5", "h6"], recursive=False):
        if not isinstance(node, Tag):
            continue
        text = node_text(node)
        if "/" not in text:
            continue
        if _section_key(text) in CATALOGUE_SECTION_LABELS:
            headers.add(node)
    return headers


def _section_fragment_from_header(header: Tag) -> Tag:
    parent = header.parent
    if parent is None or not isinstance(parent, Tag):
        return header

    sibling_headers = _top_level_section_headers(parent)
    if len(sibling_headers) <= 1:
        return parent

    fragment = BeautifulSoup("<div></div>", "lxml").div
    if fragment is None:
        return parent
    for sibling in header.next_siblings:
        if isinstance(sibling, Tag) and sibling in sibling_headers:
            break
        fragment.append(copy(sibling))
    return fragment


def _section_root_for_header(header: Tag) -> Tag:
    card = header.find_parent(class_="card")
    if isinstance(card, Tag):
        return card
    return _section_fragment_from_header(header)




def _expected_catalogue_counts(soup: BeautifulSoup) -> dict[str, int]:
    counts: dict[str, int] = {}
    for text in soup.stripped_strings:
        label = clean_display_text(text)
        if "/" not in label:
            continue
        section, _, raw_count = label.partition("/")
        section = clean_display_text(section)
        if section not in CATALOGUE_SECTION_LABELS:
            continue
        try:
            counts[section] = int(raw_count.strip())
        except ValueError:
            continue
    return counts


def _candidate_sections_for_label(soup: BeautifulSoup, label: str) -> list[Tag]:
    sections: list[Tag] = []
    for header in soup.find_all(["h2", "h3", "h4", "h5", "h6"]):
        if _section_key(node_text(header)) == label:
            root = _section_root_for_header(header)
            if root not in sections:
                sections.append(root)

    for anchor in soup.find_all("a"):
        if _section_key(node_text(anchor)) != label:
            continue
        href = anchor.get("href") or ""
        if href.startswith("#") and len(href) > 1:
            pane = soup.select_one(href)
            if pane is not None and pane not in sections:
                sections.append(pane)
    return sections


def _is_catalogue_item_anchor(anchor: Tag) -> bool:
    name = clean_display_text(anchor.get_text(" ", strip=True))
    href = str(anchor.get("href") or "").strip()
    if not name or not href or href.startswith("#"):
        return False
    if href.startswith("http") and "poe2db.tw" not in href:
        return False
    if href.startswith("?"):
        return False
    if href.startswith("Economy") or href.startswith("Data"):
        return False
    if "/" in href and href.startswith(("http://", "https://")) is False:
        # Keep local Poe2DB item slugs, but ignore broad relative paths that are
        # usually site navigation rather than catalogue detail links.
        return False
    return True


def _collect_catalogue_entries_from_section(
    *,
    source_url: str,
    section: Tag,
    section_label: str,
    seen_urls: set[str],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for anchor in section.find_all("a"):
        if not _is_catalogue_item_anchor(anchor):
            continue
        name = clean_display_text(anchor.get_text(" ", strip=True))
        href = str(anchor.get("href") or "").strip()
        detail_url = urljoin(source_url, href)
        if detail_url in seen_urls:
            continue
        seen_urls.add(detail_url)
        classification = classify_augment_catalogue_entry(section_label, name)
        entries.append(
            {
                "id": entity_id(detail_url),
                "slug": slug(detail_url),
                "name": name,
                "sourceUrl": detail_url,
                "source": "poe2db",
                "kind": "augment_catalogue_entry",
                "section": section_label,
                "category": classification,
                "socketCandidate": section_label == RUNE_ITEM_SECTION_LABEL,
                "icon": _icon_for_anchor(anchor),
            }
        )
    return entries


def _catalogue_section_audits(soup: BeautifulSoup, source_url: str) -> list[dict[str, Any]]:
    expected_counts = _expected_catalogue_counts(soup)
    audits: list[dict[str, Any]] = []
    for label in sorted(CATALOGUE_SECTION_LABELS):
        seen_urls: set[str] = set()
        entries: list[dict[str, Any]] = []
        sections = _candidate_sections_for_label(soup, label)
        for section in sections:
            entries.extend(
                _collect_catalogue_entries_from_section(
                    source_url=source_url,
                    section=section,
                    section_label=label,
                    seen_urls=seen_urls,
                )
            )
        expected = expected_counts.get(label)
        category_counts: dict[str, int] = {}
        for entry in entries:
            category = str(entry.get("category") or "unknown")
            category_counts[category] = category_counts.get(category, 0) + 1
        warnings: list[str] = []
        if expected is None:
            count_comparison = "unknown"
        elif len(entries) < expected:
            count_comparison = "below_label"
            warnings.append(f"Parsed {len(entries)} entries, expected at least {expected} from the {label} label.")
        elif len(entries) > expected:
            count_comparison = "above_label"
        else:
            count_comparison = "matches_label"
        audits.append(
            {
                "section": label,
                "expected": expected,
                "expectedSource": "poe2db_section_label",
                "expectedComparison": "at_least",
                "countComparison": count_comparison,
                "discovered": len(entries),
                "extraDiscoveredOverLabel": (len(entries) - expected) if isinstance(expected, int) and len(entries) > expected else 0,
                "categoryCounts": category_counts,
                "socketCandidateCount": sum(1 for entry in entries if entry.get("socketCandidate")),
                "entries": entries,
                "warnings": warnings,
            }
        )
    return audits


def _candidate_rune_sections(soup: BeautifulSoup) -> list[Tag]:
    sections: list[Tag] = []
    for header in soup.find_all(["h2", "h3", "h4", "h5", "h6"]):
        if _section_key(node_text(header)) == RUNE_ITEM_SECTION_LABEL:
            root = _section_root_for_header(header)
            if root not in sections:
                sections.append(root)

    # Fallback for compact/static HTML fixtures and minor PoE2DB markup changes.
    # If a tab title points to a Rune Item pane, parse that pane directly.
    for anchor in soup.find_all("a"):
        if _section_key(node_text(anchor)) != RUNE_ITEM_SECTION_LABEL:
            continue
        href = anchor.get("href") or ""
        if href.startswith("#") and len(href) > 1:
            pane = soup.select_one(href)
            if pane is not None and pane not in sections:
                sections.append(pane)
    return sections


def _is_rune_item_anchor(anchor: Tag) -> bool:
    name = clean_display_text(anchor.get_text(" ", strip=True))
    href = str(anchor.get("href") or "").strip()
    if not name or not href or href.startswith("#"):
        return False
    if not _is_known_rune_name_like(name):
        return False
    if href.startswith("http") and "poe2db.tw" not in href:
        return False
    if href.startswith("?"):
        return False
    if href.startswith("Economy") or href.startswith("Data"):
        return False
    return True


def _icon_for_anchor(anchor: Tag) -> str | None:
    row = anchor.find_parent("tr")
    search_root = row or anchor.find_parent(class_="rune-card") or anchor.parent
    if search_root is None:
        return None
    image = search_root.find("img")
    if image is None:
        return None
    src = image.get("src") or image.get("data-src")
    return str(src) if src else None




def _normalise_property_line(text: str) -> str:
    return clean_display_text(text.replace("Stack Size:", "Stack Size: "))


def _lines_from_container(container: Tag) -> list[str]:
    raw_lines = [clean_display_text(line) for line in container.get_text("\n", strip=True).split("\n")]
    return [line for line in raw_lines if line and line != "Reset"]


def _line_effect(line: str, *, bonded: bool) -> dict[str, Any] | None:
    parsed = _split_effect(line)
    if parsed is None:
        return None
    condition, text = parsed
    return {
        "kind": "augment_effect",
        "condition": condition,
        "bonded": bonded,
        "lines": [text],
    }


def _embedded_augment_from_lines(
    *,
    source_url: str,
    name: str,
    detail_url: str,
    icon: str | None,
    lines: list[str],
) -> dict[str, Any] | None:
    if name not in lines:
        lines = [name, *lines]

    try:
        name_index = lines.index(name)
    except ValueError:
        name_index = 0

    relevant = lines[name_index + 1 :]
    sections: list[dict[str, Any]] = [{"kind": "title", "lines": [name, "Augment"]}]
    property_lines: list[str] = []
    requirement_lines: list[str] = []
    normal_sections: list[dict[str, Any]] = []
    bonded_sections: list[dict[str, Any]] = []
    bonded = False

    index = 0
    while index < len(relevant):
        line = relevant[index]
        if line == name:
            break
        if _is_known_rune_name_like(line) and normal_sections:
            break
        if line.startswith("Stack Size:"):
            if line.strip().lower() == "stack size:" and index + 1 < len(relevant):
                next_line = relevant[index + 1].strip()
                if next_line and not next_line.endswith(":") and ":" not in next_line:
                    combined = f"Stack Size: {next_line}"
                    if combined not in property_lines:
                        property_lines.append(combined)
                    index += 2
                    continue
            normalised = _normalise_property_line(line)
            if normalised.strip().lower() != "stack size:" and normalised not in property_lines:
                property_lines.append(normalised)
            index += 1
            continue
        if line.startswith("Requires:"):
            if line not in requirement_lines:
                requirement_lines.append(line)
            index += 1
            continue
        if line == "Bonded:":
            bonded = True
            index += 1
            continue
        effect = _line_effect(line, bonded=bonded)
        if effect is not None:
            if bonded:
                bonded_sections.append(effect)
            else:
                normal_sections.append(effect)
        index += 1

    if not normal_sections and not bonded_sections:
        return None

    if property_lines:
        sections.append({"kind": "property", "lines": property_lines})
    if requirement_lines:
        sections.append({"kind": "requirement", "lines": requirement_lines})
    sections.extend(normal_sections)
    sections.extend(bonded_sections)
    sections.append(
        {
            "kind": "description",
            "lines": [
                "Place into an empty Augment Socket in a Weapon or Armour to apply its effect to that item. Once socketed it cannot be retrieved but can be replaced by other Augment items."
            ],
        }
    )

    effects = normalized_augment_effects(sections)
    for effect in effects:
        effect.setdefault("label", _augment_label_for_condition(str(effect.get("condition") or "")))

    return {
        "id": entity_id(detail_url),
        "slug": slug(detail_url),
        "sourceUrl": detail_url,
        "source": "poe2db",
        "kind": "augment",
        "name": name,
        "itemClass": "Augment",
        "baseType": name,
        "icon": icon,
        "tooltipSections": sections,
        "objectData": {},
        "augmentEffects": effects,
        "parseStatus": "ok",
        "warnings": ["Parsed from the central Augment index instead of the detail page."],
    }


def _is_known_rune_name_like(line: str) -> bool:
    if not line.endswith(" Rune"):
        return False
    if ":" in line:
        return False
    return True


def _embedded_container_for_anchor(anchor: Tag, section: Tag) -> Tag:
    # Most stable source is the table/list row that owns this link. If there is
    # no row, fall back to the section so we can still parse compact fixtures.
    return anchor.find_parent("tr") or anchor.find_parent(class_="rune-card") or section


def _embedded_augment_for_anchor(source_url: str, section: Tag, anchor: Tag, name: str, detail_url: str) -> dict[str, Any] | None:
    container = _embedded_container_for_anchor(anchor, section)
    lines = _lines_from_container(container)
    return _embedded_augment_from_lines(
        source_url=source_url,
        name=name,
        detail_url=detail_url,
        icon=_icon_for_anchor(anchor),
        lines=lines,
    )

def _expected_rune_item_count(soup: BeautifulSoup) -> int:
    for text in soup.stripped_strings:
        label = clean_display_text(text)
        if not label.startswith(f"{RUNE_ITEM_SECTION_LABEL} /"):
            continue
        _, _, raw_count = label.partition("/")
        try:
            return int(raw_count.strip())
        except ValueError:
            continue
    return EXPECTED_RUNE_AUGMENT_COUNT


def _collect_rune_entries_from_section(
    *,
    source_url: str,
    section: Tag,
    seen_urls: set[str],
) -> list[dict[str, Any]]:
    runes: list[dict[str, Any]] = []
    for anchor in section.find_all("a"):
        if not _is_rune_item_anchor(anchor):
            continue
        name = clean_display_text(anchor.get_text(" ", strip=True))
        href = str(anchor.get("href") or "").strip()
        detail_url = urljoin(source_url, href)
        if detail_url in seen_urls:
            continue
        seen_urls.add(detail_url)
        embedded = _embedded_augment_for_anchor(source_url, section, anchor, name, detail_url)
        entry = {
            "id": entity_id(detail_url),
            "slug": slug(detail_url),
            "name": name,
            "sourceUrl": detail_url,
            "source": "poe2db",
            "kind": "augment_index_entry",
            "category": "rune",
            "icon": _icon_for_anchor(anchor),
        }
        if embedded is not None:
            entry["embeddedAugment"] = embedded
        runes.append(entry)
    return runes

def parse_augment_index_page(source_url: str, html: str) -> dict[str, Any]:
    """Parse the central PoE2DB Augment page and return the Rune Item catalogue.

    The planner only needs Rune Items for now. The live page can expose the Rune
    Item label either as a real content section or as a tab/navigation heading;
    when the section scan looks partial we fall back to the full page but still
    admit only clean rune item names.
    """
    soup = BeautifulSoup(html, "lxml")
    catalogue_sections = _catalogue_section_audits(soup, source_url)
    expected_count = _expected_rune_item_count(soup)
    runes: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    warnings: list[str] = []

    candidate_sections = _candidate_rune_sections(soup)
    for section in candidate_sections:
        runes.extend(
            _collect_rune_entries_from_section(
                source_url=source_url,
                section=section,
                seen_urls=seen_urls,
            )
        )

    if not runes:
        runes.extend(
            _collect_rune_entries_from_section(
                source_url=source_url,
                section=soup,
                seen_urls=seen_urls,
            )
        )
        if not candidate_sections:
            warnings.append("Rune Item section was not found; scanned the full Augment page for rune links.")
        elif runes:
            warnings.append("Rune Item section did not expose direct rune rows; scanned the full Augment page for rune links.")

    if not runes:
        warnings.append("Rune Item section was not found or did not contain rune links.")
    elif len(runes) < expected_count:
        warnings.append(f"Parsed {len(runes)} rune item links, expected {expected_count} from the Augment index label.")

    return {
        "sourceUrl": source_url,
        "source": "poe2db",
        "kind": "augment_index",
        "category": "rune",
        "catalogueSections": catalogue_sections,
        "entries": runes,
        "expectedCount": expected_count,
        "parseStatus": "ok",
        "warnings": warnings,
    }
