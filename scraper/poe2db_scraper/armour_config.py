from __future__ import annotations

from dataclasses import dataclass

POE2DB_BASE_URL = "https://poe2db.tw/us"

# These are planner-supported armour classes. The actual item/base/unique rows are
# still parsed from PoE2DB; this list only defines which class pages the POC loads.
ARMOUR_ITEM_CLASSES: tuple[str, ...] = ("Gloves", "Boots", "Helmets")

# PoE2DB uses the same six armour attribute-profile subtype slugs for these pages.
ARMOUR_SUBTYPE_PROFILES: tuple[tuple[str, tuple[str, ...], tuple[str, ...], str], ...] = (
    ("str", ("str",), ("armour",), "Strength"),
    ("dex", ("dex",), ("evasion",), "Dexterity"),
    ("int", ("int",), ("energy_shield",), "Intelligence"),
    ("str_dex", ("str", "dex"), ("armour", "evasion"), "Strength/Dexterity"),
    ("str_int", ("str", "int"), ("armour", "energy_shield"), "Strength/Intelligence"),
    ("dex_int", ("dex", "int"), ("evasion", "energy_shield"), "Dexterity/Intelligence"),
)


@dataclass(frozen=True)
class ArmourClassConfig:
    item_class: str
    class_url: str
    subtype_urls: tuple[str, ...]


def armour_class_url(item_class: str) -> str:
    return f"{POE2DB_BASE_URL}/{item_class}"


def armour_subtype_slug(item_class: str, subtype: str) -> str:
    return f"{item_class}_{subtype}"


def armour_subtype_url(item_class: str, subtype: str) -> str:
    return f"{POE2DB_BASE_URL}/{armour_subtype_slug(item_class, subtype)}"


def armour_subtype_meta(item_class: str, subtype: str) -> dict[str, object]:
    for profile, attributes, defences, label_prefix in ARMOUR_SUBTYPE_PROFILES:
        if profile == subtype:
            return {
                "itemClass": item_class,
                "subtype": subtype,
                "label": f"{label_prefix} {item_class}",
                "attributeProfile": list(attributes),
                "defenceProfile": list(defences),
            }
    return {
        "itemClass": item_class,
        "subtype": subtype,
        "label": f"{item_class} {subtype}",
        "attributeProfile": subtype.split("_"),
        "defenceProfile": [],
    }


def armour_class_configs() -> tuple[ArmourClassConfig, ...]:
    return tuple(
        ArmourClassConfig(
            item_class=item_class,
            class_url=armour_class_url(item_class),
            subtype_urls=tuple(armour_subtype_url(item_class, profile[0]) for profile in ARMOUR_SUBTYPE_PROFILES),
        )
        for item_class in ARMOUR_ITEM_CLASSES
    )


def armour_subtype_meta_by_slug() -> dict[str, dict[str, object]]:
    return {
        armour_subtype_slug(item_class, profile): armour_subtype_meta(item_class, profile)
        for item_class in ARMOUR_ITEM_CLASSES
        for profile, _, _, _ in ARMOUR_SUBTYPE_PROFILES
    }
