from __future__ import annotations

from poe2db_scraper.item_parser import parse_item_page


def _section(item: dict, kind: str) -> list[str]:
    for section in item["tooltipSections"]:
        if section["kind"] == kind:
            return section["lines"]
    return []


def test_treefingers_tooltip_is_not_tokenized(treefingers_html: str, urls: dict[str, str]) -> None:
    item = parse_item_page(urls["tree"], treefingers_html)

    assert item["id"] == "poe2db:Treefingers"
    assert item["slug"] == "Treefingers"
    assert item["name"] == "Treefingers"
    assert item["baseType"] == "Riveted Mitts"
    assert _section(item, "property") == ["Gloves", "Armour: (40-49)"]
    assert _section(item, "flavour") == ["The largest beings on Wraeclast", "are not flesh and blood."]


def test_treefingers_tooltip_does_not_leak_page_content(treefingers_html: str, urls: dict[str, str]) -> None:
    item = parse_item_page(urls["tree"], treefingers_html)
    lines = [line for section in item["tooltipSections"] for line in section["lines"]]

    for forbidden in ["Treefingers Attr /5", "Version history", "Family", '"realm": "poe2"', "Copyright"]:
        assert all(forbidden not in line for line in lines)


def test_treefingers_mods_are_separate_from_display_lines(treefingers_html: str, urls: dict[str, str]) -> None:
    item = parse_item_page(urls["tree"], treefingers_html)

    explicit = _section(item, "explicit")
    assert len(explicit) == 6
    assert len(item["mods"]) == 6
    physical = next(mod for mod in item["mods"] if mod["family"] == "PhysicalDamage")
    assert physical["stats"][0]["id"] == "attack maximum added physical damage"
    assert physical["stats"][0]["min"] == 12
    assert physical["stats"][0]["max"] == 16
