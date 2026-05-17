from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag

from .text import clean_display_text, split_csv, to_int


FIELD_LABELS = {
    "DropLevel",
    "BaseType",
    "Class",
    "Flags",
    "Type",
    "Tags",
    "Icon",
    "Currency Exchange",
    "NoteCode",
}

DOTTED_PREFIXES = (
    "Base.",
    "Mods.",
    "AttributeRequirements.",
    "Weapon.",
    "Quality.",
    "Sockets.",
)


def _row_cells(row: Tag) -> tuple[str, str] | None:
    cells = row.find_all(["td", "th"], recursive=False)
    if len(cells) < 2:
        return None
    key = clean_display_text(cells[0].get_text(" ", strip=True))
    value = clean_display_text(cells[1].get_text(" ", strip=True))
    if not key:
        return None
    return key, value


def _table_headers(table: Tag) -> list[str]:
    header_row = table.find("thead")
    if not header_row:
        return []
    return [clean_display_text(th.get_text(" ", strip=True)) for th in header_row.find_all("th")]


def collect_object_data_raw(soup: BeautifulSoup) -> dict[str, str]:
    """Collect object/data values from PoE2DB tables without including mod tables."""
    raw: dict[str, str] = {}

    for table in soup.select("table"):
        headers = _table_headers(table)
        if headers[:2] not in (["Name", "Show Full Descriptions"], ["key", "val"]):
            continue

        for row in table.select("tbody > tr"):
            parsed = _row_cells(row)
            if parsed is None:
                continue
            key, value = parsed
            if headers[:2] == ["Name", "Show Full Descriptions"]:
                if key in FIELD_LABELS:
                    raw[key] = value
            elif key.startswith(DOTTED_PREFIXES):
                raw[key] = value

    return raw


def normalize_object_data(raw: dict[str, str]) -> dict[str, Any]:
    data: dict[str, Any] = {}

    if (drop_level := to_int(raw.get("DropLevel"))) is not None:
        data["dropLevel"] = drop_level
    if raw.get("BaseType"):
        data["baseType"] = raw["BaseType"]
    if raw.get("Class"):
        data["class"] = raw["Class"]
    if raw.get("Type"):
        data["type"] = raw["Type"]
    if raw.get("Tags"):
        data["tags"] = split_csv(raw["Tags"])
    if raw.get("Icon"):
        data["icon"] = raw["Icon"]
    if raw.get("Currency Exchange"):
        data["currencyExchange"] = raw["Currency Exchange"]
    if raw.get("NoteCode"):
        data["noteCode"] = raw["NoteCode"]

    attr_map = {
        "AttributeRequirements.strength_requirement": "strengthRequirement",
        "AttributeRequirements.dexterity_requirement": "dexterityRequirement",
        "AttributeRequirements.intelligence_requirement": "intelligenceRequirement",
    }
    attrs: dict[str, int] = {}
    for raw_key, out_key in attr_map.items():
        value = to_int(raw.get(raw_key))
        if value is not None:
            attrs[out_key] = value
    if attrs:
        data["attributeRequirements"] = attrs

    weapon_map = {
        "Weapon.minimum_damage": "minimumDamage",
        "Weapon.maximum_damage": "maximumDamage",
        "Weapon.weapon_speed": "weaponSpeed",
        "Weapon.critical_chance": "criticalChance",
        "Weapon.minimum_attack_distance": "minimumAttackDistance",
        "Weapon.maximum_attack_distance": "maximumAttackDistance",
    }
    weapon: dict[str, int] = {}
    for raw_key, out_key in weapon_map.items():
        value = to_int(raw.get(raw_key))
        if value is not None:
            weapon[out_key] = value
    if weapon:
        data["weapon"] = weapon

    if raw.get("Sockets.socket_info"):
        data["sockets"] = {"raw": raw["Sockets.socket_info"]}

    quality = to_int(raw.get("Quality.max_quality"))
    if quality is not None:
        data["quality"] = {"maxQuality": quality}

    return data


def parse_object_data(soup: BeautifulSoup) -> tuple[dict[str, Any], dict[str, str]]:
    raw = collect_object_data_raw(soup)
    return normalize_object_data(raw), raw
