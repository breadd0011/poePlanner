from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .unique_gloves_parser import WEAPON_UNIQUE_CLASS_URL_SLUGS

ModifierSupportState = Literal["required", "experimental", "unsupported"]


@dataclass(frozen=True)
class ModifierClassSupport:
    item_class: str
    support_state: ModifierSupportState
    require_editor_pools: bool = False
    require_normal_explicit_pools: bool = False
    note: str = ""


# Armour classes are parsed from the six attribute-profile subtype pages.
ARMOUR_MODIFIER_ITEM_CLASSES: tuple[str, ...] = ("Gloves", "Boots", "Helmets")

# Body Armours use the same six attribute-profile subtype pattern as armour
# gloves/boots/helmets, but they are not part of the legacy itemSubtypes payload.
# The UI derives the applicable subtype from the selected base item defences.
BODY_ARMOUR_MODIFIER_ITEM_CLASSES: tuple[str, ...] = ("Body Armours",)

# Shields expose ModifiersCalc on Shield subtype pages rather than on /Shields.
# Keep this separate from armour because the planner treats Shields as one item
# class but derives the applicable modifier subtype from the selected base item.
SHIELD_MODIFIER_ITEM_CLASSES: tuple[str, ...] = ("Shields",)

# Class-level non-armour/offhand/utility pipeline. These pages expose their
# ModifiersCalc table directly on the class page, not on str/dex/int subtype pages.
UTILITY_MODIFIER_ITEM_CLASSES: tuple[str, ...] = ("Life Flasks", "Mana Flasks", "Charms")
CLASS_LEVEL_MODIFIER_ITEM_CLASSES: tuple[str, ...] = (
    "Rings",
    "Amulets",
    "Belts",
    "Foci",
    "Quivers",
    *UTILITY_MODIFIER_ITEM_CLASSES,
)

# PoE2DB's current Modifiers index lists these under One Handed Weapons and Two
# Handed Weapons, with Talismans exposed as a weapon-like class page. Traps are
# intentionally out of scope for this planner and are not refreshed, audited, or
# offered in the UI.
WEAPON_MODIFIER_CLASS_URL_SLUGS: dict[str, str] = dict(WEAPON_UNIQUE_CLASS_URL_SLUGS)
WEAPON_MODIFIER_ITEM_CLASSES: tuple[str, ...] = tuple(WEAPON_MODIFIER_CLASS_URL_SLUGS)
EXPERIMENTAL_WEAPON_MODIFIER_ITEM_CLASSES: tuple[str, ...] = ()
SUPPORTED_WEAPON_MODIFIER_ITEM_CLASSES: tuple[str, ...] = WEAPON_MODIFIER_ITEM_CLASSES

# Class-level pages that are production inputs for editorModifierPools and
# normalExplicitPools. Armour/body/shield subtype pages remain configured
# separately because they derive one pool per defence/attribute profile.
CLASS_LEVEL_PRODUCTION_MODIFIER_ITEM_CLASSES: tuple[str, ...] = (
    *CLASS_LEVEL_MODIFIER_ITEM_CLASSES,
    *SUPPORTED_WEAPON_MODIFIER_ITEM_CLASSES,
)

# Weapon-class audits keep source URL and snapshot status visible in health
# reports even after the supported weapon classes are promoted to production.
AUDITED_MODIFIER_CLASSES: tuple[str, ...] = WEAPON_MODIFIER_ITEM_CLASSES

# Missing pools for these classes should fail the health report because the
# editor is expected to offer selectable modifiers for all supported classes.
REQUIRED_MODIFIER_CLASSES: tuple[str, ...] = (
    *ARMOUR_MODIFIER_ITEM_CLASSES,
    *BODY_ARMOUR_MODIFIER_ITEM_CLASSES,
    *SHIELD_MODIFIER_ITEM_CLASSES,
    *CLASS_LEVEL_MODIFIER_ITEM_CLASSES,
    *SUPPORTED_WEAPON_MODIFIER_ITEM_CLASSES,
)

# Experimental modifier targets are audited but do not fail payload health while
# they are being investigated. Empty when every in-scope modifier class is either
# required or unsupported.
EXPERIMENTAL_MODIFIER_CLASSES: tuple[str, ...] = EXPERIMENTAL_WEAPON_MODIFIER_ITEM_CLASSES

# Item classes that must not surface in the Simple Item Editor even if PoE2DB
# exposes a class page. Traps are intentionally excluded from this planner.
EXCLUDED_ITEM_EDITOR_CLASSES: tuple[str, ...] = ("Traps",)


MODIFIER_CLASS_SUPPORT: dict[str, ModifierClassSupport] = {
    **{
        item_class: ModifierClassSupport(
            item_class=item_class,
            support_state="required",
            require_editor_pools=True,
            require_normal_explicit_pools=True,
            note="Armour subtype modifier pipeline is production-required for the current planner UI.",
        )
        for item_class in ARMOUR_MODIFIER_ITEM_CLASSES
    },
    **{
        item_class: ModifierClassSupport(
            item_class=item_class,
            support_state="required",
            require_editor_pools=True,
            require_normal_explicit_pools=True,
            note="Body Armour subtype modifier pipeline is production-required once Body Armours are available in baseItems/uniqueItems.",
        )
        for item_class in BODY_ARMOUR_MODIFIER_ITEM_CLASSES
    },
    **{
        item_class: ModifierClassSupport(
            item_class=item_class,
            support_state="required",
            require_editor_pools=True,
            require_normal_explicit_pools=True,
            note="Shield subtype modifier pipeline is production-required once Shields are available in baseItems/uniqueItems.",
        )
        for item_class in SHIELD_MODIFIER_ITEM_CLASSES
    },
    **{
        item_class: ModifierClassSupport(
            item_class=item_class,
            support_state="required",
            require_editor_pools=True,
            require_normal_explicit_pools=True,
            note="Class-level non-armour/offhand modifier pipeline is production-required once this item class is available in baseItems/uniqueItems.",
        )
        for item_class in CLASS_LEVEL_MODIFIER_ITEM_CLASSES
    },
    **{
        item_class: ModifierClassSupport(
            item_class=item_class,
            support_state="required",
            require_editor_pools=True,
            require_normal_explicit_pools=True,
            note="Class-level weapon modifier pipeline is production-required for the current planner UI.",
        )
        for item_class in SUPPORTED_WEAPON_MODIFIER_ITEM_CLASSES
    },
    **{
        item_class: ModifierClassSupport(
            item_class=item_class,
            support_state="experimental",
            require_editor_pools=False,
            require_normal_explicit_pools=False,
            note="Weapon-adjacent modifier audit target. Coverage is reported from PoE2DB class pages, but pools are not wired into the planner UI until slot semantics are decided.",
        )
        for item_class in EXPERIMENTAL_MODIFIER_CLASSES
    },
}


def modifier_class_slug(item_class: str) -> str | None:
    return WEAPON_MODIFIER_CLASS_URL_SLUGS.get(item_class)


def modifier_class_url(item_class: str) -> str | None:
    slug = modifier_class_slug(item_class)
    return f"https://poe2db.tw/us/{slug}" if slug else None


def modifier_source_url(item_class: str) -> str | None:
    class_url = modifier_class_url(item_class)
    return f"{class_url}#ModifiersCalc" if class_url else None


def modifier_support_for_class(item_class: str) -> ModifierClassSupport:
    canonical = str(item_class or "Unknown")
    return MODIFIER_CLASS_SUPPORT.get(
        canonical,
        ModifierClassSupport(
            item_class=canonical,
            support_state="unsupported",
            note="No modifier parser support requirement is configured for this item class yet.",
        ),
    )
