from __future__ import annotations

from poe2db_scraper.augment_classification import classify_augment_name, socket_candidate_reason
from poe2db_scraper.diagnostics import normalise_diagnostic, warning
from poe2db_scraper.payload_contract import RuntimePayloadOptions, diagnostics_payload, runtime_payload, runtime_payload_from_options


def test_runtime_payload_can_strip_inline_diagnostics_and_legacy_fields() -> None:
    payload = {
        "schemaVersion": "poc-0.21",
        "parserVersion": "test",
        "generatedAt": "2026-05-16T00:00:00+00:00",
        "source": "poe2db",
        "sourceUrls": [],
        "items": [],
        "augment": {},
        "augments": [],
        "augmentCatalogue": None,
        "itemClasses": [],
        "itemSubtypes": [],
        "normalExplicitPools": [],
        "editorModifierPools": [],
        "modifierSourceMechanics": [],
        "modifierAudits": [{"sourceUrl": "https://example.test"}],
        "baseItems": [],
        "uniqueItems": [],
        "uniqueGloves": [],
        "dataSnapshots": [{"path": "data/snapshot.html"}],
        "parserSanity": {"loadedAugments": 1},
        "payloadHealth": {"summary": {"status": "ok"}},
    }

    stripped = runtime_payload(payload, include_legacy_fields=False, include_inline_diagnostics=False)

    assert "items" in stripped
    assert "modifierAudits" not in stripped
    assert "payloadHealth" not in stripped
    assert "uniqueGloves" not in stripped


def test_diagnostics_payload_collects_report_fields_without_runtime_arrays() -> None:
    payload = {
        "schemaVersion": "poc-0.21",
        "parserVersion": "test",
        "generatedAt": "2026-05-16T00:00:00+00:00",
        "source": "poe2db",
        "items": [{"name": "Treefingers"}],
        "modifierAudits": [{"sourceUrl": "https://example.test"}],
        "dataSnapshots": [],
        "parserSanity": {"loadedAugments": 1},
        "payloadHealth": {"summary": {"status": "ok"}},
    }

    diagnostics = diagnostics_payload(
        payload,
        build_options={"mode": "strict"},
        runtime_options={"includeLegacyFields": False},
    )

    assert diagnostics["diagnosticsVersion"] == 2
    assert diagnostics["buildOptions"] == {"mode": "strict"}
    assert diagnostics["runtimeOptions"] == {"includeLegacyFields": False}
    assert diagnostics["parserSanity"] == {"loadedAugments": 1}
    assert "items" not in diagnostics
    assert diagnostics["deprecatedRuntimeFields"][0]["field"] in {"uniqueBoots", "uniqueGloves", "uniqueHelmets"}


def test_diagnostics_helpers_normalise_legacy_string_warnings() -> None:
    assert warning(code="test_warning", message="Something happened") == {
        "severity": "warning",
        "code": "test_warning",
        "message": "Something happened",
        "actionRequired": False,
    }
    assert normalise_diagnostic("legacy warning", default_code="legacy") == {
        "severity": "warning",
        "code": "legacy",
        "message": "legacy warning",
        "actionRequired": False,
    }


def test_shared_augment_classification_is_name_and_detail_aware() -> None:
    assert classify_augment_name("Soul Core of Tacati") == "soul_core"
    assert classify_augment_name("Desert Rune") == "rune_item"

    entry = {"section": "Augment Item", "category": "soul_core", "name": "Soul Core of Tacati"}
    augment = {
        "name": "Soul Core of Tacati",
        "tooltipSections": [
            {"kind": "description", "lines": ["Place into an empty Augment Socket in a Weapon or Armour."]}
        ],
        "augmentEffects": [{"condition": "armour", "bonded": False, "text": "+11% to Chaos Resistance"}],
    }

    assert socket_candidate_reason(entry, augment) == "augment_socket_description"


def test_runtime_payload_options_support_slim_output() -> None:
    payload = {
        "schemaVersion": "poc-0.21",
        "parserVersion": "test",
        "generatedAt": "2026-05-16T00:00:00+00:00",
        "source": "poe2db",
        "sourceUrls": [],
        "items": [],
        "augment": {},
        "augments": [],
        "augmentCatalogue": None,
        "itemClasses": [],
        "itemSubtypes": [],
        "normalExplicitPools": [],
        "editorModifierPools": [],
        "modifierSourceMechanics": [],
        "modifierAudits": [],
        "baseItems": [],
        "uniqueItems": [],
        "uniqueGloves": [{"name": "legacy"}],
        "uniqueBoots": [],
        "uniqueHelmets": [],
        "dataSnapshots": [],
        "parserSanity": {},
        "payloadHealth": {},
    }

    options = RuntimePayloadOptions.from_slim_flag(True)
    slim = runtime_payload_from_options(payload, options)

    assert options.as_dict() == {"includeLegacyFields": False, "includeInlineDiagnostics": False}
    assert "uniqueGloves" not in slim
    assert "parserSanity" not in slim
    assert "uniqueItems" in slim
