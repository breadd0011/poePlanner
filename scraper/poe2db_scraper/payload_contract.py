from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

RUNTIME_PAYLOAD_KEYS = {
    "schemaVersion",
    "parserVersion",
    "generatedAt",
    "source",
    "sourceUrls",
    "items",
    "augment",
    "augments",
    "augmentCatalogue",
    "itemClasses",
    "itemSubtypes",
    "normalExplicitPools",
    "editorModifierPools",
    "modifierSourceMechanics",
    "baseItems",
    "uniqueItems",
}

LEGACY_PAYLOAD_KEYS = {"uniqueGloves", "uniqueBoots", "uniqueHelmets"}
DIAGNOSTIC_PAYLOAD_KEYS = {"modifierAudits", "dataSnapshots", "parserSanity", "payloadHealth"}

LEGACY_FIELD_DEPRECATIONS: dict[str, dict[str, str]] = {
    "uniqueGloves": {
        "replacement": "uniqueItems filtered by itemClass == 'Gloves'",
        "reason": "Class-specific unique arrays duplicate uniqueItems and increase frontend payload size.",
    },
    "uniqueBoots": {
        "replacement": "uniqueItems filtered by itemClass == 'Boots'",
        "reason": "Class-specific unique arrays duplicate uniqueItems and increase frontend payload size.",
    },
    "uniqueHelmets": {
        "replacement": "uniqueItems filtered by itemClass == 'Helmets'",
        "reason": "Class-specific unique arrays duplicate uniqueItems and increase frontend payload size.",
    },
}


@dataclass(frozen=True)
class RuntimePayloadOptions:
    """Options for shaping the frontend-facing JSON artifact."""

    include_legacy_fields: bool = True
    include_inline_diagnostics: bool = True

    @classmethod
    def from_slim_flag(cls, slim: bool) -> "RuntimePayloadOptions":
        if slim:
            return cls(include_legacy_fields=False, include_inline_diagnostics=False)
        return cls()

    def as_dict(self) -> dict[str, bool]:
        return {
            "includeLegacyFields": self.include_legacy_fields,
            "includeInlineDiagnostics": self.include_inline_diagnostics,
        }


def deprecated_runtime_fields() -> list[dict[str, str]]:
    return [
        {
            "field": field,
            "replacement": metadata["replacement"],
            "reason": metadata["reason"],
        }
        for field, metadata in sorted(LEGACY_FIELD_DEPRECATIONS.items())
    ]


def runtime_payload(
    payload: dict[str, Any],
    *,
    include_legacy_fields: bool = True,
    include_inline_diagnostics: bool = True,
) -> dict[str, Any]:
    """Return the frontend-facing subset of the payload.

    The default keeps the current backwards-compatible UI payload shape. Passing
    include_inline_diagnostics=False and include_legacy_fields=False writes the
    smaller future runtime payload while diagnostics remain available in the
    separate diagnostics artifact.
    """
    keys = set(RUNTIME_PAYLOAD_KEYS)
    if include_legacy_fields:
        keys.update(LEGACY_PAYLOAD_KEYS)
    if include_inline_diagnostics:
        keys.update(DIAGNOSTIC_PAYLOAD_KEYS)
    return {key: copy.deepcopy(payload[key]) for key in payload if key in keys}


def runtime_payload_from_options(payload: dict[str, Any], options: RuntimePayloadOptions) -> dict[str, Any]:
    return runtime_payload(
        payload,
        include_legacy_fields=options.include_legacy_fields,
        include_inline_diagnostics=options.include_inline_diagnostics,
    )


def diagnostics_payload(
    payload: dict[str, Any],
    *,
    build_options: dict[str, Any] | None = None,
    runtime_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the separate diagnostics/report artifact for scraper and CI use."""
    return {
        "schemaVersion": payload.get("schemaVersion"),
        "parserVersion": payload.get("parserVersion"),
        "generatedAt": payload.get("generatedAt"),
        "source": payload.get("source"),
        "diagnosticsVersion": 2,
        "buildOptions": copy.deepcopy(build_options or {}),
        "runtimeOptions": copy.deepcopy(runtime_options or {}),
        "parserSanity": copy.deepcopy(payload.get("parserSanity") or {}),
        "payloadHealth": copy.deepcopy(payload.get("payloadHealth") or {}),
        "modifierAudits": copy.deepcopy(payload.get("modifierAudits") or []),
        "dataSnapshots": copy.deepcopy(payload.get("dataSnapshots") or []),
        "deprecatedRuntimeFields": deprecated_runtime_fields(),
        "futureRuntimePayloadKeys": sorted(RUNTIME_PAYLOAD_KEYS),
        "diagnosticPayloadKeys": sorted(DIAGNOSTIC_PAYLOAD_KEYS),
    }
