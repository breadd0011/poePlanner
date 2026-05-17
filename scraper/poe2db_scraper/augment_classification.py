from __future__ import annotations

from typing import Any

RUNE_ITEM_SECTION_LABEL = "Rune Item"
REFERENCE_AUGMENT_SECTIONS = {"Augment Ref", "Rune Ref", "SoulCore Ref"}
SOCKET_AUGMENT_EQUIPMENT_CONDITIONS = {"martial_weapon", "wand_or_staff", "armour", "all_equipment"}


def classify_augment_catalogue_entry(section_label: str, name: str) -> str:
    """Classify an Augment catalogue entry using one shared scraper policy."""
    if section_label == RUNE_ITEM_SECTION_LABEL:
        return "rune_item"
    if "Soul Core" in name or "SoulCore" in name:
        return "soul_core"
    if section_label.endswith("Ref"):
        return "reference"
    if name.endswith(" Rune"):
        return "rune_like_augment"
    return "augment_item"


def classify_augment_name(name: str) -> str:
    """Best-effort classification when only a row/name is available."""
    stripped = str(name or "").strip()
    if "Soul Core" in stripped or "SoulCore" in stripped:
        return "soul_core"
    if stripped.endswith(" Rune"):
        return "rune_item"
    return "augment_item"


def _description_lines(augment: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for section in augment.get("tooltipSections") or []:
        if isinstance(section, dict) and section.get("kind") == "description":
            lines.extend(str(line) for line in section.get("lines") or [])
    return lines


def _normal_conditions(augment: dict[str, Any]) -> set[str]:
    return {
        str(effect.get("condition"))
        for effect in augment.get("augmentEffects") or []
        if isinstance(effect, dict) and effect.get("condition") and not effect.get("bonded")
    }


def socket_candidate_reason(entry: dict[str, Any], augment: dict[str, Any] | None = None) -> str | None:
    """Return why a catalogue augment should be usable in item Augment sockets.

    This intentionally follows the game/PoE2DB data instead of a UI-only allow
    list: actual item entries with equipment-targeted augment effects or an
    Augment Socket usage description are admitted; reference sections stay out.
    """
    category = str(entry.get("category") or "")
    section = str(entry.get("section") or "")
    if category == "reference" or section.endswith("Ref"):
        return None
    if category == "rune_item":
        return "rune_item_section"
    if augment is None:
        return None

    descriptions = " ".join(_description_lines(augment)).lower()
    if "augment socket" in descriptions and ("weapon" in descriptions or "armour" in descriptions or "armor" in descriptions):
        return "augment_socket_description"

    normal_conditions = _normal_conditions(augment)
    if normal_conditions & SOCKET_AUGMENT_EQUIPMENT_CONDITIONS:
        augment_name = str(augment.get("name") or "")
        if category == "soul_core" or "soul core" in augment_name.lower():
            return "soul_core_equipment_effects"
        return "equipment_targeted_effects"
    return None


def with_socket_candidate_fields(entry: dict[str, Any], reason: str | None) -> dict[str, Any]:
    updated = dict(entry)
    updated["socketCandidate"] = bool(reason)
    updated["socketCandidateReason"] = reason
    updated["plannerVisibility"] = "socket_picker" if reason else "catalogue_only"
    return updated
