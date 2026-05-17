from __future__ import annotations

from poe2db_scraper.item_parser import parse_item_page


def _section(item: dict, kind: str) -> list[str]:
    for section in item["tooltipSections"]:
        if section["kind"] == kind:
            return section["lines"]
    return []


def test_crude_claw_display_properties_stay_as_lines(crude_claw_html: str, urls: dict[str, str]) -> None:
    item = parse_item_page(urls["claw"], crude_claw_html)

    assert item["id"] == "poe2db:Crude_Claw"
    assert item["name"] == "Crude Claw"
    assert item["baseType"] == "Crude Claw"
    assert _section(item, "property") == [
        "Claws",
        "Physical Damage: 4-10",
        "Critical Hit Chance: 5%",
        "Attacks per Second: 1.65",
        "Weapon Range: 1.1",
    ]


def test_crude_claw_object_and_normalized_weapon_data(crude_claw_html: str, urls: dict[str, str]) -> None:
    item = parse_item_page(urls["claw"], crude_claw_html)

    assert item["objectData"]["weapon"]["minimumDamage"] == 5
    assert item["objectData"]["weapon"]["maximumDamage"] == 10
    assert item["normalized"]["weapon"]["physicalDamage"] == {"min": 4, "max": 10}
    assert item["normalized"]["weapon"]["criticalHitChance"] == 5.0
    assert item["normalized"]["weapon"]["attacksPerSecond"] == 1.65
