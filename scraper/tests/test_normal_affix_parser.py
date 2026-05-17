from pathlib import Path

from poe2db_scraper.normal_affix_parser import parse_normal_affix_snapshot, parse_normal_affix_sources


def _snapshot(project_root: Path) -> str:
    return (project_root / "tests" / "fixtures" / "modifiers_calc" / "Gloves_int_modifiers_calc.txt").read_text(encoding="utf-8")


def _prefix_html(project_root: Path) -> str:
    return (project_root / "tests" / "fixtures" / "modifiers_calc" / "Gloves_int_base_prefix.html").read_text(encoding="utf-8")


def _suffix_html(project_root: Path) -> str:
    return (project_root / "tests" / "fixtures" / "modifiers_calc" / "modifiers_calc_gloves_int_base_suffix.html").read_text(encoding="utf-8")


def _str_dex_prefix_html(project_root: Path) -> str:
    return (project_root / "tests" / "fixtures" / "modifiers_calc" / "modifiers_calc_gloves_str_dex_base_prefix.html").read_text(encoding="utf-8")


def _str_dex_suffix_html(project_root: Path) -> str:
    return (project_root / "tests" / "fixtures" / "modifiers_calc" / "modifiers_calc_gloves_str_dex_base_suffix.html").read_text(encoding="utf-8")


def test_gloves_int_normal_affix_snapshot_contract(project_root: Path) -> None:
    pool = parse_normal_affix_snapshot(
        _snapshot(project_root),
        source_url="https://poe2db.tw/us/Gloves_int#ModifiersCalc",
        item_class="Gloves",
        subtype="int",
        slug="Gloves_int",
        validation_source="user_supplied_modifiers_calc_snapshot_and_manual_check",
        confidence="high",
    )

    prefix_texts = [mod["text"] for mod in pool["prefixes"]]
    suffix_texts = [mod["text"] for mod in pool["suffixes"]]

    assert len(prefix_texts) == 10
    assert len(suffix_texts) == 17
    assert "# to maximum Life" in prefix_texts
    assert "# to maximum Mana" in prefix_texts
    assert "# to maximum" not in prefix_texts
    assert "# to maximum Energy Shield" in prefix_texts
    assert "#% increased Energy Shield" in prefix_texts
    assert "#% increased Energy Shield / # to maximum Life" in prefix_texts
    assert "Adds # to # Lightning Damage to Attacks" in prefix_texts
    assert "# to Intelligence" in suffix_texts
    assert "#% increased Energy Shield Recharge Rate" in suffix_texts
    assert "#% to Chaos Resistance" in suffix_texts
    assert not any("LifeDefences" in text or "ElementalFire" in text for text in prefix_texts + suffix_texts)

    life_prefix = next(mod for mod in pool["prefixes"] if mod["text"] == "# to maximum Life")
    mana_prefix = next(mod for mod in pool["prefixes"] if mod["text"] == "# to maximum Mana")
    hybrid_prefix = next(mod for mod in pool["prefixes"] if mod["text"] == "#% increased Energy Shield / # to maximum Life")
    fire_prefix = next(mod for mod in pool["prefixes"] if mod["text"] == "Adds # to # Fire Damage to Attacks")
    assert life_prefix["tags"] == ["Life"]
    assert mana_prefix["tags"] == ["Mana"]
    assert hybrid_prefix["tags"] == ["Life", "Defences"]
    assert fire_prefix["tags"] == ["Damage", "Elemental", "Fire", "Attack"]

    assert pool["validationSource"] == "user_supplied_modifiers_calc_snapshot_and_manual_check"
    assert pool["confidence"] == "high"


def test_gloves_int_base_prefix_suffix_dom_contract(project_root: Path) -> None:
    pool = parse_normal_affix_sources(
        _snapshot(project_root),
        source_url="https://poe2db.tw/us/Gloves_int#ModifiersCalc",
        item_class="Gloves",
        subtype="int",
        slug="Gloves_int",
        prefix_html=_prefix_html(project_root),
        suffix_html=_suffix_html(project_root),
        validation_source="user_supplied_modifiers_calc_snapshot_dom_prefix_suffix_and_manual_check",
        confidence="high",
    )

    life_prefix = next(mod for mod in pool["prefixes"] if mod["text"] == "# to maximum Life")
    fire_prefix = next(mod for mod in pool["prefixes"] if mod["text"] == "Adds # to # Fire Damage to Attacks")
    hybrid_prefix = next(mod for mod in pool["prefixes"] if mod["text"] == "#% increased Energy Shield / # to maximum Life")
    int_suffix = next(mod for mod in pool["suffixes"] if mod["text"] == "# to Intelligence")
    fire_res_suffix = next(mod for mod in pool["suffixes"] if mod["text"] == "#% to Fire Resistance")

    assert len(pool["prefixes"]) == 10
    assert len(pool["suffixes"]) == 17
    assert pool["rawSources"] == ["snapshot_txt", "prefix_dom_html", "suffix_dom_html"]
    assert life_prefix["family"] == "IncreasedLife"
    assert life_prefix["generationGroup"] == "1IncreasedLife"
    assert life_prefix["weightRaw"] == "9000"
    assert life_prefix["weightPercent"] == "14.129%"
    assert life_prefix["level"] == 60
    assert life_prefix["tierCount"] == 9
    assert life_prefix["detailStatus"] == "available"
    assert life_prefix["tags"] == ["Life"]
    assert fire_prefix["tags"] == ["Damage", "Elemental", "Fire", "Attack"]
    assert hybrid_prefix["tags"] == ["Life", "Defences"]
    assert int_suffix["family"] == "Intelligence"
    assert int_suffix["generationGroup"] == "2Intelligence"
    assert int_suffix["weightRaw"] == "8000"
    assert int_suffix["level"] == 74
    assert int_suffix["tierCount"] == 8
    assert int_suffix["tags"] == ["Attribute"]
    assert fire_res_suffix["tags"] == ["Elemental", "Fire", "Resistance"]
    assert any(d["code"] == "NORMAL_PREFIX_DOM_SOURCE_USED" for d in pool["diagnostics"])
    assert any(d["code"] == "NORMAL_SUFFIX_DOM_SOURCE_USED" for d in pool["diagnostics"])


def test_gloves_str_dex_hybrid_dom_contract(project_root: Path) -> None:
    pool = parse_normal_affix_sources(
        "",
        source_url="https://poe2db.tw/us/Gloves_str_dex#ModifiersCalc",
        item_class="Gloves",
        subtype="str_dex",
        slug="Gloves_str_dex",
        prefix_html=_str_dex_prefix_html(project_root),
        suffix_html=_str_dex_suffix_html(project_root),
        validation_source="user_supplied_modifiers_calc_dom_prefix_suffix_snapshot",
        confidence="high",
    )

    prefix_texts = [mod["text"] for mod in pool["prefixes"]]
    assert len(pool["prefixes"]) == 10
    assert len(pool["suffixes"]) == 17
    assert ("# to Armour / # to Evasion Rating" in prefix_texts) or ("# to Armour # to Evasion Rating" in prefix_texts)
    assert "#% increased Armour and Evasion" in prefix_texts
    assert ("#% increased Armour and Evasion / # to maximum Life" in prefix_texts) or ("#% increased Armour and Evasion # to maximum Life" in prefix_texts)
    hybrid_defence = next(mod for mod in pool["prefixes"] if mod["text"] == "# to Armour / # to Evasion Rating")
    hybrid_life = next(mod for mod in pool["prefixes"] if mod["text"] == "#% increased Armour and Evasion / # to maximum Life")
    assert hybrid_defence["family"] == "BaseLocalDefences"
    assert hybrid_defence["tags"] == ["Defences"]
    assert hybrid_life["tags"] == ["Life", "Defences"]

from poe2db_scraper.normal_affix_parser import parse_editor_modifier_pools_from_html, normal_pool_from_editor_pools


def test_full_modifiers_calc_html_parses_all_editor_groups(project_root: Path) -> None:
    html = (project_root / "data" / "modifiers_calc_full" / "Gloves_int.html").read_text(encoding="utf-8")
    pools = parse_editor_modifier_pools_from_html(
        html,
        source_url="https://poe2db.tw/us/Gloves_int#ModifiersCalc",
        item_class="Gloves",
        subtype="int",
        slug="Gloves_int",
    )
    by_group = {pool["sourceGroup"]: pool for pool in pools}
    assert len(pools) == 11
    assert len(by_group["Base Prefix"]["mods"]) == 10
    assert len(by_group["Base Suffix"]["mods"]) == 17
    assert len(by_group["Augment"]["mods"]) >= 43
    assert len(by_group["Bonded Modifiers"]["mods"]) == 28
    assert len(by_group["Corrupted"]["mods"]) == 9
    assert by_group["Augment"]["sourceMechanic"] == "augment"
    assert by_group["Bonded Modifiers"]["sourceMechanic"] == "bonded"
    assert by_group["Augment"]["affixType"] is None
    assert by_group["Base Prefix"]["mods"][0]["text"] == "# to maximum Life"
    assert by_group["Base Prefix"]["mods"][0]["tags"] == ["Life"]


def test_derived_normal_pool_from_full_html(project_root: Path) -> None:
    html = (project_root / "data" / "modifiers_calc_full" / "Gloves_str_dex.html").read_text(encoding="utf-8")
    editor_pools = parse_editor_modifier_pools_from_html(
        html,
        source_url="https://poe2db.tw/us/Gloves_str_dex#ModifiersCalc",
        item_class="Gloves",
        subtype="str_dex",
        slug="Gloves_str_dex",
    )
    normal_pool = normal_pool_from_editor_pools(
        editor_pools,
        source_url="https://poe2db.tw/us/Gloves_str_dex#ModifiersCalc",
        item_class="Gloves",
        subtype="str_dex",
        slug="Gloves_str_dex",
    )
    prefix_texts = [mod["text"] for mod in normal_pool["prefixes"]]
    assert len(normal_pool["prefixes"]) == 10
    assert len(normal_pool["suffixes"]) == 18
    assert normal_pool["rawSources"] in (["full_html"], ["modsview_json"])
    assert ("# to Armour / # to Evasion Rating" in prefix_texts) or ("# to Armour # to Evasion Rating" in prefix_texts)
    assert ("#% increased Armour and Evasion / # to maximum Life" in prefix_texts) or ("#% increased Armour and Evasion # to maximum Life" in prefix_texts)
