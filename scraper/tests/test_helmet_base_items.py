from pathlib import Path

from poe2db_scraper.subtype_parser import parse_subtype_page


def _read_fixture(project_root: Path, slug: str) -> str:
    return (project_root / 'data' / 'modifiers_calc_full' / f'{slug}.html').read_text(encoding='utf-8')


def test_helmet_str_base_items_parse_from_tokenized_poe2db_table(project_root: Path):
    parsed = parse_subtype_page('https://poe2db.tw/us/Helmets_str', _read_fixture(project_root, 'Helmets_str'))
    assert len(parsed['baseItems']) == 20
    assert parsed['baseItems'][0] == {
        'name': 'Rusted Greathelm',
        'requirements': {'level': None, 'str': None, 'dex': None, 'int': None},
        'defences': {'armour': 29},
    }
    assert parsed['baseItems'][-1] == {
        'name': 'Imperial Greathelm',
        'requirements': {'level': 80, 'str': 115, 'dex': None, 'int': None},
        'defences': {'armour': 316},
    }


def test_all_helmet_subtypes_have_base_items(project_root: Path):
    expected_counts = {
        'Helmets_str': 20,
        'Helmets_dex': 20,
        'Helmets_int': 20,
        'Helmets_str_dex': 17,
        'Helmets_str_int': 17,
        'Helmets_dex_int': 17,
    }
    for slug, expected_count in expected_counts.items():
        parsed = parse_subtype_page(f'https://poe2db.tw/us/{slug}', _read_fixture(project_root, slug))
        assert len(parsed['baseItems']) == expected_count, slug
