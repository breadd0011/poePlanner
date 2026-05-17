from __future__ import annotations

from poe2db_scraper.augment_parser import parse_augment_index_page
from poe2db_scraper.builder import _augment_coverage_report
from poe2db_scraper.schema import AUGMENT_INDEX_URL


def test_augment_index_parser_reads_rune_item_section_only() -> None:
    html = """
    <html><body>
      <div class="card"><h5 class="card-header">Augment Item /123</h5>
        <a href="Desert_Rune">Desert Rune</a>
      </div>
      <div class="card"><h5 class="card-header">Rune Item /42</h5>
        <table><tbody>
          <tr><td><img src="https://cdn.poe2db.tw/image/Art/2DItems/Currency/Runes/FireRune.webp"><a class="whiteitem SoulCore" href="Desert_Rune">Desert Rune</a></td></tr>
          <tr><td><img src="https://cdn.poe2db.tw/image/Art/2DItems/Currency/Runes/ColdRune.webp"><a class="whiteitem SoulCore" href="Glacial_Rune">Glacial Rune</a></td></tr>
        </tbody></table>
      </div>
    </body></html>
    """

    index = parse_augment_index_page(AUGMENT_INDEX_URL, html)
    entries = index["entries"]

    assert index["kind"] == "augment_index"
    assert len(entries) == 2
    assert [entry["name"] for entry in entries] == ["Desert Rune", "Glacial Rune"]
    assert entries[0]["sourceUrl"] == "https://poe2db.tw/us/Desert_Rune"
    assert entries[0]["icon"].endswith("FireRune.webp")


def test_augment_index_parser_dedupes_rune_links() -> None:
    html = """
    <html><body>
      <div class="tab-content"><div id="RuneItems" class="tab-pane">
        <h5>Rune Item /42</h5>
        <a class="SoulCore" href="Desert_Rune">Desert Rune</a>
        <a class="SoulCore" href="Desert_Rune">Desert Rune</a>
      </div></div>
    </body></html>
    """

    entries = parse_augment_index_page(AUGMENT_INDEX_URL, html)["entries"]

    assert len(entries) == 1
    assert entries[0]["id"] == "poe2db:Desert_Rune"


def test_augment_index_parser_embeds_rune_tooltip_data_from_row() -> None:
    html = """
    <html><body>
      <div class="card"><h5 class="card-header">Rune Item /42</h5>
        <table><tbody>
          <tr>
            <td><img src="https://cdn.poe2db.tw/image/Art/2DItems/Currency/Runes/FireRune.webp"><a class="whiteitem SoulCore" href="Desert_Rune">Desert Rune</a></td>
            <td>Stack Size: 1 / 10</td>
            <td>Requires: Level 15</td>
            <td>Martial Weapon: Adds 7 to 11 Fire Damage</td>
            <td>Wand or Staff: Gain 8% of Damage as Extra Fire Damage</td>
            <td>Armour: +12% to Fire Resistance</td>
            <td>Bonded:</td>
            <td>Martial Weapon: 25% increased Ignite Magnitude</td>
            <td>Wand or Staff: 25% increased Ignite Magnitude</td>
            <td>Armour: +10 to maximum Life, +10 to maximum Mana</td>
          </tr>
        </tbody></table>
      </div>
    </body></html>
    """

    entries = parse_augment_index_page(AUGMENT_INDEX_URL, html)["entries"]
    augment = entries[0]["embeddedAugment"]

    assert augment["name"] == "Desert Rune"
    assert augment["icon"].endswith("FireRune.webp")
    assert len(augment["augmentEffects"]) == 6
    assert augment["augmentEffects"][0] == {
        "condition": "martial_weapon",
        "bonded": False,
        "text": "Adds 7 to 11 Fire Damage",
        "label": "Martial Weapon",
    }
    assert augment["augmentEffects"][3] == {
        "condition": "martial_weapon",
        "bonded": True,
        "text": "25% increased Ignite Magnitude",
        "label": "Martial Weapon",
    }


def test_augment_index_parser_falls_back_to_full_page_when_section_is_tab_label() -> None:
    html = """
    <html><body>
      <ul><li><a href="#RuneItems">Rune Item /42</a></li></ul>
      <div id="RuneItems"></div>
      <div class="py-2">
        <div class="newItemPopup currencyPopup item-popup--poe2">
          <div class="itemHeader singleLine"><div class="itemName typeLine">Desert Rune</div></div>
          <div class="content"><div class="Stats">
            <div class="property">Augment</div>
            <div class="property">Stack Size: 1 / 10</div>
            <div class="requirements">Requires: Level 15</div>
            <div class="implicitMod">Martial Weapon: Adds 7 to 11 Fire Damage</div>
            <div class="implicitMod">Wand or Staff: Gain 8% of Damage as Extra Fire Damage</div>
            <div class="implicitMod">Armour: +12% to Fire Resistance</div>
            <div class="bondedMod">Bonded:</div>
            <div class="bondedMod">Martial Weapon: 25% increased Ignite Magnitude</div>
            <div class="bondedMod">Wand or Staff: 25% increased Ignite Magnitude</div>
            <div class="bondedMod">Armour: +10 to maximum Life, +10 to maximum Mana</div>
          </div></div>
        </div>
        <a href="Desert_Rune">Desert Rune</a>
      </div>
      <a href="Random_Soul_Core">Random Soul Core</a>
    </body></html>
    """

    index = parse_augment_index_page(AUGMENT_INDEX_URL, html)
    entries = index["entries"]

    assert index["expectedCount"] == 42
    assert len(entries) == 1
    assert entries[0]["name"] == "Desert Rune"
    assert any("full Augment page" in warning for warning in index["warnings"])


def test_augment_index_parser_ignores_soul_core_links_even_with_soulcore_class() -> None:
    html = """
    <html><body>
      <div class="card"><h5 class="card-header">Rune Item /42</h5>
        <a class="whiteitem SoulCore" href="Desert_Rune">Desert Rune</a>
        <a class="whiteitem SoulCore" href="Ruby_Soul_Core">Ruby Soul Core</a>
      </div>
    </body></html>
    """

    entries = parse_augment_index_page(AUGMENT_INDEX_URL, html)["entries"]

    assert [entry["name"] for entry in entries] == ["Desert Rune"]


def test_augment_index_parser_handles_plain_flow_rune_item_section_without_leaking() -> None:
    html = """
    <html><body>
      <h5>Augment Item /123</h5>
      <img src="ignored.webp"><a href="Fake_Rune">Fake Rune</a>
      <div>Stack Size: 1 / 10</div>
      <div>Martial Weapon: This should not be parsed</div>

      <h5>Rune Item /42</h5>
      <h5>Rune</h5>
      <p>Runes are Augments of Kalguuran origin and make.</p>
      <img src="https://cdn.poe2db.tw/image/Art/2DItems/Currency/Runes/FireRune.webp">
      <a href="Desert_Rune">Desert Rune</a>
      <div>Stack Size: 1 / 10</div>
      <div>Requires: Level 15</div>
      <div>Martial Weapon: Adds 7 to 11 Fire Damage</div>
      <div>Wand or Staff: Gain 8% of Damage as Extra Fire Damage</div>
      <div>Armour: +12% to Fire Resistance</div>
      <div>Bonded:</div>
      <div>Martial Weapon: 25% increased Ignite Magnitude</div>
      <div>Wand or Staff: 25% increased Ignite Magnitude</div>
      <div>Armour: +10 to maximum Life, +10 to maximum Mana</div>

      <h5>Rune Ref /2</h5>
      <a href="Other_Rune">Other Rune</a>
    </body></html>
    """

    entries = parse_augment_index_page(AUGMENT_INDEX_URL, html)["entries"]

    assert [entry["name"] for entry in entries] == ["Desert Rune"]
    assert entries[0]["icon"].endswith("FireRune.webp")
    assert len(entries[0]["embeddedAugment"]["augmentEffects"]) == 6


def test_augment_index_parser_normalizes_all_equipment_rune_effects() -> None:
    html = """
    <html><body>
      <div class="card"><h5 class="card-header">Rune Item /42</h5>
        <table><tbody>
          <tr>
            <td><img src="https://cdn.poe2db.tw/image/Art/2DItems/Currency/Runes/StrengthRuneTier1.webp"><a href="Lesser_Robust_Rune">Lesser Robust Rune</a></td>
            <td>Stack Size: 1 / 10</td>
            <td>All Equipment: +6 to Strength</td>
            <td>Bonded:</td>
            <td>Martial Weapon: Adds 6 to 10 Physical Damage to Attacks, Adds 6 to 10 Fire damage to Attacks</td>
            <td>Wand or Staff: +100 to Armour</td>
            <td>Armour: +10 to maximum Life, +10 to maximum Mana</td>
          </tr>
        </tbody></table>
      </div>
    </body></html>
    """

    augment = parse_augment_index_page(AUGMENT_INDEX_URL, html)["entries"][0]["embeddedAugment"]

    assert augment["augmentEffects"][0] == {
        "condition": "all_equipment",
        "bonded": False,
        "text": "+6 to Strength",
        "label": "All Equipment",
    }
    assert len(augment["augmentEffects"]) == 4


def test_augment_index_parser_combines_split_stack_size_and_dedupes_properties() -> None:
    html = """
    <html><body>
      <div class="card"><h5 class="card-header">Rune Item /42</h5>
        <table><tbody>
          <tr>
            <td><img src="https://cdn.poe2db.tw/image/Art/2DItems/Currency/Runes/FireRune.webp"><a href="Lesser_Desert_Rune">Lesser Desert Rune</a></td>
            <td>Stack Size:</td><td>1 / 10</td>
            <td>Stack Size:</td>
            <td>Requires: Level 5</td>
            <td>Martial Weapon: Adds 4 to 6 Fire Damage</td>
            <td>Wand or Staff: Gain 4% of Damage as Extra Fire Damage</td>
            <td>Armour: +8% to Fire Resistance</td>
          </tr>
        </tbody></table>
      </div>
    </body></html>
    """

    augment = parse_augment_index_page(AUGMENT_INDEX_URL, html)["entries"][0]["embeddedAugment"]
    property_sections = [section for section in augment["tooltipSections"] if section["kind"] == "property"]

    assert property_sections == [{"kind": "property", "lines": ["Stack Size: 1 / 10"]}]
    assert len([effect for effect in augment["augmentEffects"] if not effect["bonded"]]) == 3



def test_augment_coverage_report_flags_suspicious_partial_data() -> None:
    augments = [
        {
            "name": "Lesser Desert Rune",
            "icon": "FireRune.webp",
            "tooltipSections": [
                {"kind": "property", "lines": ["Stack Size:", "Stack Size:"]},
                {"kind": "requirement", "lines": ["Requires: Level 5"]},
            ],
            "objectData": {"augmentDataSource": "embedded_index"},
            "augmentEffects": [
                {"condition": "armour", "bonded": False, "label": "Armour", "text": "Regenerate"},
            ],
        }
    ]
    report = _augment_coverage_report(augments, {"expectedCount": 42, "entries": [{"name": "Lesser Desert Rune"}]})

    assert report["loaded"] == 1
    assert report["complete"] is False
    assert report["dataSourceCounts"] == {"embedded_index": 1}
    assert report["emptyStackSizeProperties"] == ["Lesser Desert Rune"]
    assert report["duplicatePropertyLines"] == {"Lesser Desert Rune": ["Stack Size:"]}
    assert report["missingNormalConditions"] == {"Lesser Desert Rune": "martial_weapon, wand_or_staff"}
    assert report["suspiciousEffectTexts"] == {"Lesser Desert Rune": ["Armour: Regenerate"]}
    assert any(warning["code"] == "using_embedded_index_fallback" for warning in report["validationWarnings"])
    assert any(warning["code"] == "suspicious_effect_text" for warning in report["validationWarnings"])


def test_augment_coverage_report_accepts_all_equipment_condition_set() -> None:
    augments = [
        {
            "name": "Lesser Robust Rune",
            "icon": "StrengthRuneTier1.webp",
            "tooltipSections": [
                {"kind": "property", "lines": ["Stack Size: 1 / 10"]},
                {"kind": "requirement", "lines": ["Requires: Level 1"]},
            ],
            "objectData": {"augmentDataSource": "detail_page"},
            "augmentEffects": [
                {"condition": "all_equipment", "bonded": False, "label": "All Equipment", "text": "+6 to Strength"},
                {"condition": "armour", "bonded": True, "label": "Armour", "text": "+10 to maximum Life"},
            ],
        }
    ]
    report = _augment_coverage_report(augments, {"expectedCount": 1, "entries": [{"name": "Lesser Robust Rune"}]})

    assert report["missingNormalConditions"] == {}
    assert report["withCompleteNormalConditionSets"] == 1
    assert report["warningCounts"]["error"] == 0
    assert report["warningCounts"]["warning"] == 0


def test_augment_index_parser_audits_full_catalogue_sections() -> None:
    html = """
    <html><body>
      <div class="card"><h5 class="card-header">Augment Item /3</h5>
        <table><tbody>
          <tr><td><img src="lesser.webp"><a href="Lesser_Desert_Rune">Lesser Desert Rune</a></td></tr>
          <tr><td><img src="soul.webp"><a href="Abyssal_Soul_Core">Abyssal Soul Core</a></td></tr>
          <tr><td><img src="other.webp"><a href="Artificers_Orb">Artificer's Orb</a></td></tr>
        </tbody></table>
      </div>
      <div class="card"><h5 class="card-header">Rune Item /1</h5>
        <table><tbody>
          <tr><td><img src="desert.webp"><a href="Desert_Rune">Desert Rune</a></td></tr>
        </tbody></table>
      </div>
      <div class="card"><h5 class="card-header">Rune Ref /1</h5>
        <a href="Rune">Rune</a>
      </div>
    </body></html>
    """

    index = parse_augment_index_page(AUGMENT_INDEX_URL, html)
    audits = {section["section"]: section for section in index["catalogueSections"]}

    assert audits["Augment Item"]["expected"] == 3
    assert audits["Augment Item"]["discovered"] == 3
    assert audits["Augment Item"]["categoryCounts"] == {
        "augment_item": 1,
        "rune_like_augment": 1,
        "soul_core": 1,
    }
    assert audits["Augment Item"]["socketCandidateCount"] == 0
    assert audits["Rune Item"]["discovered"] == 1
    assert audits["Rune Item"]["socketCandidateCount"] == 1
    assert audits["Rune Item"]["categoryCounts"] == {"rune_item": 1}


def test_augment_index_audit_report_is_read_only_and_warns_on_incomplete_sections() -> None:
    index = {
        "entries": [{"name": "Desert Rune", "sourceUrl": "https://poe2db.tw/us/Desert_Rune"}],
        "expectedCount": 1,
        "catalogueSections": [
            {
                "section": "Augment Item",
                "expected": 123,
                "discovered": 2,
                "categoryCounts": {"rune_like_augment": 1, "augment_item": 1},
                "socketCandidateCount": 0,
                "entries": [
                    {"name": "Desert Rune", "sourceUrl": "https://poe2db.tw/us/Desert_Rune"},
                    {"name": "Artificer's Orb", "sourceUrl": "https://poe2db.tw/us/Artificers_Orb"},
                ],
                "warnings": ["Parsed 2 entries, expected 123 from the Augment Item label."],
            },
            {
                "section": "Rune Item",
                "expected": 42,
                "discovered": 1,
                "categoryCounts": {"rune_item": 1},
                "socketCandidateCount": 1,
                "entries": [
                    {"name": "Desert Rune", "sourceUrl": "https://poe2db.tw/us/Desert_Rune"},
                ],
                "warnings": [],
            },
        ],
    }

    from poe2db_scraper.builder import _augment_index_audit_report

    report = _augment_index_audit_report(index)

    assert report["complete"] is False
    assert report["expectedTotal"] == 165
    assert report["discoveredTotal"] == 3
    assert report["categoryCounts"] == {"augment_item": 1, "rune_item": 1, "rune_like_augment": 1}
    assert any(warning["code"] == "augment_catalogue_section_warning" for warning in report["validationWarnings"])
    assert any(warning["code"] == "augment_item_contains_rune_like_entries" for warning in report["validationWarnings"])


def test_augment_catalogue_registry_keeps_full_index_read_only() -> None:
    from poe2db_scraper.builder import _augment_catalogue_registry

    html = """
    <html><body>
      <div class="card"><h5 class="card-header">Augment Item /123</h5>
        <a href="Desert_Rune">Desert Rune</a>
        <a href="Random_Augment">Random Augment</a>
      </div>
      <div class="card"><h5 class="card-header">Rune Item /42</h5>
        <a href="Desert_Rune">Desert Rune</a>
        <a href="Glacial_Rune">Glacial Rune</a>
      </div>
    </body></html>
    """

    index = parse_augment_index_page(AUGMENT_INDEX_URL, html)
    catalogue = _augment_catalogue_registry(index)

    assert catalogue["kind"] == "augment_catalogue"
    assert catalogue["total"] == 4
    assert catalogue["socketCandidateCount"] == 2
    assert catalogue["sectionCounts"]["Augment Item"] == 2
    assert catalogue["sectionCounts"]["Rune Item"] == 2
    assert catalogue["categoryCounts"]["rune_item"] == 2
    assert catalogue["categoryCounts"]["rune_like_augment"] == 1
    assert [entry["plannerVisibility"] for entry in catalogue["entries"] if entry["section"] == "Rune Item"] == ["socket_picker", "socket_picker"]
    assert [entry["plannerVisibility"] for entry in catalogue["entries"] if entry["section"] == "Augment Item"] == ["catalogue_only", "catalogue_only"]


def test_augment_catalogue_registry_reuses_preloaded_detail_without_fetch(tmp_path) -> None:
    from poe2db_scraper.builder import _augment_catalogue_registry
    from poe2db_scraper.schema import BuildPaths

    index = {
        "sourceUrl": AUGMENT_INDEX_URL,
        "warnings": [],
        "catalogueSections": [
            {
                "section": "Rune Item",
                "entries": [
                    {
                        "id": "poe2db:Desert_Rune",
                        "slug": "Desert_Rune",
                        "name": "Desert Rune",
                        "sourceUrl": "https://poe2db.tw/us/Desert_Rune",
                        "category": "rune_item",
                        "socketCandidate": True,
                        "icon": "FireRune.webp",
                    }
                ],
            },
            {
                "section": "Augment Item",
                "entries": [
                    {
                        "id": "poe2db:Other_Augment",
                        "slug": "Other_Augment",
                        "name": "Other Augment",
                        "sourceUrl": "https://poe2db.tw/us/Other_Augment",
                        "category": "augment_item",
                        "socketCandidate": False,
                    }
                ],
            },
        ],
    }
    preloaded = [
        {
            "name": "Desert Rune",
            "sourceUrl": "https://poe2db.tw/us/Desert_Rune",
            "itemClass": "Augment",
            "icon": "FireRune.webp",
            "tooltipSections": [
                {"kind": "property", "lines": ["Stack Size: 1 / 10"]},
                {"kind": "requirement", "lines": ["Requires: Level 15"]},
                {"kind": "description", "lines": ["Place into an empty Augment Socket."]},
            ],
            "objectData": {"augmentDataSource": "detail_page"},
            "augmentEffects": [
                {"condition": "martial_weapon", "bonded": False, "label": "Martial Weapon", "text": "Adds 7 to 11 Fire Damage"},
                {"condition": "armour", "bonded": True, "label": "Armour", "text": "+10 to maximum Life"},
            ],
        }
    ]

    catalogue = _augment_catalogue_registry(
        index,
        paths=BuildPaths(project_root=tmp_path),
        force_refresh=False,
        data_snapshots=[],
        snapshot_date="2026-05-13",
        preloaded_augments=preloaded,
    )

    assert catalogue["total"] == 2
    assert catalogue["detailLoadedCount"] == 1
    assert catalogue["indexOnlyCount"] == 1
    assert catalogue["entriesWithEffects"] == 1
    assert catalogue["detailStatusCounts"] == {"detail_loaded": 1, "index_only": 1}
    desert = next(entry for entry in catalogue["entries"] if entry["name"] == "Desert Rune")
    assert desert["detailStatus"] == "detail_loaded"
    assert desert["detailSource"] == "detail_page"
    assert desert["normalEffectCount"] == 1
    assert desert["bondedEffectCount"] == 1
    assert desert["requirementLines"] == ["Requires: Level 15"]


def test_socket_candidate_reason_uses_game_socket_description_for_soul_core() -> None:
    from poe2db_scraper.builder import _augment_socket_candidate_reason

    entry = {"section": "Augment Item", "category": "soul_core", "name": "Soul Core of Tacati"}
    augment = {
        "name": "Soul Core of Tacati",
        "tooltipSections": [
            {"kind": "description", "lines": ["Place into an empty Augment Socket in a Weapon or Armour to apply its effect to that item."]},
        ],
        "augmentEffects": [
            {"condition": "armour", "bonded": False, "label": "Armour", "text": "+11% to Chaos Resistance"},
        ],
    }

    assert _augment_socket_candidate_reason(entry, augment) == "augment_socket_description"


def test_socket_candidate_reason_keeps_reference_sections_out() -> None:
    from poe2db_scraper.builder import _augment_socket_candidate_reason

    entry = {"section": "SoulCore Ref", "category": "reference", "name": "Soul Core"}
    augment = {
        "name": "Soul Core",
        "tooltipSections": [
            {"kind": "description", "lines": ["Place into an empty Augment Socket in a Weapon or Armour to apply its effect to that item."]},
        ],
        "augmentEffects": [
            {"condition": "armour", "bonded": False, "label": "Armour", "text": "+11% to Chaos Resistance"},
        ],
    }

    assert _augment_socket_candidate_reason(entry, augment) is None


def test_socket_candidate_guardrails_count_categories_and_references() -> None:
    from poe2db_scraper.builder import _socket_candidate_guardrail_report

    entries = [
        {
            "name": "Desert Rune",
            "section": "Rune Item",
            "category": "rune_item",
            "socketCandidate": True,
            "socketCandidateReason": "rune_item_section",
            "plannerVisibility": "socket_picker",
            "normalEffectCount": 3,
            "effectConditions": ["martial_weapon", "wand_or_staff", "armour"],
        },
        {
            "name": "Soul Core of Tacati",
            "section": "Augment Item",
            "category": "soul_core",
            "socketCandidate": True,
            "socketCandidateReason": "augment_socket_description",
            "plannerVisibility": "socket_picker",
            "normalEffectCount": 2,
            "effectConditions": ["martial_weapon", "armour"],
        },
        {
            "name": "Soul Core Ref",
            "section": "SoulCore Ref",
            "category": "reference",
            "socketCandidate": False,
            "plannerVisibility": "catalogue_only",
            "normalEffectCount": 0,
            "effectConditions": [],
        },
    ]

    report = _socket_candidate_guardrail_report(entries)

    assert report["socketCandidateCount"] == 2
    assert report["runeItemCandidates"] == 1
    assert report["soulCoreCandidates"] == 1
    assert report["excludedReferenceEntries"] == 1
    assert report["socketCandidatesByCategory"] == {"rune_item": 1, "soul_core": 1}
    assert report["socketCandidatesByReason"] == {"augment_socket_description": 1, "rune_item_section": 1}
    assert report["validationWarnings"] == []
    assert report["complete"] is True


def test_socket_candidate_guardrails_flag_false_positive_candidates() -> None:
    from poe2db_scraper.builder import _socket_candidate_guardrail_report

    entries = [
        {
            "name": "Soul Core Ref",
            "section": "SoulCore Ref",
            "category": "reference",
            "socketCandidate": True,
            "socketCandidateReason": "augment_socket_description",
            "plannerVisibility": "socket_picker",
            "normalEffectCount": 1,
            "effectConditions": ["armour"],
        },
        {
            "name": "Broken Soul Core",
            "section": "Augment Item",
            "category": "soul_core",
            "socketCandidate": True,
            "socketCandidateReason": "soul_core_equipment_effects",
            "plannerVisibility": "socket_picker",
            "normalEffectCount": 0,
            "effectConditions": [],
        },
        {
            "name": "Odd Augment",
            "section": "Augment Item",
            "category": "augment_item",
            "socketCandidate": True,
            "socketCandidateReason": "equipment_targeted_effects",
            "plannerVisibility": "socket_picker",
            "normalEffectCount": 1,
            "effectConditions": ["unknown_condition"],
        },
    ]

    report = _socket_candidate_guardrail_report(entries)
    codes = {warning["code"] for warning in report["validationWarnings"]}

    assert report["complete"] is False
    assert "reference_entry_in_socket_picker" in codes
    assert "socket_candidate_missing_normal_effects" in codes
    assert "soul_core_missing_normal_effects" in codes
    assert "socket_candidate_missing_equipment_target" in codes
