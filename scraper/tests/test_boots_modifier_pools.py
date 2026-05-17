import json
from pathlib import Path


def load_payload(project_root: Path):
    return json.loads((project_root / 'out' / 'poe2db_poc_ui.json').read_text(encoding='utf-8'))


def test_boots_have_own_modifier_pools(project_root: Path):
    payload = load_payload(project_root)
    editor = payload['editorModifierPools']
    normal = payload['normalExplicitPools']
    boot_editor = [pool for pool in editor if pool['itemClass'] == 'Boots']
    boot_normal = [pool for pool in normal if pool['itemClass'] == 'Boots']
    assert len(boot_editor) == 66
    assert len(boot_normal) == 6
    assert all('Boots_' in pool['slug'] for pool in boot_editor)
    assert all('/Boots_' in pool['sourceUrl'] for pool in boot_editor)


def test_boots_pools_do_not_reuse_glove_specific_attack_mods(project_root: Path):
    payload = load_payload(project_root)
    boot_mod_texts = [
        mod['text']
        for pool in payload['editorModifierPools']
        if pool['itemClass'] == 'Boots'
        for mod in pool['mods']
    ]
    assert '#% increased Movement Speed' in boot_mod_texts
    assert '#% increased Attack Speed' not in boot_mod_texts
    assert '#% increased Critical Damage Bonus' not in boot_mod_texts
