from pathlib import Path

from poe2db_scraper.subtype_parser import parse_subtype_page
from poe2db_scraper.unique_gloves_parser import extract_unique_glove_candidates


def _base_names(project_root: Path) -> list[str]:
    names: list[str] = []
    for slug in [
        'Helmets_str',
        'Helmets_dex',
        'Helmets_int',
        'Helmets_str_dex',
        'Helmets_str_int',
        'Helmets_dex_int',
    ]:
        html = (project_root / 'data' / 'modifiers_calc_full' / f'{slug}.html').read_text(encoding='utf-8')
        parsed = parse_subtype_page(f'https://poe2db.tw/us/{slug}', html)
        names.extend(item['name'] for item in parsed['baseItems'])
    return names


def _helmets_class_html(project_root: Path) -> str:
    snapshots = sorted((project_root / 'data' / 'snapshots' / 'poe2db').glob('*/classes/Helmets.html'), reverse=True)
    if snapshots:
        return snapshots[0].read_text(encoding='utf-8')
    cache_snapshots = sorted((project_root / 'scraper' / 'cache').glob('*.html'), reverse=True)
    for path in cache_snapshots:
        text = path.read_text(encoding='utf-8')
        if 'Helmets Unique /50' in text:
            return text
    raise AssertionError('No Helmets class HTML snapshot found. Run --update-snapshots --categories Helmets first.')


def test_helmet_unique_candidates_are_real_item_cards_only(project_root: Path):
    candidates = extract_unique_glove_candidates(
        'https://poe2db.tw/us/Helmets',
        _helmets_class_html(project_root),
        _base_names(project_root),
    )
    names = {candidate.name for candidate in candidates}
    assert len(candidates) == 50
    assert 'Helmets' not in names
    assert 'Wings of Caelyn' in names
    assert 'Goldrim' in names
    assert all(candidate.baseType for candidate in candidates)
    assert all('/us/' in candidate.sourceUrl for candidate in candidates)
