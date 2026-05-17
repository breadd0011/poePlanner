from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_PATH = ROOT / "out" / "poe2db_payload_health_report.json"


def _load_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Health report not found: {path}\n"
            "Run scraper\\scripts\\generate_payload.bat first, then run scraper\\scripts\\show_health_report.bat again."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _metric(row: dict[str, Any], key: str) -> str:
    metric = row.get(key) or {}
    return f"{metric.get('withValue', 0)}/{metric.get('total', row.get('total', 0))}"


def _print_unique_items(report: dict[str, Any]) -> None:
    unique = report.get("uniqueItems") or {}
    by_class = unique.get("byClass") or {}
    print(f"Unique items: {unique.get('total', 0)}")
    if not by_class:
        print("  - none")
        return
    for item_class, row in sorted(by_class.items()):
        print(
            "  - "
            f"{item_class}: "
            f"{row.get('total', 0)} total, "
            f"{_metric(row, 'icon')} icon, "
            f"{_metric(row, 'flavourText')} flavourText, "
            f"{_metric(row, 'explicitMods')} explicitMods"
        )




def _print_weapon_unique_production(report: dict[str, Any]) -> None:
    weapon = report.get("weaponUniqueProduction") or {}
    if not weapon:
        return
    summary = weapon.get("summary") or {}
    print(
        "Weapon unique production: "
        f"{str(weapon.get('status', 'unknown')).upper()} "
        f"({summary.get('importedUniqueItems', 0)}/{summary.get('expectedUniqueItems', 0)} imported, "
        f"{summary.get('weaponUniqueClassesOk', 0)}/{summary.get('weaponUniqueClasses', 0)} classes OK, "
        f"{summary.get('classesWithUniques', 0)} classes with uniques)"
    )
    for item_class, row in sorted((weapon.get("byClass") or {}).items()):
        icon = row.get("icon") or {}
        flavour = row.get("flavourText") or {}
        explicit = row.get("explicitMods") or {}
        total = int(row.get("total") or 0)
        print(
            "  - "
            f"{item_class}: [{row.get('status', 'unknown')}] "
            f"{total}/{row.get('expectedTotal', 0)} uniques, "
            f"{icon.get('withValue', 0)}/{total} icon, "
            f"{flavour.get('withValue', 0)}/{total} flavourText, "
            f"{explicit.get('withValue', 0)}/{total} explicitMods"
        )

def _print_base_items(report: dict[str, Any]) -> None:
    base = report.get("baseItems") or {}
    by_class = base.get("byClass") or {}
    print(f"Base items: {base.get('total', 0)}")
    if not by_class:
        print("  - none")
        return
    for item_class, row in sorted(by_class.items()):
        print(
            "  - "
            f"{item_class}: "
            f"{row.get('total', 0)} total, "
            f"{_metric(row, 'icon')} icon, "
            f"{_metric(row, 'sourceUrl')} sourceUrl"
        )


def _print_modifier_coverage(report: dict[str, Any]) -> None:
    coverage = report.get("modifierCoverage") or {}
    summary = coverage.get("summary") or {}
    by_class = coverage.get("byClass") or {}
    if not by_class:
        return

    if summary:
        print(
            "Modifier coverage: "
            f"{summary.get('requiredClassesOk', 0)}/{summary.get('requiredClasses', 0)} required ok; "
            f"{summary.get('experimentalClassesReady', 0)}/{summary.get('experimentalClasses', 0)} experimental ready"
        )
    else:
        print("Modifier coverage:")

    priority = {"required": 0, "experimental": 1, "unsupported": 2}
    for item_class, row in sorted(by_class.items(), key=lambda item: (priority.get(str(item[1].get("supportState")), 9), item[0])):
        state = row.get("supportState", "unknown")
        status = row.get("coverageStatus") or row.get("status") or "unknown"
        if state == "unsupported" and status == "not_required":
            continue
        editor_pools = row.get("editorModifierPoolCount", (row.get("editor") or {}).get("pools", 0))
        editor_mods = row.get("editorModifierCount", (row.get("editor") or {}).get("mods", 0))
        normal_pools = row.get("normalExplicitPoolCount", (row.get("normalExplicit") or {}).get("pools", 0))
        prefixes = row.get("normalPrefixCount", (row.get("normalExplicit") or {}).get("prefixes", 0))
        suffixes = row.get("normalSuffixCount", (row.get("normalExplicit") or {}).get("suffixes", 0))
        base_total = ((row.get("baseItems") or {}).get("total")) or 0
        unique_total = ((row.get("uniqueItems") or {}).get("total")) or 0
        count_source = row.get("coverageCountSource") or "payload"
        line = (
            "  - "
            f"{item_class}: [{state}/{status}] "
            f"{base_total} base, {unique_total} unique, "
            f"{editor_pools} editor pools/{editor_mods} mods, "
            f"{normal_pools} normal pools/{prefixes} prefixes/{suffixes} suffixes"
        )
        if count_source != "payload":
            line += f", counts={count_source}"
        snapshot = row.get("snapshotStatus") or {}
        source_urls = [str(url) for url in (row.get("sourceUrls") or []) if str(url).strip()]
        source_url = str(row.get("sourceUrl") or "")
        if source_urls or source_url or snapshot:
            if len(source_urls) > 1:
                source_text = f"{len(source_urls)} sources, first={source_urls[0]}"
            else:
                source_text = source_urls[0] if source_urls else (source_url or "unknown")
            present = snapshot.get("modifiersCalcPresent")
            expected = snapshot.get("modifiersCalcExpected")
            if isinstance(present, int) and isinstance(expected, int) and expected > 1:
                modifiers_text = f"{snapshot.get('modifiersCalc', 'unknown')} ({present}/{expected})"
            else:
                modifiers_text = str(snapshot.get("modifiersCalc", "unknown"))
            line += (
                f", source={source_text}, "
                f"snapshots class={snapshot.get('classPage', 'unknown')}/modifiers={modifiers_text}"
            )
        print(line)


def _print_item_editor_binding(report: dict[str, Any]) -> None:
    binding = report.get("itemEditorBinding") or {}
    if not binding:
        return
    summary = binding.get("summary") or {}
    item_options = summary.get("itemOptions", 0)
    bindable_options = summary.get("bindableItemOptions", item_options)
    untyped_special = int(summary.get("untypedSpecialItemOptions") or 0)
    suffix = f"; {untyped_special} untyped special item options reported separately" if untyped_special else ""
    print(
        "Item editor binding: "
        f"{str(binding.get('status', 'unknown')).upper()} "
        f"({summary.get('optionsWithEditorPools', 0)}/{bindable_options} bindable editor-bound, "
        f"{summary.get('optionsWithNormalExplicitPools', 0)}/{bindable_options} bindable normal-bound"
        f"{suffix})"
    )
    for item_class, row in sorted((binding.get("byClass") or {}).items()):
        status = row.get("status", "unknown")
        if status not in {"ok", "missing_binding", "missing_visible_options"}:
            continue
        print(
            "  - "
            f"{item_class}: [{status}] "
            f"{row.get('totalItemOptions', 0)} item options, "
            f"{row.get('editorPools', 0)} editor pools, "
            f"{row.get('normalExplicitPools', 0)} normal pools"
            + (f", {row.get('untypedSpecialItemOptions', 0)} untyped special" if int(row.get('untypedSpecialItemOptions') or 0) else "")
        )
    for item_class, row in sorted((binding.get("excludedClasses") or {}).items()):
        print(
            "  - "
            f"excluded {item_class}: [{row.get('status', 'unknown')}] "
            f"{row.get('baseOptions', 0)} base, "
            f"{row.get('uniqueOptions', 0)} unique, "
            f"{row.get('editorPools', 0)} editor pools, "
            f"{row.get('normalExplicitPools', 0)} normal pools"
        )




def _print_unique_editor_binding(report: dict[str, Any]) -> None:
    binding = report.get("uniqueEditorBinding") or {}
    if not binding:
        return
    summary = binding.get("summary") or {}
    unique_options = int(summary.get("uniqueOptions") or 0)
    bindable = int(summary.get("bindableUniqueOptions") or unique_options)
    untyped_special = int(summary.get("untypedSpecialUniqueOptions") or 0)
    suffix = f"; {untyped_special} untyped special unique options reported separately" if untyped_special else ""
    print(
        "Unique editor binding: "
        f"{str(binding.get('status', 'unknown')).upper()} "
        f"({summary.get('optionsWithBaseItems', 0)}/{unique_options} base-matched, "
        f"{summary.get('optionsWithEditorPools', 0)}/{bindable} bindable editor-bound, "
        f"{summary.get('optionsWithNormalExplicitPools', 0)}/{bindable} bindable normal-bound"
        f"{suffix})"
    )
    for item_class, row in sorted((binding.get("byClass") or {}).items()):
        status = row.get("status", "unknown")
        if status not in {"ok", "missing_base_item", "missing_binding"}:
            continue
        print(
            "  - "
            f"{item_class}: [{status}] "
            f"{row.get('uniqueOptions', 0)} unique options, "
            f"{row.get('optionsWithBaseItems', 0)} base-matched, "
            f"{row.get('editorPools', 0)} editor pools, "
            f"{row.get('normalExplicitPools', 0)} normal pools"
            + (f", {row.get('untypedSpecialUniqueOptions', 0)} untyped special" if int(row.get('untypedSpecialUniqueOptions') or 0) else "")
        )
    for item_class, row in sorted((binding.get("excludedClasses") or {}).items()):
        print(
            "  - "
            f"excluded unique {item_class}: [{row.get('status', 'unknown')}] "
            f"{row.get('uniqueOptions', 0)} unique, "
            f"{row.get('editorPools', 0)} editor pools, "
            f"{row.get('normalExplicitPools', 0)} normal pools"
        )

def _print_modifier_pools(report: dict[str, Any]) -> None:
    pools = report.get("modifierPools") or {}
    if not pools:
        return

    editor = pools.get("editor") or {}
    normal = pools.get("normalExplicit") or {}
    print("Modifier pools:")
    print(f"  - editor pools: {editor.get('poolCount', 0)}")
    print(f"  - editor mods: {editor.get('modCount', 0)}")
    print(f"  - normal pools: {normal.get('poolCount', 0)}")
    print(f"  - normal prefixes: {normal.get('prefixCount', 0)}")
    print(f"  - normal suffixes: {normal.get('suffixCount', 0)}")


def _print_warnings(report: dict[str, Any]) -> None:
    warnings = report.get("warnings") or []
    print(f"Warnings: {len(warnings)}")
    for warning in warnings[:20]:
        severity = warning.get("severity", "warning")
        code = warning.get("code", "")
        message = warning.get("message", "")
        print(f"  - [{severity}] {code}: {message}")
    if len(warnings) > 20:
        print(f"  ... {len(warnings) - 20} more warnings not shown")


def main(argv: list[str]) -> int:
    report_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_REPORT_PATH
    try:
        report = _load_report(report_path)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Payload health: {str(report.get('status', 'unknown')).upper()}")
    if report.get("generatedAt"):
        print(f"Generated at: {report.get('generatedAt')}")
    if report.get("schemaVersion"):
        print(f"Schema version: {report.get('schemaVersion')}")
    if report.get("parserVersion"):
        print(f"Parser version: {report.get('parserVersion')}")
    print()

    _print_unique_items(report)
    print()
    _print_weapon_unique_production(report)
    if report.get("weaponUniqueProduction"):
        print()
    _print_base_items(report)
    print()
    _print_modifier_coverage(report)
    if report.get("modifierCoverage"):
        print()
    _print_item_editor_binding(report)
    if report.get("itemEditorBinding"):
        print()
    _print_unique_editor_binding(report)
    if report.get("uniqueEditorBinding"):
        print()
    _print_modifier_pools(report)
    if report.get("modifierPools"):
        print()
    _print_warnings(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
