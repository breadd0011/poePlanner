from __future__ import annotations

from poe2db_scraper.health_report import build_payload_health_report
from poe2db_scraper.modifier_coverage_config import (
    EXPERIMENTAL_MODIFIER_CLASSES,
    REQUIRED_MODIFIER_CLASSES,
    SUPPORTED_WEAPON_MODIFIER_ITEM_CLASSES,
)


def _pool(item_class: str, *, editor: bool = True) -> dict:
    if editor:
        return {
            "itemClass": item_class,
            "mods": [{"text": "+# to maximum Life"}],
        }
    return {
        "itemClass": item_class,
        "prefixes": [{"text": "+# to maximum Life"}],
        "suffixes": [{"text": "+#% to Fire Resistance"}],
    }


def _required_editor_pools() -> list[dict]:
    return [_pool(item_class) for item_class in REQUIRED_MODIFIER_CLASSES]


def _required_normal_pools() -> list[dict]:
    return [_pool(item_class, editor=False) for item_class in REQUIRED_MODIFIER_CLASSES]


def _minimal_payload(**overrides) -> dict:
    payload = {
        "schemaVersion": "poc-0.21",
        "parserVersion": "test",
        "baseItems": [],
        "uniqueItems": [],
        "itemSubtypes": [],
        "editorModifierPools": [],
        "normalExplicitPools": [],
    }
    payload.update(overrides)
    return payload


def test_base_item_duplicates_are_scoped_to_item_class() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            baseItems=[
                {"itemClass": "One Hand Swords", "name": "Energy Blade", "icon": "a", "sourceUrl": "a"},
                {"itemClass": "Two Hand Swords", "name": "Energy Blade", "icon": "b", "sourceUrl": "b"},
            ],
            editorModifierPools=_required_editor_pools(),
            normalExplicitPools=_required_normal_pools(),
        )
    )

    assert report["baseItems"]["duplicateNames"] == []
    assert not any(warning["code"] == "DUPLICATE_BASE_ITEM_NAMES" for warning in report["warnings"])


def test_base_item_duplicates_inside_same_class_still_warn() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            baseItems=[
                {"itemClass": "Rings", "name": "Gold Ring", "icon": "a", "sourceUrl": "a"},
                {"itemClass": "Rings", "name": "Gold Ring", "icon": "b", "sourceUrl": "b"},
            ],
            editorModifierPools=_required_editor_pools(),
            normalExplicitPools=_required_normal_pools(),
        )
    )

    assert report["baseItems"]["duplicateNames"] == [{"itemClass": "Rings", "name": "Gold Ring", "count": 2}]
    assert any(warning["code"] == "DUPLICATE_BASE_ITEM_NAMES" for warning in report["warnings"])


def test_required_modifier_classes_must_have_editor_and_normal_pools() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            baseItems=[{"itemClass": "Gloves", "name": "Stocky Mitts", "icon": "a", "sourceUrl": "a"}],
            editorModifierPools=[_pool("Gloves")],
            normalExplicitPools=[_pool("Gloves", editor=False)],
        )
    )

    assert report["status"] == "error"
    assert report["modifierCoverage"]["byClass"]["Gloves"]["coverageStatus"] == "ok"
    assert report["modifierCoverage"]["byClass"]["Boots"]["coverageStatus"] == "missing_required_pools"
    assert report["modifierCoverage"]["byClass"]["Rings"]["missingRequired"] == [
        "editorModifierPools",
        "normalExplicitPools",
    ]
    assert any(warning["code"] == "REQUIRED_MODIFIER_CLASS_MISSING_POOLS" for warning in report["warnings"])


def test_non_armour_modifier_classes_are_now_required() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            baseItems=[{"itemClass": "Rings", "name": "Gold Ring", "icon": "a", "sourceUrl": "a"}],
            editorModifierPools=_required_editor_pools(),
            normalExplicitPools=_required_normal_pools(),
        )
    )

    rings = report["modifierCoverage"]["byClass"]["Rings"]
    assert rings["supportState"] == "required"
    assert rings["coverageStatus"] == "ok"
    assert rings["missingRequired"] == []
    assert not any(warning.get("itemClass") == "Rings" for warning in report["warnings"])


def test_modifier_coverage_summary_counts_ready_required_classes() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            editorModifierPools=_required_editor_pools(),
            normalExplicitPools=_required_normal_pools(),
        )
    )

    summary = report["modifierCoverage"]["summary"]
    assert summary["requiredClasses"] == len(REQUIRED_MODIFIER_CLASSES)
    assert summary["requiredClassesOk"] == len(REQUIRED_MODIFIER_CLASSES)
    assert summary["experimentalClasses"] == len(EXPERIMENTAL_MODIFIER_CLASSES)
    assert summary["experimentalClassesReady"] == 0
    assert report["modifierCoverage"]["byClass"]["Rings"]["coverageStatus"] == "ok"


def test_unpublished_unique_flavour_placeholder_does_not_warn() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            uniqueItems=[
                {
                    "itemClass": "Body Armours",
                    "name": "Tabula Rasa",
                    "icon": "icon",
                    "sourceUrl": "https://poe2db.tw/us/Tabula_Rasa",
                    "explicitMods": [{"text": "Has 6 Jewel Sockets"}],
                    "flavourText": [],
                    "diagnostics": [{"code": "UNIQUE_FLAVOUR_TEXT_NOT_PUBLISHED"}],
                }
            ],
            editorModifierPools=_required_editor_pools(),
            normalExplicitPools=_required_normal_pools(),
        )
    )

    flavour = report["uniqueItems"]["byClass"]["Body Armours"]["flavourText"]
    assert flavour["missing"] == 0
    assert flavour["unavailable"] == 1
    assert not any(warning["code"] == "UNIQUE_MISSING_FLAVOUR_TEXT" for warning in report["warnings"])


def test_talismans_are_promoted_to_required_weapon_pools() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            editorModifierPools=_required_editor_pools(),
            normalExplicitPools=_required_normal_pools(),
            modifierAudits=[
                {
                    "kind": "modifier_class_audit",
                    "itemClass": "Talismans",
                    "supportState": "required",
                    "sourceUrl": "https://poe2db.tw/us/Talismans#ModifiersCalc",
                    "sourceUrls": ["https://poe2db.tw/us/Talismans#ModifiersCalc"],
                    "classPageUrl": "https://poe2db.tw/us/Talismans",
                    "classSnapshotStatus": "present",
                    "classSnapshotPath": "data/snapshots/poe2db/2026-05-06/classes/talismans.html",
                    "modifierSnapshotStatus": "present",
                    "modifierSnapshotPath": "data/modifiers_calc_full/talismans.html",
                    "baseItemCount": 26,
                    "uniqueItemCount": 9,
                    "editorModifierPoolCount": 11,
                    "editorModifierCount": 167,
                    "normalExplicitPoolCount": 1,
                    "normalPrefixCount": 8,
                    "normalSuffixCount": 13,
                    "rawSources": ["ModifiersCalc"],
                }
            ],
        )
    )

    talismans = report["modifierCoverage"]["byClass"]["Talismans"]
    assert talismans["supportState"] == "required"
    assert talismans["coverageStatus"] == "ok"
    assert talismans["coverageCountSource"] == "payload"
    assert talismans["baseItems"]["total"] == 26
    assert talismans["uniqueItems"]["total"] == 9
    assert talismans["sourceUrl"] == "https://poe2db.tw/us/Talismans#ModifiersCalc"
    assert talismans["snapshotStatus"]["modifiersCalc"] == "present"
    assert not any(warning.get("itemClass") == "Talismans" for warning in report["warnings"])


def test_promoted_weapon_classes_require_production_pools_not_audit_only() -> None:
    editor_pools = [_pool(item_class) for item_class in REQUIRED_MODIFIER_CLASSES if item_class != "Bows"]
    normal_pools = [_pool(item_class, editor=False) for item_class in REQUIRED_MODIFIER_CLASSES if item_class != "Bows"]
    report = build_payload_health_report(
        _minimal_payload(
            editorModifierPools=editor_pools,
            normalExplicitPools=normal_pools,
            modifierAudits=[
                {
                    "kind": "modifier_class_audit",
                    "itemClass": "Bows",
                    "supportState": "required",
                    "sourceUrl": "https://poe2db.tw/us/Bows#ModifiersCalc",
                    "classPageUrl": "https://poe2db.tw/us/Bows",
                    "classSnapshotStatus": "present",
                    "modifierSnapshotStatus": "present",
                    "baseItemCount": 26,
                    "uniqueItemCount": 9,
                    "editorModifierPoolCount": 11,
                    "editorModifierCount": 167,
                    "normalExplicitPoolCount": 1,
                    "normalPrefixCount": 8,
                    "normalSuffixCount": 13,
                    "rawSources": ["modsview_json"],
                }
            ],
        )
    )

    bows = report["modifierCoverage"]["byClass"]["Bows"]
    assert bows["supportState"] == "required"
    assert bows["coverageStatus"] == "missing_required_pools"
    assert bows["coverageCountSource"] == "payload"
    assert bows["missingRequired"] == ["editorModifierPools", "normalExplicitPools"]
    assert any(warning.get("itemClass") == "Bows" for warning in report["warnings"])


def test_weapon_modifier_classes_are_registered_by_support_state() -> None:
    assert "Bows" in SUPPORTED_WEAPON_MODIFIER_ITEM_CLASSES
    assert "Crossbows" in SUPPORTED_WEAPON_MODIFIER_ITEM_CLASSES
    assert "Bows" in REQUIRED_MODIFIER_CLASSES
    assert "Crossbows" in REQUIRED_MODIFIER_CLASSES
    assert "Talismans" in SUPPORTED_WEAPON_MODIFIER_ITEM_CLASSES
    assert "Talismans" in REQUIRED_MODIFIER_CLASSES
    assert "Traps" not in SUPPORTED_WEAPON_MODIFIER_ITEM_CLASSES
    assert "Traps" not in REQUIRED_MODIFIER_CLASSES
    assert "Traps" not in EXPERIMENTAL_MODIFIER_CLASSES
    assert "Talismans" not in EXPERIMENTAL_MODIFIER_CLASSES


def test_item_editor_binding_confirms_visible_weapon_options_have_pools() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            baseItems=[
                {"itemClass": "Bows", "name": "Advanced Dualstring Bow", "icon": "a", "sourceUrl": "a"},
                {"itemClass": "Talismans", "name": "Azure Talisman", "icon": "b", "sourceUrl": "b"},
            ],
            editorModifierPools=[
                {"itemClass": "Bows", "subtype": "base", "mods": [{"text": "+# to Accuracy Rating"}]},
                {"itemClass": "Talismans", "subtype": "base", "mods": [{"text": "+# to maximum Spirit"}]},
                *_required_editor_pools(),
            ],
            normalExplicitPools=[
                {"itemClass": "Bows", "subtype": "base", "prefixes": [{"text": "+# to Accuracy Rating"}], "suffixes": [{"text": "+#% to Fire Resistance"}]},
                {"itemClass": "Talismans", "subtype": "base", "prefixes": [{"text": "+# to maximum Spirit"}], "suffixes": [{"text": "+#% to Fire Resistance"}]},
                *_required_normal_pools(),
            ],
        )
    )

    binding = report["itemEditorBinding"]
    assert binding["byClass"]["Bows"]["status"] == "ok"
    assert binding["byClass"]["Bows"]["totalItemOptions"] == 1
    assert binding["byClass"]["Bows"]["optionsWithEditorPools"] == 1
    assert binding["byClass"]["Bows"]["optionsWithNormalExplicitPools"] == 1
    assert binding["byClass"]["Talismans"]["status"] == "ok"
    assert binding["excludedClasses"]["Traps"]["status"] == "ok"
    assert not any(warning["code"] == "ITEM_EDITOR_BINDING_MISSING_POOLS" for warning in report["warnings"])


def test_item_editor_binding_errors_when_visible_item_has_no_matching_pool() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            baseItems=[{"itemClass": "Bows", "name": "Advanced Dualstring Bow", "icon": "a", "sourceUrl": "a"}],
            editorModifierPools=[pool for pool in _required_editor_pools() if pool["itemClass"] != "Bows"],
            normalExplicitPools=[pool for pool in _required_normal_pools() if pool["itemClass"] != "Bows"],
        )
    )

    bows = report["itemEditorBinding"]["byClass"]["Bows"]
    assert bows["status"] == "missing_binding"
    assert bows["missingEditorPoolOptions"][0]["name"] == "Advanced Dualstring Bow"
    assert bows["missingNormalExplicitPoolOptions"][0]["name"] == "Advanced Dualstring Bow"
    assert any(warning["code"] == "ITEM_EDITOR_BINDING_MISSING_POOLS" for warning in report["warnings"])


def test_item_editor_binding_errors_if_excluded_traps_are_visible() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            baseItems=[{"itemClass": "Traps", "name": "Spike Trap", "icon": "a", "sourceUrl": "a"}],
            editorModifierPools=_required_editor_pools(),
            normalExplicitPools=_required_normal_pools(),
        )
    )

    assert report["itemEditorBinding"]["excludedClasses"]["Traps"]["status"] == "excluded_class_visible"
    assert any(warning["code"] == "ITEM_EDITOR_EXCLUDED_CLASS_VISIBLE" for warning in report["warnings"])


def test_item_editor_binding_reports_untyped_special_options_without_failing() -> None:
    editor_pools = [
        *_required_editor_pools(),
        {"itemClass": "Body Armours", "subtype": "str", "mods": [{"text": "+# to Armour"}]},
        {"itemClass": "Shields", "subtype": "str", "mods": [{"text": "+# to Armour"}]},
    ]
    normal_pools = [
        *_required_normal_pools(),
        {"itemClass": "Body Armours", "subtype": "str", "prefixes": [{"text": "+# to Armour"}], "suffixes": [{"text": "+#% to Fire Resistance"}]},
        {"itemClass": "Shields", "subtype": "str", "prefixes": [{"text": "+# to Armour"}], "suffixes": [{"text": "+#% to Fire Resistance"}]},
    ]
    # Remove any class-level test pools for these two classes so they mimic the
    # real payload: source-backed pools exist by defence subtype, but no
    # subtype=base pool exists for special no-defence bases.
    editor_pools = [pool for pool in editor_pools if not (pool["itemClass"] in {"Body Armours", "Shields"} and pool.get("subtype") in {None, "", "base"})]
    normal_pools = [pool for pool in normal_pools if not (pool["itemClass"] in {"Body Armours", "Shields"} and pool.get("subtype") in {None, "", "base"})]

    report = build_payload_health_report(
        _minimal_payload(
            baseItems=[
                {"itemClass": "Body Armours", "name": "Garment", "icon": "a", "sourceUrl": "a", "defences": {}},
                {"itemClass": "Body Armours", "name": "Iron Cuirass", "icon": "b", "sourceUrl": "b", "defences": {"armour": 20}},
                {"itemClass": "Shields", "name": "Golden Shield", "icon": "c", "sourceUrl": "c", "defences": {}},
            ],
            uniqueItems=[
                {"itemClass": "Body Armours", "name": "Tabula Rasa", "baseType": "Garment", "icon": "u", "sourceUrl": "u", "explicitMods": [{"text": "Has 6 Jewel Sockets"}]},
            ],
            editorModifierPools=editor_pools,
            normalExplicitPools=normal_pools,
        )
    )

    binding = report["itemEditorBinding"]
    assert binding["status"] == "ok"
    assert binding["summary"]["itemOptions"] == 4
    assert binding["summary"]["bindableItemOptions"] == 1
    assert binding["summary"]["untypedSpecialItemOptions"] == 3
    assert binding["summary"]["missingEditorPoolOptions"] == 0
    assert binding["summary"]["missingNormalExplicitPoolOptions"] == 0
    assert binding["byClass"]["Body Armours"]["untypedSpecialItemOptions"] == 2
    assert binding["byClass"]["Shields"]["untypedSpecialItemOptions"] == 1
    assert not any(warning["code"] == "ITEM_EDITOR_BINDING_MISSING_POOLS" for warning in report["warnings"])


def test_item_editor_binding_confirms_visible_weapon_unique_options_have_pools() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            baseItems=[
                {"itemClass": "Bows", "name": "Dualstring Bow", "icon": "a", "sourceUrl": "a"},
            ],
            uniqueItems=[
                {"itemClass": "Bows", "name": "Death's Harp", "baseType": "Dualstring Bow", "icon": "u", "sourceUrl": "u", "explicitMods": [{"text": "Bow Attacks fire an additional Arrow"}]},
            ],
            editorModifierPools=[
                *_required_editor_pools(),
                {"itemClass": "Bows", "subtype": "base", "mods": [{"text": "+# to Accuracy Rating"}]},
            ],
            normalExplicitPools=[
                *_required_normal_pools(),
                {"itemClass": "Bows", "subtype": "base", "prefixes": [{"text": "+# to Accuracy Rating"}], "suffixes": [{"text": "+#% to Fire Resistance"}]},
            ],
        )
    )

    bows = report["itemEditorBinding"]["byClass"]["Bows"]
    assert bows["status"] == "ok"
    assert bows["baseOptions"] == 1
    assert bows["uniqueOptions"] == 1
    assert bows["optionsWithEditorPools"] == 2
    assert bows["optionsWithNormalExplicitPools"] == 2
    assert not any(warning["code"] == "ITEM_EDITOR_BINDING_MISSING_POOLS" for warning in report["warnings"])


def test_weapon_unique_production_health_reports_zero_unique_weapon_classes() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            parserSanity={"weaponUniqueItemsByClass": {"Bows": 1, "Claws": 0}},
            uniqueItems=[
                {
                    "itemClass": "Bows",
                    "name": "Death's Harp",
                    "baseType": "Dualstring Bow",
                    "icon": "icon.png",
                    "flavourText": "A song for the dead.",
                    "explicitMods": [{"text": "Bow Attacks fire an additional Arrow"}],
                    "sourceUrl": "https://poe2db.tw/us/Death%27s_Harp",
                }
            ],
            editorModifierPools=_required_editor_pools(),
            normalExplicitPools=_required_normal_pools(),
        )
    )

    weapon = report["weaponUniqueProduction"]
    assert weapon["status"] == "ok"
    assert weapon["summary"]["importedUniqueItems"] == 1
    assert weapon["summary"]["expectedUniqueItems"] == 1
    assert weapon["byClass"]["Bows"]["status"] == "ok"
    assert weapon["byClass"]["Bows"]["icon"]["withValue"] == 1
    assert weapon["byClass"]["Claws"]["status"] == "ok"
    assert weapon["byClass"]["Claws"]["zeroUniqueClass"] is True
    assert not any(warning["code"] == "WEAPON_UNIQUE_PRODUCTION_INCOMPLETE" for warning in report["warnings"])


def test_weapon_unique_production_health_errors_on_count_or_detail_mismatch() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            parserSanity={"weaponUniqueItemsByClass": {"Bows": 2}},
            uniqueItems=[
                {
                    "itemClass": "Bows",
                    "name": "Death's Harp",
                    "baseType": "Dualstring Bow",
                    "explicitMods": [],
                    "sourceUrl": "https://poe2db.tw/us/Death%27s_Harp",
                }
            ],
            editorModifierPools=_required_editor_pools(),
            normalExplicitPools=_required_normal_pools(),
        )
    )

    weapon = report["weaponUniqueProduction"]
    assert weapon["status"] == "error"
    assert weapon["byClass"]["Bows"]["status"] == "count_mismatch"
    assert weapon["summary"]["countMismatches"] == 1
    assert weapon["summary"]["missingIcon"] == 1
    assert weapon["summary"]["missingExplicitMods"] == 1
    assert any(warning["code"] == "WEAPON_UNIQUE_PRODUCTION_INCOMPLETE" for warning in report["warnings"])


def test_unique_editor_binding_confirms_unique_base_and_modifier_pool_path() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            baseItems=[{"itemClass": "Bows", "name": "Dualstring Bow", "icon": "a", "sourceUrl": "a"}],
            uniqueItems=[
                {
                    "itemClass": "Bows",
                    "name": "Death's Harp",
                    "baseType": "Dualstring Bow",
                    "icon": "u",
                    "flavourText": "A song for the dead.",
                    "sourceUrl": "u",
                    "explicitMods": [{"text": "Bow Attacks fire an additional Arrow"}],
                }
            ],
            editorModifierPools=[*_required_editor_pools(), {"itemClass": "Bows", "subtype": "base", "mods": [{"text": "+# to Accuracy Rating"}]}],
            normalExplicitPools=[*_required_normal_pools(), {"itemClass": "Bows", "subtype": "base", "prefixes": [{"text": "+# to Accuracy Rating"}], "suffixes": [{"text": "+#% to Fire Resistance"}]}],
        )
    )

    binding = report["uniqueEditorBinding"]
    assert binding["status"] == "ok"
    assert binding["summary"]["uniqueOptions"] == 1
    assert binding["summary"]["optionsWithBaseItems"] == 1
    assert binding["summary"]["optionsWithEditorPools"] == 1
    assert binding["summary"]["optionsWithNormalExplicitPools"] == 1
    assert binding["byClass"]["Bows"]["status"] == "ok"
    assert not any(warning["code"] == "UNIQUE_EDITOR_BINDING_MISSING" for warning in report["warnings"])


def test_unique_editor_binding_errors_when_unique_base_type_is_not_visible() -> None:
    report = build_payload_health_report(
        _minimal_payload(
            baseItems=[{"itemClass": "Bows", "name": "Dualstring Bow", "icon": "a", "sourceUrl": "a"}],
            uniqueItems=[
                {
                    "itemClass": "Bows",
                    "name": "Death's Harp",
                    "baseType": "Unknown Bow",
                    "icon": "u",
                    "flavourText": "A song for the dead.",
                    "sourceUrl": "u",
                    "explicitMods": [{"text": "Bow Attacks fire an additional Arrow"}],
                }
            ],
            editorModifierPools=[*_required_editor_pools(), {"itemClass": "Bows", "subtype": "base", "mods": [{"text": "+# to Accuracy Rating"}]}],
            normalExplicitPools=[*_required_normal_pools(), {"itemClass": "Bows", "subtype": "base", "prefixes": [{"text": "+# to Accuracy Rating"}], "suffixes": [{"text": "+#% to Fire Resistance"}]}],
        )
    )

    binding = report["uniqueEditorBinding"]
    assert binding["status"] == "error"
    assert binding["summary"]["missingBaseItemOptions"] == 1
    assert binding["byClass"]["Bows"]["status"] == "missing_base_item"
    assert binding["byClass"]["Bows"]["missingBaseItemOptions"][0]["baseName"] == "Unknown Bow"
    assert any(warning["code"] == "UNIQUE_EDITOR_BINDING_MISSING" for warning in report["warnings"])
