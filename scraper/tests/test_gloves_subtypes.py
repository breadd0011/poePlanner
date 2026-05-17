from pathlib import Path

from poe2db_scraper.schema import (
    GLOVES_DEX_INT_URL,
    GLOVES_DEX_URL,
    GLOVES_INT_URL,
    GLOVES_STR_DEX_URL,
    GLOVES_STR_INT_URL,
    GLOVES_STR_URL,
)
from poe2db_scraper.subtype_parser import parse_subtype_page


def _primary(parsed):
    return next(group for group in parsed["modGroups"] if group["plannerPrimary"])


def _texts(group):
    return [mod["text"] for mod in group["mods"]]


def _assert_primary_pool(parsed, expected_extra: str):
    primary = _primary(parsed)
    reference = next(group for group in parsed["modGroups"] if not group["plannerPrimary"])
    primary_texts = _texts(primary)
    reference_texts = _texts(reference)
    assert primary["sourceSection"] == "ModifiersCalc"
    assert all("Corruption" not in text for text in primary_texts)
    if expected_extra in primary_texts:
        assert len(primary_texts) == len(reference_texts) + 1
        assert expected_extra not in reference_texts
        assert parsed["modPoolComparisons"][0]["status"] == "primary_superset"
        assert parsed["modPoolComparisons"][0]["extraInPrimary"] == [expected_extra]
    else:
        # Legacy plain-text fixtures do not embed the planner dropdown/ModsView JSON.
        # In that case the parser now uses the PoE2DB static Vaal section as the
        # primary fallback instead of inventing a subtype-specific corruption.
        assert primary_texts == reference_texts
        assert parsed["modPoolComparisons"][0]["status"] == "same"


def test_gloves_str_base_items(fixtures_dir: Path):
    parsed = parse_subtype_page(GLOVES_STR_URL, (fixtures_dir / "Gloves_str.html").read_text(encoding="utf-8"))
    assert parsed["subtype"] == "str"
    assert parsed["attributeProfile"] == ["str"]
    assert parsed["defenceProfile"] == ["armour"]
    assert len(parsed["baseItems"]) == 16
    riveted = next(item for item in parsed["baseItems"] if item["name"] == "Riveted Mitts")
    assert riveted["defences"] == {"armour": 31}
    assert riveted["requirements"] == {"level": 11, "str": 16, "dex": None, "int": None}
    _assert_primary_pool(parsed, "(15—25)% increased Armour")


def test_gloves_dex_base_items(fixtures_dir: Path):
    parsed = parse_subtype_page(GLOVES_DEX_URL, (fixtures_dir / "Gloves_dex.html").read_text(encoding="utf-8"))
    assert parsed["subtype"] == "dex"
    assert parsed["attributeProfile"] == ["dex"]
    assert parsed["defenceProfile"] == ["evasion"]
    assert len(parsed["baseItems"]) == 16
    firm = next(item for item in parsed["baseItems"] if item["name"] == "Firm Bracers")
    assert firm["defences"] == {"evasion": 26}
    assert firm["requirements"] == {"level": 11, "str": None, "dex": 16, "int": None}
    _assert_primary_pool(parsed, "(15—25)% increased Evasion Rating")


def test_gloves_int_primary_corrupted_pool_from_modifiers_calc(fixtures_dir: Path):
    parsed = parse_subtype_page(GLOVES_INT_URL, (fixtures_dir / "Gloves_int.html").read_text(encoding="utf-8"))
    assert parsed["subtype"] == "int"
    assert parsed["attributeProfile"] == ["int"]
    assert parsed["defenceProfile"] == ["energy_shield"]
    assert len(parsed["baseItems"]) == 16
    sombre = next(item for item in parsed["baseItems"] if item["name"] == "Sombre Gloves")
    assert sombre["defences"] == {"energyShield": 15}
    assert sombre["requirements"] == {"level": 12, "str": None, "dex": None, "int": 17}
    _assert_primary_pool(parsed, "(15—25)% increased Energy Shield")


def test_gloves_str_dex_hybrid_base_items(fixtures_dir: Path):
    parsed = parse_subtype_page(GLOVES_STR_DEX_URL, (fixtures_dir / "Gloves_str_dex.html").read_text(encoding="utf-8"))
    assert parsed["subtype"] == "str_dex"
    assert parsed["attributeProfile"] == ["str", "dex"]
    assert parsed["defenceProfile"] == ["armour", "evasion"]
    assert len(parsed["baseItems"]) == 13
    ringmail = next(item for item in parsed["baseItems"] if item["name"] == "Ringmail Gauntlets")
    assert ringmail["defences"] == {"armour": 13, "evasion": 10}
    assert ringmail["requirements"] == {"level": 6, "str": 6, "dex": 6, "int": None}
    _assert_primary_pool(parsed, "(15—25)% increased Evasion Rating")


def test_gloves_str_int_hybrid_base_items(fixtures_dir: Path):
    parsed = parse_subtype_page(GLOVES_STR_INT_URL, (fixtures_dir / "Gloves_str_int.html").read_text(encoding="utf-8"))
    assert parsed["subtype"] == "str_int"
    assert parsed["attributeProfile"] == ["str", "int"]
    assert parsed["defenceProfile"] == ["armour", "energy_shield"]
    assert len(parsed["baseItems"]) == 13
    rope = next(item for item in parsed["baseItems"] if item["name"] == "Rope Cuffs")
    assert rope["defences"] == {"armour": 12, "energyShield": 6}
    assert rope["requirements"] == {"level": 5, "str": 6, "dex": None, "int": 6}
    _assert_primary_pool(parsed, "(15—25)% increased Energy Shield")


def test_gloves_dex_int_hybrid_base_items_skip_dnt(fixtures_dir: Path):
    parsed = parse_subtype_page(GLOVES_DEX_INT_URL, (fixtures_dir / "Gloves_dex_int.html").read_text(encoding="utf-8"))
    assert parsed["subtype"] == "dex_int"
    assert parsed["attributeProfile"] == ["dex", "int"]
    assert parsed["defenceProfile"] == ["evasion", "energy_shield"]
    assert len(parsed["baseItems"]) == 13
    assert not any("DNT" in item["name"] for item in parsed["baseItems"])
    gauze = next(item for item in parsed["baseItems"] if item["name"] == "Gauze Wraps")
    assert gauze["defences"] == {"evasion": 8, "energyShield": 6}
    assert gauze["requirements"] == {"level": 4, "str": None, "dex": 6, "int": 6}
    _assert_primary_pool(parsed, "(15—25)% increased Energy Shield")
