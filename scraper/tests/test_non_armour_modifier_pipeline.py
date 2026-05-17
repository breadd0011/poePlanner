from __future__ import annotations

from pathlib import Path

from poe2db_scraper.health_report import build_payload_health_report
from poe2db_scraper.modifier_coverage_config import REQUIRED_MODIFIER_CLASSES, SUPPORTED_WEAPON_MODIFIER_ITEM_CLASSES
from poe2db_scraper.normal_affix_parser import parse_editor_modifier_pools_from_html, normal_pool_from_editor_pools
from poe2db_scraper.unique_gloves_parser import stable_slug


def _latest_class_snapshot(project_root: Path, item_class: str) -> Path:
    file_name = f"{item_class.replace(' ', '_')}.html"
    snapshots = project_root / "data" / "snapshots" / "poe2db"
    for dated_dir in sorted([path for path in snapshots.iterdir() if path.is_dir()], reverse=True):
        candidate = dated_dir / "classes" / file_name
        if candidate.exists():
            return candidate
    raise AssertionError(f"Missing checked-in class snapshot for {item_class}")


def _minimal_modsview_html() -> str:
    rows = {
        "normal": [
            {"Name": "Healthy", "Level": 1, "DropChance": 1, "ModGenerationTypeID": "1", "str": "+<span class='mod-value'>10</span> to maximum Life", "ModFamilyList": ["Life"], "mod_no": ["<span class='badge' data-tag='life'>Life</span>"]},
            {"Name": "of the Fortress", "Level": 1, "DropChance": 1, "ModGenerationTypeID": "2", "str": "+<span class='mod-value'>8</span>% to Fire Resistance", "ModFamilyList": ["Resistance"], "mod_no": ["<span class='badge' data-tag='resistance'>Resistance</span>"]},
        ],
        "desecrated": [],
        "essence": [],
        "perfect_essence": [],
        "socketable": [],
        "bonded": [],
        "corrupted": [],
    }
    import json

    return f"<script>new ModsView({json.dumps(rows)});</script>"


def test_class_level_accessory_and_offhand_modifiers_parse_from_poe2db_snapshots(project_root: Path) -> None:
    expected_minimums = {
        "Rings": (13, 18),
        "Amulets": (12, 21),
        "Belts": (7, 11),
        "Foci": (10, 13),
        "Quivers": (7, 8),
    }

    for item_class, (min_prefixes, min_suffixes) in expected_minimums.items():
        source_url = f"https://poe2db.tw/us/{item_class.replace(' ', '_')}#ModifiersCalc"
        html = _latest_class_snapshot(project_root, item_class).read_text(encoding="utf-8")
        pools = parse_editor_modifier_pools_from_html(
            html,
            source_url=source_url,
            item_class=item_class,
            subtype="base",
            slug=stable_slug(item_class),
            validation_source="test_class_level_snapshot",
            confidence="high",
        )
        normal = normal_pool_from_editor_pools(
            pools,
            source_url=source_url,
            item_class=item_class,
            subtype="base",
            slug=stable_slug(item_class),
            validation_source="test_class_level_snapshot",
            confidence="high",
        )

        assert len(pools) == 11
        assert len(normal["prefixes"]) >= min_prefixes
        assert len(normal["suffixes"]) >= min_suffixes
        assert {pool["rawSource"] for pool in pools} == {"modsview_json"}



def test_representative_supported_weapon_modifiers_parse_from_poe2db_snapshots(project_root: Path) -> None:
    # Keep this focused: the health config test covers all promoted classes,
    # while this parser test samples one one-handed, one two-handed, and one
    # ranged weapon page so the full suite stays fast.
    for item_class in ("Bows", "One Hand Swords", "Quarterstaves"):
        assert item_class in SUPPORTED_WEAPON_MODIFIER_ITEM_CLASSES
        source_url = f"https://poe2db.tw/us/{item_class.replace(' ', '_')}#ModifiersCalc"
        html = _latest_class_snapshot(project_root, item_class).read_text(encoding="utf-8")
        pools = parse_editor_modifier_pools_from_html(
            html,
            source_url=source_url,
            item_class=item_class,
            subtype="base",
            slug=stable_slug(item_class),
            validation_source="test_supported_weapon_snapshot",
            confidence="high",
        )
        normal = normal_pool_from_editor_pools(
            pools,
            source_url=source_url,
            item_class=item_class,
            subtype="base",
            slug=stable_slug(item_class),
            validation_source="test_supported_weapon_snapshot",
            confidence="high",
        )

        assert len(pools) == 11, item_class
        assert len(normal["prefixes"]) > 0, item_class
        assert len(normal["suffixes"]) > 0, item_class
        assert {pool["rawSource"] for pool in pools} == {"modsview_json"}

def test_shield_subtype_modifier_pages_are_supported_as_required_coverage() -> None:
    html = _minimal_modsview_html()
    pools = parse_editor_modifier_pools_from_html(
        html,
        source_url="https://poe2db.tw/us/Shields_str#ModifiersCalc",
        item_class="Shields",
        subtype="str",
        slug="Shields_str",
        validation_source="test_shield_subtype_synthetic_modsview",
        confidence="high",
    )
    normal = normal_pool_from_editor_pools(
        pools,
        source_url="https://poe2db.tw/us/Shields_str#ModifiersCalc",
        item_class="Shields",
        subtype="str",
        slug="Shields_str",
        validation_source="test_shield_subtype_synthetic_modsview",
        confidence="high",
    )

    assert len(pools) == 11
    assert len(normal["prefixes"]) == 1
    assert len(normal["suffixes"]) == 1
    assert {pool["rawSource"] for pool in pools} == {"modsview_json"}


def test_body_armour_subtype_modifier_pages_are_supported_as_required_coverage() -> None:
    html = _minimal_modsview_html()
    pools = parse_editor_modifier_pools_from_html(
        html,
        source_url="https://poe2db.tw/us/Body_Armours_str_dex#ModifiersCalc",
        item_class="Body Armours",
        subtype="str_dex",
        slug="Body_Armours_str_dex",
        validation_source="test_body_armour_subtype_synthetic_modsview",
        confidence="high",
    )
    normal = normal_pool_from_editor_pools(
        pools,
        source_url="https://poe2db.tw/us/Body_Armours_str_dex#ModifiersCalc",
        item_class="Body Armours",
        subtype="str_dex",
        slug="Body_Armours_str_dex",
        validation_source="test_body_armour_subtype_synthetic_modsview",
        confidence="high",
    )

    assert len(pools) == 11
    assert len(normal["prefixes"]) == 1
    assert len(normal["suffixes"]) == 1
    assert {pool["rawSource"] for pool in pools} == {"modsview_json"}


def test_offhand_modifier_coverage_marks_required_classes_ok_when_pools_exist() -> None:
    editor_pools = []
    normal_pools = []
    for item_class in REQUIRED_MODIFIER_CLASSES:
        editor_pools.append({"itemClass": item_class, "mods": [{"text": "+# to maximum Life"}]})
        normal_pools.append({
            "itemClass": item_class,
            "prefixes": [{"text": "+# to maximum Life"}],
            "suffixes": [{"text": "+#% to Fire Resistance"}],
        })

    report = build_payload_health_report({
        "schemaVersion": "poc-0.21",
        "parserVersion": "test",
        "baseItems": [
            {"itemClass": "Rings", "name": "Gold Ring", "icon": "a", "sourceUrl": "a"},
            {"itemClass": "Amulets", "name": "Lapis Amulet", "icon": "b", "sourceUrl": "b"},
            {"itemClass": "Belts", "name": "Fine Belt", "icon": "c", "sourceUrl": "c"},
            {"itemClass": "Shields", "name": "Aged Tower Shield", "icon": "d", "sourceUrl": "d"},
            {"itemClass": "Body Armours", "name": "Garment", "icon": "g", "sourceUrl": "g"},
            {"itemClass": "Foci", "name": "Lacewood Focus", "icon": "e", "sourceUrl": "e"},
            {"itemClass": "Quivers", "name": "Sacred Quiver", "icon": "f", "sourceUrl": "f"},
        ],
        "uniqueItems": [],
        "itemSubtypes": [],
        "editorModifierPools": editor_pools,
        "normalExplicitPools": normal_pools,
    })

    coverage = report["modifierCoverage"]["byClass"]
    for item_class in ("Rings", "Amulets", "Belts", "Body Armours", "Shields", "Foci", "Quivers"):
        row = coverage[item_class]
        assert row["supportState"] == "required"
        assert row["coverageStatus"] == "ok"
        assert row["baseItems"]["coveredByEditorPools"] == row["baseItems"]["total"]
        assert row["baseItems"]["coveredByNormalExplicitPools"] == row["baseItems"]["total"]

    assert report["status"] == "ok"


def test_parser_sanity_report_accepts_offhand_modifier_counts() -> None:
    from poe2db_scraper.models import ParserSanityReport

    report = ParserSanityReport.model_validate({
        "loadedBodyArmourEditorModifierPools": 66,
        "loadedBodyArmourNormalExplicitPools": 6,
        "loadedShieldEditorModifierPools": 33,
        "loadedShieldNormalExplicitPools": 3,
        "loadedFocusEditorModifierPools": 11,
        "loadedFocusNormalExplicitPools": 1,
        "loadedQuiverEditorModifierPools": 11,
        "loadedQuiverNormalExplicitPools": 1,
    })

    assert report.loadedBodyArmourEditorModifierPools == 66
    assert report.loadedBodyArmourNormalExplicitPools == 6
    assert report.loadedShieldEditorModifierPools == 33
    assert report.loadedShieldNormalExplicitPools == 3
    assert report.loadedFocusEditorModifierPools == 11
    assert report.loadedFocusNormalExplicitPools == 1
    assert report.loadedQuiverEditorModifierPools == 11
    assert report.loadedQuiverNormalExplicitPools == 1
