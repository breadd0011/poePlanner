from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_run_poc_module():
    module_path = Path(__file__).resolve().parents[1] / "run_poc.py"
    spec = importlib.util.spec_from_file_location("scraper_run_poc", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_print_augment_coverage_summary_warns_when_only_desert_rune_loaded(capsys):
    run_poc = _load_run_poc_module()
    payload = {
        "parserSanity": {
            "augmentCoverage": {
                "expected": 42,
                "loaded": 1,
                "discovered": 42,
                "withNormalEffects": 1,
                "withBondedEffects": 1,
                "withIcons": 1,
                "withRequirements": 1,
                "complete": False,
                "dataSourceCounts": {"detail_page_fallback": 1},
                "warningCounts": {"warning": 1},
                "validationWarnings": [
                    {
                        "severity": "warning",
                        "code": "missing_detail_page",
                        "augmentName": "Desert Rune",
                        "message": "Used fallback data.",
                    }
                ],
            }
        }
    }

    run_poc.print_augment_coverage_summary(payload)

    output = capsys.readouterr().out
    assert "Rune augment coverage" in output
    assert "Loaded: 1 / 42" in output
    assert "ACTION: Only one rune augment is loaded" in output
    assert "scraper\\scripts\\refresh_rune_augments.bat" in output


def test_print_augment_coverage_summary_reports_complete_state(capsys):
    run_poc = _load_run_poc_module()
    payload = {
        "parserSanity": {
            "augmentCoverage": {
                "expected": 42,
                "loaded": 42,
                "discovered": 42,
                "withNormalEffects": 42,
                "withBondedEffects": 42,
                "withIcons": 42,
                "withRequirements": 42,
                "complete": True,
                "dataSourceCounts": {"detail_page": 42},
                "warningCounts": {},
                "validationWarnings": [],
            }
        }
    }

    run_poc.print_augment_coverage_summary(payload)

    output = capsys.readouterr().out
    assert "Loaded: 42 / 42" in output
    assert "Data sources: detail_page=42" in output
    assert "OK: Rune augment coverage looks complete." in output


def test_print_augment_index_audit_summary_reports_sections(capsys):
    run_poc = _load_run_poc_module()
    payload = {
        "parserSanity": {
            "augmentIndexAudit": {
                "expectedTotal": 165,
                "discoveredTotal": 165,
                "complete": True,
                "categoryCounts": {"augment_item": 81, "rune_item": 42, "soul_core": 3},
                "sections": [
                    {
                        "section": "Augment Item",
                        "expected": 123,
                        "discovered": 123,
                        "socketCandidateCount": 0,
                        "categoryCounts": {"augment_item": 81, "rune_like_augment": 42},
                        "entries": [],
                        "warnings": [],
                    },
                    {
                        "section": "Rune Item",
                        "expected": 42,
                        "discovered": 42,
                        "socketCandidateCount": 42,
                        "categoryCounts": {"rune_item": 42},
                        "entries": [],
                        "warnings": [],
                    },
                ],
                "validationWarnings": [],
            }
        }
    }

    run_poc.print_augment_index_audit_summary(payload)

    output = capsys.readouterr().out
    assert "Augment index classification audit" in output
    assert "Catalogue links discovered: 165 / 165" in output
    assert "Augment Item: 123 / 123 discovered" in output
    assert "Rune Item: 42 / 42 discovered, socket candidates=42" in output


def test_print_augment_index_audit_summary_reports_warnings(capsys):
    run_poc = _load_run_poc_module()
    payload = {
        "parserSanity": {
            "augmentIndexAudit": {
                "expectedTotal": 165,
                "discoveredTotal": 43,
                "complete": False,
                "categoryCounts": {"rune_item": 42, "augment_item": 1},
                "sections": [
                    {
                        "section": "Augment Item",
                        "expected": 123,
                        "discovered": 1,
                        "socketCandidateCount": 0,
                        "categoryCounts": {"augment_item": 1},
                        "entries": [],
                        "warnings": ["Parsed 1 entries, expected 123 from the Augment Item label."],
                    }
                ],
                "validationWarnings": [
                    {
                        "severity": "warning",
                        "code": "augment_catalogue_section_warning",
                        "section": "Augment Item",
                        "message": "Parsed 1 entries, expected 123 from the Augment Item label.",
                    }
                ],
            }
        }
    }

    run_poc.print_augment_index_audit_summary(payload)

    output = capsys.readouterr().out
    assert "Audit warnings:" in output
    assert "WARNING augment_catalogue_section_warning" in output


def test_print_augment_catalogue_summary_reports_read_only_registry(capsys):
    run_poc = _load_run_poc_module()
    payload = {
        "augmentCatalogue": {
            "kind": "augment_catalogue",
            "total": 165,
            "socketCandidateCount": 42,
            "sectionCounts": {"Augment Item": 123, "Rune Item": 42},
            "categoryCounts": {"augment_item": 81, "rune_item": 42, "rune_like_augment": 42},
            "detailLoadedCount": 42,
            "detailFailedCount": 0,
            "indexOnlyCount": 123,
            "entriesWithEffects": 42,
            "detailStatusCounts": {"detail_loaded": 42, "index_only": 123},
            "detailSourceCounts": {"detail_page": 42, "index_only": 123},
            "entries": [{"name": "Desert Rune"}],
        }
    }

    run_poc.print_augment_catalogue_summary(payload)

    output = capsys.readouterr().out
    assert "Augment catalogue registry" in output
    assert "Entries: 165" in output
    assert "Socket picker candidates: 42" in output
    assert "Catalogue-only entries: 123" in output
    assert "Detail loaded: 42" in output
    assert "Index-only: 123" in output
    assert "Detail statuses: detail_loaded=42, index_only=123" in output
    assert "Non-rune catalogue entries are retained read-only" in output


def test_print_socket_candidate_guardrail_summary_reports_ok_state(capsys):
    run_poc = _load_run_poc_module()
    payload = {
        "augmentCatalogue": {
            "socketCandidateAudit": {
                "socketCandidateCount": 45,
                "runeItemCandidates": 42,
                "soulCoreCandidates": 3,
                "otherSocketableAugments": 0,
                "excludedReferenceEntries": 5,
                "socketCandidatesByCategory": {"rune_item": 42, "soul_core": 3},
                "socketCandidatesByReason": {"rune_item_section": 42, "augment_socket_description": 3},
                "validationWarnings": [],
            }
        }
    }

    run_poc.print_socket_candidate_guardrail_summary(payload)

    output = capsys.readouterr().out
    assert "Socket-compatible augment guardrails" in output
    assert "Rune Item candidates: 42" in output
    assert "Soul Core candidates: 3" in output
    assert "OK: Socket-compatible augment picker guardrails passed." in output


def test_print_socket_candidate_guardrail_summary_reports_warnings(capsys):
    run_poc = _load_run_poc_module()
    payload = {
        "augmentCatalogue": {
            "socketCandidateAudit": {
                "socketCandidateCount": 1,
                "runeItemCandidates": 0,
                "soulCoreCandidates": 0,
                "otherSocketableAugments": 1,
                "excludedReferenceEntries": 0,
                "socketCandidatesByCategory": {"reference": 1},
                "socketCandidatesByReason": {"augment_socket_description": 1},
                "validationWarnings": [
                    {
                        "severity": "error",
                        "code": "reference_entry_in_socket_picker",
                        "augmentName": "Soul Core Ref",
                        "message": "Reference entry leaked into socket picker.",
                    }
                ],
            }
        }
    }

    run_poc.print_socket_candidate_guardrail_summary(payload)

    output = capsys.readouterr().out
    assert "Warnings:" in output
    assert "ERROR reference_entry_in_socket_picker" in output


def test_compact_augment_coverage_groups_warnings_and_names_missing_bonded(capsys):
    run_poc = _load_run_poc_module()
    payload = {
        "parserSanity": {
            "augmentCoverage": {
                "expected": 42,
                "loaded": 42,
                "discovered": 42,
                "withNormalEffects": 42,
                "withBondedEffects": 39,
                "withIcons": 42,
                "withRequirements": 28,
                "complete": False,
                "missingBondedEffects": ["Rune A", "Rune B", "Rune C"],
                "dataSourceCounts": {"detail_page": 42},
                "warningCounts": {"info": 17, "warning": 3},
                "validationWarnings": [
                    {"severity": "info", "code": "missing_bonded_effects", "augmentName": "Rune A"},
                    {"severity": "info", "code": "missing_bonded_effects", "augmentName": "Rune B"},
                    {"severity": "warning", "code": "missing_normal_conditions", "augmentName": "Rune C"},
                ],
            }
        }
    }

    run_poc.print_augment_coverage_summary(payload, detail="compact")

    output = capsys.readouterr().out
    assert "Missing bonded effects: 3" in output
    assert "Warnings by code:" in output
    assert "missing_bonded_effects=2" in output
    assert "REVIEW: Rune data loaded" in output


def test_compact_augment_index_audit_uses_label_count_language(capsys):
    run_poc = _load_run_poc_module()
    payload = {
        "parserSanity": {
            "augmentIndexAudit": {
                "expectedTotal": 178,
                "discoveredTotal": 344,
                "categoryCounts": {"augment_item": 167, "rune_item": 78},
                "sections": [
                    {"section": "Augment Item", "expected": 123, "discovered": 239, "socketCandidateCount": 0},
                    {"section": "Rune Item", "expected": 42, "discovered": 78, "socketCandidateCount": 78},
                ],
                "validationWarnings": [],
            }
        }
    }

    run_poc.print_augment_index_audit_summary(payload, detail="compact")

    output = capsys.readouterr().out
    assert "Catalogue links discovered: 344 (label total 178" in output
    assert "Augment Item: 239 discovered (label count 123" in output
    assert "Rune Item: 78 discovered (label count 42" in output


def test_compact_socket_guardrail_groups_warning_codes(capsys):
    run_poc = _load_run_poc_module()
    payload = {
        "augmentCatalogue": {
            "socketCandidateAudit": {
                "socketCandidateCount": 2,
                "runeItemCandidates": 1,
                "soulCoreCandidates": 0,
                "otherSocketableAugments": 1,
                "excludedReferenceEntries": 0,
                "socketCandidatesByCategory": {"rune_item": 1, "augment_item": 1},
                "socketCandidatesByReason": {"rune_item_section": 1, "augment_socket_description": 1},
                "validationWarnings": [
                    {"severity": "warning", "code": "socket_candidate_missing_equipment_target", "augmentName": "Odd Rune"},
                    {"severity": "warning", "code": "socket_candidate_missing_equipment_target", "augmentName": "Odd Idol"},
                ],
            }
        }
    }

    run_poc.print_socket_candidate_guardrail_summary(payload, detail="compact")

    output = capsys.readouterr().out
    assert "Warnings by code: socket_candidate_missing_equipment_target=2" in output
    assert "Odd Rune, Odd Idol" in output
    assert "REVIEW: Some socket candidates lack explicit parsed equipment targets" in output
