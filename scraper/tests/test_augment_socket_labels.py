from __future__ import annotations

from pathlib import Path

from poe2db_scraper.normal_affix_parser import parse_editor_modifier_pools_from_html


def test_augment_socket_options_are_fixed_rune_rows(project_root: Path) -> None:
    html = (project_root / 'data' / 'modifiers_calc_full' / 'Gloves_str.html').read_text(encoding='utf-8')
    pools = parse_editor_modifier_pools_from_html(
        html,
        source_url='https://poe2db.tw/us/Gloves_str#ModifiersCalc',
        item_class='Gloves',
        subtype='str',
        slug='Gloves_str',
    )
    augment_pool = next(pool for pool in pools if pool['sourceMechanic'] == 'augment')
    labels = [mod.get('pickerLabel') for mod in augment_pool['mods']]

    assert 'Lesser Desert Rune - +10% to Fire Resistance' in labels
    assert 'Desert Rune - +12% to Fire Resistance' in labels
    assert 'Greater Desert Rune - +14% to Fire Resistance' in labels
    assert all(mod['editableValues'] == [] for mod in augment_pool['mods'])
    assert all(mod.get('fixedValue') is True for mod in augment_pool['mods'])
