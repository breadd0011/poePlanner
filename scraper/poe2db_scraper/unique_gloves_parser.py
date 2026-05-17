from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from .item_parser import parse_item_page
from .text import clean_display_text, get_page_lines_from_html, slug_from_url


@dataclass(frozen=True)
class UniqueGloveCandidate:
    name: str
    baseType: str | None
    sourceUrl: str
    label: str


@dataclass(frozen=True)
class UniqueItemMeta:
    item_class: str
    pane_id: str
    kind: str
    id_prefix: str
    icon_folder: str


UNIQUE_ITEM_META: dict[str, UniqueItemMeta] = {
    "Gloves": UniqueItemMeta("Gloves", "GlovesUnique", "unique_glove", "unique_gloves", "Gloves"),
    "Boots": UniqueItemMeta("Boots", "BootsUnique", "unique_boot", "unique_boots", "Boots"),
    "Helmets": UniqueItemMeta("Helmets", "HelmetsUnique", "unique_helmet", "unique_helmets", "Helmets"),
    "Body Armours": UniqueItemMeta("Body Armours", "BodyArmoursUnique", "unique_item", "unique_body_armours", "BodyArmours"),
    "Shields": UniqueItemMeta("Shields", "ShieldsUnique", "unique_item", "unique_shields", "Shields"),
    "Foci": UniqueItemMeta("Foci", "FociUnique", "unique_item", "unique_foci", "Foci"),
    "Quivers": UniqueItemMeta("Quivers", "QuiversUnique", "unique_item", "unique_quivers", "Quivers"),
    "Rings": UniqueItemMeta("Rings", "RingsUnique", "unique_item", "unique_rings", "Rings"),
    "Amulets": UniqueItemMeta("Amulets", "AmuletsUnique", "unique_item", "unique_amulets", "Amulets"),
    "Belts": UniqueItemMeta("Belts", "BeltsUnique", "unique_item", "unique_belts", "Belts"),
}
UNIQUE_ARMOUR_META = UNIQUE_ITEM_META

UNIQUE_ITEM_CLASS_URL_SLUGS: dict[str, str] = {
    "Gloves": "Gloves",
    "Boots": "Boots",
    "Helmets": "Helmets",
    "Body Armours": "Body_Armours",
    "Shields": "Shields",
    "Foci": "Foci",
    "Quivers": "Quivers",
    "Rings": "Rings",
    "Amulets": "Amulets",
    "Belts": "Belts",
    "Life Flasks": "Life_Flasks",
    "Mana Flasks": "Mana_Flasks",
    "Charms": "Charms",
}

# PoE2DB does not expose a useful single /Weapons catalogue. Treat
# "Weapons" as a convenience alias that refreshes/audits the concrete weapon
# class pages currently listed by PoE2DB. Some classes may have zero uniques.
WEAPON_UNIQUE_CLASS_URL_SLUGS: dict[str, str] = {
    "Claws": "Claws",
    "Daggers": "Daggers",
    "Wands": "Wands",
    "One Hand Swords": "One_Hand_Swords",
    "One Hand Axes": "One_Hand_Axes",
    "One Hand Maces": "One_Hand_Maces",
    "Sceptres": "Sceptres",
    "Spears": "Spears",
    "Flails": "Flails",
    "Bows": "Bows",
    "Staves": "Staves",
    "Two Hand Swords": "Two_Hand_Swords",
    "Two Hand Axes": "Two_Hand_Axes",
    "Two Hand Maces": "Two_Hand_Maces",
    "Quarterstaves": "Quarterstaves",
    "Crossbows": "Crossbows",
    "Talismans": "Talismans",
}
SUPPORTED_POE2DB_LOCALES = {"us", "tw", "cn", "kr", "jp", "fr", "de", "ru", "es", "pt", "th"}
NAV_OR_KEYWORD_SLUGS = {
    "gloves", "boots", "helmets", "item-classes", "unique", "item", "items", "armour", "armor",
    "attacks", "spells", "skills", "skill_gems", "support_gems", "physical_damage", "fire_damage",
    "cold_damage", "lightning_damage", "chaos_damage",
}


def stable_slug(*parts: str) -> str:
    raw = "_".join(str(part) for part in parts if str(part).strip()).replace("'", "")
    raw = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").lower()
    return raw or "unknown"


def normalize_poe2db_item_url(source_url: str, href: str) -> str | None:
    raw = str(href or "").strip()
    if not raw or raw.startswith("#") or raw.startswith("javascript:"):
        return None
    parsed_raw = urlparse(raw)
    if parsed_raw.scheme and parsed_raw.netloc and "poe2db.tw" not in parsed_raw.netloc:
        return None
    raw_parts = parsed_raw.path.strip("/").split("/") if parsed_raw.path.strip("/") else []
    if raw_parts and raw_parts[0] in SUPPORTED_POE2DB_LOCALES and raw_parts[0] != "us":
        return None
    parsed = urlparse(urljoin(source_url, raw))
    if "poe2db.tw" not in parsed.netloc:
        return None
    parts = parsed.path.strip("/").split("/") if parsed.path.strip("/") else []
    if not parts:
        return None
    if parts[0] in SUPPORTED_POE2DB_LOCALES:
        if parts[0] != "us":
            return None
        slug = "/".join(parts[1:])
    else:
        slug = "/".join(parts)
    slug = unquote(slug).strip()
    if not slug or "/" in slug or slug.lower() in NAV_OR_KEYWORD_SLUGS:
        return None
    return f"https://poe2db.tw/us/{slug}"


def unique_icon_asset_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", name) or "Unknown"


def unique_glove_icon_path(name: str) -> str:
    return unique_armour_icon_path("Gloves", name)


def unique_armour_icon_path(item_class: str, name: str) -> str:
    folder = _meta_for(item_class).icon_folder
    return f"Art/2DItems/Armours/{folder}/Uniques/{unique_icon_asset_name(name)}"


def unique_name_to_url_slug(name: str) -> str:
    cleaned = str(name).strip().replace("'", "")
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", cleaned)
    return re.sub(r"_+", "_", cleaned).strip("_")


def split_unique_label(label: str, base_item_names: list[str]) -> tuple[str, str | None]:
    label = clean_display_text(label)
    for base in sorted(base_item_names, key=len, reverse=True):
        if label == base:
            continue
        suffix = " " + base
        if label.endswith(suffix):
            return label[: -len(suffix)].strip(), base
    return label, None


def _dedupe_candidates(candidates: list[UniqueGloveCandidate]) -> list[UniqueGloveCandidate]:
    seen: set[str] = set()
    out: list[UniqueGloveCandidate] = []
    for candidate in candidates:
        if candidate.sourceUrl in seen:
            continue
        seen.add(candidate.sourceUrl)
        out.append(candidate)
    return out


def _meta_for(item_class: str) -> UniqueItemMeta:
    configured = UNIQUE_ITEM_META.get(item_class)
    if configured is not None:
        return configured
    compact = re.sub(r"[^A-Za-z0-9]+", "", item_class) or item_class
    return UniqueItemMeta(
        item_class=item_class,
        pane_id=f"{compact}Unique",
        kind="unique_item",
        id_prefix=f"unique_{stable_slug(item_class)}",
        icon_folder=compact,
    )


def _soup(html: str) -> BeautifulSoup:
    # Avoid native lxml crashes on very large catalogue DOMs.
    return BeautifulSoup(html, "html.parser")


def _unique_pane(soup: BeautifulSoup, meta: UniqueItemMeta) -> Tag | None:
    pane = soup.select_one(f"#{meta.pane_id}")
    if isinstance(pane, Tag):
        return pane
    for pattern in (
        rf"{re.escape(meta.item_class)}\s+Unique\s*/\d+",
        r"Unique\s*/\d+",
    ):
        heading = soup.find(string=re.compile(pattern, re.I))
        current = heading.parent if heading and isinstance(heading.parent, Tag) else None
        while current is not None:
            if current.select(".uniqueName"):
                return current
            current = current.parent if isinstance(current.parent, Tag) else None
    return None


def _unique_cards(pane: Tag) -> list[Tag]:
    rows: list[Tag] = []
    seen_ids: set[int] = set()
    for anchor in pane.select("a.uniqueitem"):
        row = anchor.find_parent("div", class_="d-flex")
        if not isinstance(row, Tag):
            continue
        if not row.select_one(".uniqueName") or not row.select_one(".uniqueTypeLine"):
            continue
        row_id = id(row)
        if row_id in seen_ids:
            continue
        seen_ids.add(row_id)
        rows.append(row)
    return rows


def _node_text(node: Tag | None) -> str:
    return clean_display_text(node.get_text(" ", strip=True)) if node is not None else ""


def _lines(row: Tag, selector: str) -> list[str]:
    out: list[str] = []
    for node in row.select(selector):
        text = _node_text(node)
        if text and text not in out:
            out.append(text)
    return out


def _icon_from_row(row: Tag, item_class: str, name: str) -> str:
    img = row.select_one("img[src]")
    src = str(img.get("src") or "") if isinstance(img, Tag) else ""
    if src:
        path = unquote(urlparse(src).path)
        if "/image/" in path:
            asset = path.split("/image/", 1)[1]
            asset = re.sub(r"\.(webp|png|jpg|jpeg)$", "", asset, flags=re.I)
            if asset.startswith("Art/"):
                return asset
    return unique_armour_icon_path(item_class, name)


def _mod_section(kind: str, values: list[str]) -> dict[str, Any] | None:
    lines = [clean_display_text(value) for value in values if clean_display_text(value)]
    return {"kind": kind, "lines": lines} if lines else None


def _catalogue_item(source_url: str, row: Tag, meta: UniqueItemMeta) -> dict[str, Any] | None:
    name_node = row.select_one(".uniqueName")
    base_node = row.select_one(".uniqueTypeLine")
    name = _node_text(name_node)
    base_type = _node_text(base_node)
    if not name or not base_type:
        return None
    link = name_node.find_parent("a", href=True) if isinstance(name_node, Tag) else None
    item_url = normalize_poe2db_item_url(source_url, str(link.get("href") or "")) if isinstance(link, Tag) else None
    item_url = item_url or f"https://poe2db.tw/us/{unique_name_to_url_slug(name)}"
    unique_slug = stable_slug(name)
    implicit_mods = _lines(row, ".implicitMod")
    explicit_mods = _lines(row, ".explicitMod")
    flavour_text = _lines(row, ".flavourText, .flavour")
    tooltip_sections = [section for section in (_mod_section("implicit", implicit_mods), _mod_section("explicit", explicit_mods), _mod_section("flavour", flavour_text)) if section]
    return {
        "id": f"{meta.id_prefix}_{unique_slug}",
        "slug": slug_from_url(item_url) or unique_name_to_url_slug(name),
        "source": "poe2db",
        "sourceUrl": item_url,
        "kind": meta.kind,
        "name": name,
        "baseType": base_type,
        "itemClass": meta.item_class,
        "rarity": "Unique",
        "icon": _icon_from_row(row, meta.item_class, name),
        "requirements": {},
        "defences": {},
        "implicitMods": [{"id": f"{meta.id_prefix}_{unique_slug}_implicit_{i:03d}", "text": text} for i, text in enumerate(implicit_mods, start=1)],
        "explicitMods": [{"id": f"{meta.id_prefix}_{unique_slug}_explicit_{i:03d}", "text": text} for i, text in enumerate(explicit_mods, start=1)],
        "flavourText": flavour_text,
        "tooltipSections": tooltip_sections,
        "parseStatus": "ok",
        "warnings": [],
        "diagnostics": [{"severity": "info", "code": "CATALOGUE_UNIQUE_ARMOUR_ROW", "message": f"Imported {meta.item_class} unique from the PoE2DB {meta.item_class} Unique catalogue row.", "actionRequired": False}],
    }


def extract_unique_catalogue_items(source_url: str, html: str, *, item_class: str) -> list[dict[str, Any]]:
    meta = _meta_for(item_class)
    pane = _unique_pane(_soup(html), meta)
    if pane is None:
        return []
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in _unique_cards(pane):
        item = _catalogue_item(source_url, row, meta)
        if not item:
            continue
        key = str(item.get("sourceUrl") or item.get("name"))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def extract_unique_armour_candidates(source_url: str, html: str, *, item_class: str) -> list[UniqueGloveCandidate]:
    return _dedupe_candidates([
        UniqueGloveCandidate(
            name=str(item.get("name") or ""),
            baseType=str(item.get("baseType") or "") or None,
            sourceUrl=str(item.get("sourceUrl") or ""),
            label=f"{item.get('name')} {item.get('baseType') or ''}".strip(),
        )
        for item in extract_unique_catalogue_items(source_url, html, item_class=item_class)
        if item.get("name") and item.get("sourceUrl")
    ])


def _section_text_lines(html: str, item_class: str = "Gloves") -> list[str]:
    lines = get_page_lines_from_html(html)
    unique_lines: list[str] = []
    in_unique = False
    for line in lines:
        if re.match(rf"#####\s+{re.escape(item_class)}\s+Unique", line):
            in_unique = True
            continue
        if in_unique and line.startswith("##### "):
            break
        if in_unique and line not in {"Reset", "Name", "Base", "Item", "Level"} and not line.startswith("Image:"):
            unique_lines.append(line)
    return unique_lines


def extract_unique_glove_candidates(source_url: str, html: str, base_item_names: list[str]) -> list[UniqueGloveCandidate]:
    candidates = extract_unique_armour_candidates(source_url, html, item_class="Gloves")
    if candidates:
        return candidates
    fallback: list[UniqueGloveCandidate] = []
    for label in _section_text_lines(html, "Gloves"):
        if any(marker in label for marker in ["%", "Adds ", "Gain ", "Cannot ", "Requires:", "Armour:", "Evasion", "Energy Shield"]):
            continue
        name, base = split_unique_label(label, base_item_names)
        if name and not (name == label and base is None):
            fallback.append(UniqueGloveCandidate(name, base, f"https://poe2db.tw/us/{unique_name_to_url_slug(name)}", label))
    return _dedupe_candidates(fallback)


def _section_lines(item: dict[str, Any], kind: str) -> list[str]:
    for section in item.get("tooltipSections", []):
        if section.get("kind") == kind:
            return list(section.get("lines") or [])
    return []


def _fallback_lines(fallback: dict[str, Any] | None, key: str) -> list[str]:
    if not fallback:
        return []
    values = fallback.get(key) or []
    if key.endswith("Mods"):
        return [str(mod.get("text") or "") for mod in values if isinstance(mod, dict) and mod.get("text")]
    return [str(value) for value in values if str(value).strip()]


def parse_unique_armour_page(source_url: str, html: str, *, item_class: str, kind: str, id_prefix: str, expected_base_type: str | None = None, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    item = parse_item_page(source_url, html)
    name = str(item.get("name") or "").strip()
    if not name or name == "Unknown Item":
        name = str((fallback or {}).get("name") or "").strip()
    base_type = str(item.get("baseType") or expected_base_type or (fallback or {}).get("baseType") or "").strip() or None
    explicit = _section_lines(item, "explicit") or _fallback_lines(fallback, "explicitMods")
    implicit = _section_lines(item, "implicit") or _fallback_lines(fallback, "implicitMods")
    flavour = _section_lines(item, "flavour") or _fallback_lines(fallback, "flavourText")
    tooltip_sections = list(item.get("tooltipSections") or [])
    if fallback and (not tooltip_sections or not explicit):
        tooltip_sections = [section for section in (_mod_section("implicit", implicit), _mod_section("explicit", explicit), _mod_section("flavour", flavour)) if section]
    normalized = item.get("normalized") or {}
    unique_slug = stable_slug(name)
    return {
        "id": f"{id_prefix}_{unique_slug}",
        "slug": slug_from_url(source_url),
        "source": "poe2db",
        "sourceUrl": source_url,
        "kind": kind,
        "name": name,
        "baseType": base_type,
        "itemClass": item_class,
        "rarity": item.get("rarity") or "Unique",
        "icon": item.get("icon") or (fallback or {}).get("icon") or unique_armour_icon_path(item_class, name),
        "requirements": dict(normalized.get("requirements") or (fallback or {}).get("requirements") or {}),
        "defences": dict(normalized.get("defences") or (fallback or {}).get("defences") or {}),
        "implicitMods": [{"id": f"{id_prefix}_{unique_slug}_implicit_{i:03d}", "text": clean_display_text(text)} for i, text in enumerate(implicit, start=1) if clean_display_text(text)],
        "explicitMods": [{"id": f"{id_prefix}_{unique_slug}_explicit_{i:03d}", "text": clean_display_text(text)} for i, text in enumerate(explicit, start=1) if clean_display_text(text)],
        "flavourText": flavour,
        "tooltipSections": tooltip_sections,
        "parseStatus": item.get("parseStatus") or "ok",
        "warnings": list(item.get("warnings") or []),
        "diagnostics": list(item.get("diagnostics") or []),
    }


def parse_unique_item_page(source_url: str, html: str, *, item_class: str, expected_base_type: str | None = None, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = _meta_for(item_class)
    return parse_unique_armour_page(
        source_url,
        html,
        item_class=meta.item_class,
        kind=meta.kind,
        id_prefix=meta.id_prefix,
        expected_base_type=expected_base_type or (fallback or {}).get("baseType"),
        fallback=fallback,
    )


def parse_unique_glove_page(source_url: str, html: str, *, expected_base_type: str | None = None, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    return parse_unique_item_page(source_url, html, item_class="Gloves", expected_base_type=expected_base_type, fallback=fallback)


def parse_unique_boot_page(source_url: str, html: str, *, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    return parse_unique_item_page(source_url, html, item_class="Boots", expected_base_type=(fallback or {}).get("baseType"), fallback=fallback)


def parse_unique_helmet_page(source_url: str, html: str, *, expected_base_type: str | None = None, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    return parse_unique_item_page(source_url, html, item_class="Helmets", expected_base_type=expected_base_type, fallback=fallback)
