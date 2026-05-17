from __future__ import annotations

import re
from typing import Any

from .text import slug_from_url


def entity_id(source_url: str) -> str:
    return f"poe2db:{slug_from_url(source_url)}"


def slug(source_url: str) -> str:
    return slug_from_url(source_url)


def parse_requirement_line(line: str | None) -> dict[str, int | None]:
    out: dict[str, int | None] = {"level": None, "str": None, "dex": None, "int": None}
    if not line:
        return out
    text = line.replace("Requires:", "")
    if m := re.search(r"Level\s+(\d+)", text):
        out["level"] = int(m.group(1))
    for label, key in (("Str", "str"), ("Dex", "dex"), ("Int", "int")):
        if m := re.search(rf"(\d+)\s+{label}\b", text):
            out[key] = int(m.group(1))
    return out


def parse_int_range(text: str) -> dict[str, int | None] | None:
    if m := re.search(r"\(([-+]?\d+)\s*[—-]\s*([-+]?\d+)\)", text):
        return {"min": int(m.group(1)), "max": int(m.group(2))}
    if m := re.search(r"\b([-+]?\d+)\s*[—-]\s*([-+]?\d+)\b", text):
        return {"min": int(m.group(1)), "max": int(m.group(2))}
    if m := re.search(r"\b([-+]?\d+)\b", text):
        value = int(m.group(1))
        return {"min": value, "max": value}
    return None


def section_lines(sections: list[dict[str, Any]], kind: str) -> list[str]:
    for section in sections:
        if section.get("kind") == kind:
            return list(section.get("lines") or [])
    return []


def normalized_item_fields(sections: list[dict[str, Any]], object_data: dict[str, Any]) -> dict[str, Any]:
    requirements = parse_requirement_line(next(iter(section_lines(sections, "requirement")), None))
    normalized: dict[str, Any] = {"requirements": requirements}

    properties = section_lines(sections, "property")
    defences: dict[str, Any] = {}
    weapon: dict[str, Any] = {}

    for line in properties:
        if line.startswith("Armour:"):
            parsed = parse_int_range(line)
            if parsed:
                defences["armour"] = parsed
        elif line.startswith("Evasion Rating:") or line.startswith("Evasion:"):
            parsed = parse_int_range(line)
            if parsed:
                defences["evasion"] = parsed
        elif line.startswith("Energy Shield:"):
            parsed = parse_int_range(line)
            if parsed:
                defences["energyShield"] = parsed
        elif line.startswith("Physical Damage:"):
            parsed = parse_int_range(line)
            if parsed:
                weapon["physicalDamage"] = parsed
        elif line.startswith("Critical Hit Chance:"):
            if m := re.search(r"([\d.]+)%", line):
                weapon["criticalHitChance"] = float(m.group(1))
        elif line.startswith("Attacks per Second:"):
            if m := re.search(r"([\d.]+)", line):
                weapon["attacksPerSecond"] = float(m.group(1))
        elif line.startswith("Weapon Range:"):
            if m := re.search(r"([\d.]+)", line):
                weapon["weaponRange"] = float(m.group(1))

    if defences:
        normalized["defences"] = defences
    if weapon:
        normalized["weapon"] = weapon

    # Keep raw object weapon data close to normalized display stats for future planner math.
    if object_data.get("weapon"):
        normalized["objectWeapon"] = object_data["weapon"]
    if object_data.get("attributeRequirements"):
        normalized["objectAttributeRequirements"] = object_data["attributeRequirements"]

    return normalized


def normalized_augment_effects(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    effects: list[dict[str, Any]] = []
    for section in sections:
        if section.get("kind") != "augment_effect":
            continue
        effects.append(
            {
                "condition": section.get("condition"),
                "bonded": bool(section.get("bonded")),
                "text": " ".join(section.get("lines") or []).strip(),
            }
        )
    return effects


def stable_id(*parts: str) -> str:
    raw = "_".join(str(part) for part in parts if str(part).strip())
    raw = raw.replace("'", "")
    raw = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").lower()
    return raw or "unknown"
