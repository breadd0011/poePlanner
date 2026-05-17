from __future__ import annotations

from poe2db_scraper.augment_parser import parse_augment_page


def test_desert_rune_has_six_non_empty_effects(desert_rune_html, urls) -> None:
    augment = parse_augment_page(urls["rune"], desert_rune_html)
    effects = [s for s in augment["tooltipSections"] if s["kind"] == "augment_effect"]

    assert augment["id"] == "poe2db:Desert_Rune"
    assert augment["name"] == "Desert Rune"
    assert len(effects) == 6
    assert sum(1 for effect in effects if not effect["bonded"]) == 3
    assert sum(1 for effect in effects if effect["bonded"]) == 3
    assert all(effect["lines"] and effect["lines"][0].strip() for effect in effects)
    assert len(augment["augmentEffects"]) == 6


def test_desert_rune_description_is_not_empty(desert_rune_html, urls) -> None:
    augment = parse_augment_page(urls["rune"], desert_rune_html)
    description = next(section for section in augment["tooltipSections"] if section["kind"] == "description")

    assert description["lines"] == [
        "Place into an empty Augment Socket in a Weapon or Armour to apply its effect to that item.",
        "Once socketed it cannot be retrieved but can be replaced by other Augment items.",
    ]
