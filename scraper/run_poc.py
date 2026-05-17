from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from poe2db_scraper.builder import ValidationError, build_poc_payload
from poe2db_scraper.console import configure_color, heading, label, paint
from poe2db_scraper.health_report import print_payload_health_report
from poe2db_scraper.models import ui_payload_json_schema
from poe2db_scraper.payload_contract import RuntimePayloadOptions, diagnostics_payload, runtime_payload_from_options
from poe2db_scraper.schema import BuildPaths
from poe2db_scraper.snapshot_updater import update_category_snapshots


def _display_path(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)

def _write_json_artifact(path: Path, payload: object, *, repo_root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{paint('Wrote', 'info')} {paint(_display_path(path, repo_root), 'path')}")


def _copy_artifact(source: Path, target: Path, *, repo_root: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    print(f"{paint('Copied', 'info')} {paint(_display_path(target, repo_root), 'path')}")




def _print_section(title: str) -> None:
    print("")
    print(heading(title))


def _print_outcome(prefix: str, message: str) -> None:
    severity = prefix.strip().lower()
    print(f"  {label(prefix, severity)}: {message}")

def _int_value(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _augment_warning_summary(warning: dict[str, object]) -> str:
    code = str(warning.get("code") or "augment_warning")
    severity = str(warning.get("severity") or "warning")
    augment_name = str(warning.get("augmentName") or "").strip()
    message = str(warning.get("message") or "").strip()
    prefix = label(f"{severity.upper()} {code}", severity)
    if augment_name:
        prefix = f"{prefix} [{augment_name}]"
    return f"{prefix}: {message}" if message else prefix


def _warning_code_counts(warnings: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(warnings, list):
        return counts
    for warning in warnings:
        if isinstance(warning, dict):
            code = str(warning.get("code") or "warning")
        else:
            code = "warning"
        counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items()))


def _warning_names(warnings: object, code: str, *, limit: int = 6) -> list[str]:
    names: list[str] = []
    if not isinstance(warnings, list):
        return names
    for warning in warnings:
        if not isinstance(warning, dict) or str(warning.get("code") or "") != code:
            continue
        name = str(warning.get("augmentName") or warning.get("section") or "").strip()
        if name and name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return names


def _format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def _print_warning_groups(warnings: object, *, indent: str = "  ", sample_limit: int = 5) -> None:
    counts = _warning_code_counts(warnings)
    if not counts:
        print(f"{indent}{label('Warnings', 'ok')}: none")
        return
    print(f"{indent}{label('Warnings by code', 'warning')}: {_format_counts(counts)}")
    if isinstance(warnings, list):
        for code in counts:
            names = _warning_names(warnings, code, limit=sample_limit)
            if names:
                suffix = "" if counts[code] <= len(names) else f", +{counts[code] - len(names)} more"
                print(f"{indent}  {code}: {', '.join(names)}{suffix}")


def _format_label_count(discovered: int, expected_raw: object) -> str:
    if expected_raw is None:
        return f"{discovered} discovered"
    expected = _int_value(expected_raw)
    if discovered > expected:
        return f"{discovered} discovered (label count {expected}, +{discovered - expected} extra classified links)"
    if discovered == expected:
        return f"{discovered} discovered (label count {expected})"
    return f"{discovered} discovered (below label count {expected})"


def print_augment_coverage_summary(ui_payload: dict[str, object], *, detail: str = "full") -> None:
    sanity = ui_payload.get("parserSanity") if isinstance(ui_payload, dict) else None
    if not isinstance(sanity, dict):
        return
    coverage = sanity.get("augmentCoverage")
    if not isinstance(coverage, dict):
        return

    expected = _int_value(coverage.get("expected"), 42)
    loaded = _int_value(coverage.get("loaded"))
    discovered = _int_value(coverage.get("discovered"))
    with_normal = _int_value(coverage.get("withNormalEffects"))
    with_bonded = _int_value(coverage.get("withBondedEffects"))
    with_icons = _int_value(coverage.get("withIcons"))
    with_requirements = _int_value(coverage.get("withRequirements"))
    complete = bool(coverage.get("complete"))

    _print_section("Rune augment coverage")
    print(f"  Loaded: {loaded} / {expected}; discovered in index: {discovered} / {expected}")
    print(f"  Effects/icons: normal {with_normal}/{loaded}, bonded {with_bonded}/{loaded}, icons {with_icons}/{loaded}, requirements {with_requirements}/{loaded}")

    source_counts = coverage.get("dataSourceCounts")
    if isinstance(source_counts, dict) and source_counts:
        print(f"  Data sources: {_format_counts({str(k): _int_value(v) for k, v in source_counts.items()})}")

    validation_warnings = coverage.get("validationWarnings")
    missing_bonded = coverage.get("missingBondedEffects")
    if isinstance(missing_bonded, list) and missing_bonded:
        sample = ", ".join(str(name) for name in missing_bonded[:6])
        remaining = len(missing_bonded) - min(len(missing_bonded), 6)
        suffix = f", +{remaining} more" if remaining else ""
        print(f"  Missing bonded effects: {len(missing_bonded)} ({sample}{suffix})")

    if detail == "compact":
        _print_warning_groups(validation_warnings, indent="  ")
    elif isinstance(validation_warnings, list) and validation_warnings:
        print("  Warnings:")
        for warning in validation_warnings[:12]:
            if isinstance(warning, dict):
                print(f"    - {_augment_warning_summary(warning)}")
            else:
                print(f"    - {warning}")
        remaining = len(validation_warnings) - 12
        if remaining > 0:
            print(f"    - ... {remaining} more warning(s); inspect scraper/out/poe2db_poc_diagnostics.json")

    if loaded <= 1 and expected > 1:
        _print_outcome("ACTION", "Only one rune augment is loaded. Run scraper\\scripts\\refresh_rune_augments.bat or run python scraper\\run_poc.py with --force-refresh.")
    elif with_normal < loaded:
        _print_outcome("ACTION", "Rune augment coverage is incomplete because one or more normal effects are missing. Inspect poe2db_poc_diagnostics.json.")
    elif _int_value((coverage.get("warningCounts") or {}).get("error")) or _int_value((coverage.get("warningCounts") or {}).get("warning")):
        _print_outcome("REVIEW", "Rune data loaded, but warnings remain. Inspect poe2db_poc_diagnostics.json before exposing new socket behavior.")
    elif not complete:
        _print_outcome("REVIEW", "Rune augment coverage has non-blocking gaps, usually requirements or bonded effects. Inspect diagnostics if these matter to the UI.")
    else:
        _print_outcome("OK", "Rune augment coverage looks complete.")


def print_augment_catalogue_summary(ui_payload: dict[str, object], *, detail: str = "full") -> None:
    catalogue = ui_payload.get("augmentCatalogue") if isinstance(ui_payload, dict) else None
    if not isinstance(catalogue, dict):
        return
    entries = catalogue.get("entries")
    if not isinstance(entries, list):
        return

    total = _int_value(catalogue.get("total"), len(entries))
    socket_candidates = _int_value(catalogue.get("socketCandidateCount"))
    catalogue_only = max(total - socket_candidates, 0)

    _print_section("Augment catalogue registry")
    print(f"  Entries: {total}; socket picker candidates: {socket_candidates}; catalogue-only: {catalogue_only}")
    if detail == "full":
        print(f"  Socket picker candidates: {socket_candidates}")
        print(f"  Catalogue-only entries: {catalogue_only}")
        print(f"  Detail loaded: {_int_value(catalogue.get('detailLoadedCount'))}")
        print(f"  Index-only: {_int_value(catalogue.get('indexOnlyCount'))}")
    print(f"  Detail: loaded {_int_value(catalogue.get('detailLoadedCount'))}, failed {_int_value(catalogue.get('detailFailedCount'))}, index-only {_int_value(catalogue.get('indexOnlyCount'))}, with parsed effects {_int_value(catalogue.get('entriesWithEffects'))}")

    section_counts = catalogue.get("sectionCounts")
    if isinstance(section_counts, dict) and section_counts:
        print(f"  Sections: {_format_counts({str(k): _int_value(v) for k, v in section_counts.items()})}")

    category_counts = catalogue.get("categoryCounts")
    if isinstance(category_counts, dict) and category_counts:
        print(f"  Categories: {_format_counts({str(k): _int_value(v) for k, v in category_counts.items()})}")

    if detail == "full":
        detail_status_counts = catalogue.get("detailStatusCounts")
        if isinstance(detail_status_counts, dict) and detail_status_counts:
            print(f"  Detail statuses: {_format_counts({str(k): _int_value(v) for k, v in detail_status_counts.items()})}")

        detail_source_counts = catalogue.get("detailSourceCounts")
        if isinstance(detail_source_counts, dict) and detail_source_counts:
            print(f"  Detail sources: {_format_counts({str(k): _int_value(v) for k, v in detail_source_counts.items()})}")

    if total and socket_candidates == total:
        _print_outcome("NOTE", "All catalogue entries are currently socket candidates; verify classification before exposing new entries in the picker.")
    else:
        _print_outcome("OK", "Non-rune catalogue entries are retained read-only and filtered out of the socket picker.")


def print_socket_candidate_guardrail_summary(ui_payload: dict[str, object], *, detail: str = "full") -> None:
    catalogue = ui_payload.get("augmentCatalogue") if isinstance(ui_payload, dict) else None
    audit = catalogue.get("socketCandidateAudit") if isinstance(catalogue, dict) else None
    if not isinstance(audit, dict):
        return

    _print_section("Socket-compatible augment guardrails")
    print(
        "  Candidates: "
        f"{_int_value(audit.get('socketCandidateCount'))} total; "
        f"Rune Item {_int_value(audit.get('runeItemCandidates'))}, "
        f"Soul Core {_int_value(audit.get('soulCoreCandidates'))}, "
        f"other {_int_value(audit.get('otherSocketableAugments'))}; "
        f"excluded refs {_int_value(audit.get('excludedReferenceEntries'))}"
    )
    if detail == "full":
        print(f"  Rune Item candidates: {_int_value(audit.get('runeItemCandidates'))}")
        print(f"  Soul Core candidates: {_int_value(audit.get('soulCoreCandidates'))}")
        print(f"  Other socketable augments: {_int_value(audit.get('otherSocketableAugments'))}")
        print(f"  Excluded reference entries: {_int_value(audit.get('excludedReferenceEntries'))}")

    by_category = audit.get("socketCandidatesByCategory")
    if isinstance(by_category, dict) and by_category:
        print(f"  By category: {_format_counts({str(k): _int_value(v) for k, v in by_category.items()})}")

    by_reason = audit.get("socketCandidatesByReason")
    if isinstance(by_reason, dict) and by_reason:
        print(f"  By reason: {_format_counts({str(k): _int_value(v) for k, v in by_reason.items()})}")

    warnings = audit.get("validationWarnings")
    if isinstance(warnings, list) and warnings:
        if detail == "full":
            print("  Warnings:")
        _print_warning_groups(warnings, indent="  ")
        if detail == "full":
            print("  Warning details:")
            for warning in warnings[:12]:
                if isinstance(warning, dict):
                    print(f"    - {_augment_warning_summary(warning)}")
                else:
                    print(f"    - {warning}")
            remaining = len(warnings) - 12
            if remaining > 0:
                print(f"    - ... {remaining} more warning(s); inspect scraper/out/poe2db_poc_diagnostics.json")
        else:
            _print_outcome("REVIEW", "Some socket candidates lack explicit parsed equipment targets. Keep them behind diagnostics until target mapping is confirmed.")
    else:
        _print_outcome("OK", "Socket-compatible augment picker guardrails passed.")


def print_augment_index_audit_summary(ui_payload: dict[str, object], *, detail: str = "full") -> None:
    sanity = ui_payload.get("parserSanity") if isinstance(ui_payload, dict) else None
    if not isinstance(sanity, dict):
        return
    audit = sanity.get("augmentIndexAudit")
    if not isinstance(audit, dict):
        return

    sections = audit.get("sections")
    if not isinstance(sections, list) or not sections:
        return

    discovered_total = _int_value(audit.get("discoveredTotal"))
    expected_total = _int_value(audit.get("expectedTotal"))
    _print_section("Augment index classification audit")
    if detail == "compact" and expected_total and discovered_total > expected_total:
        print(f"  Catalogue links discovered: {discovered_total} (label total {expected_total}, +{discovered_total - expected_total} extra classified links)")
    else:
        print(f"  Catalogue links discovered: {discovered_total} / {expected_total}")
    category_counts = audit.get("categoryCounts")
    if isinstance(category_counts, dict) and category_counts:
        print(f"  Classification buckets: {_format_counts({str(k): _int_value(v) for k, v in category_counts.items()})}")

    for section in sections:
        if not isinstance(section, dict):
            continue
        name = str(section.get("section") or "unknown")
        discovered = _int_value(section.get("discovered"))
        expected_raw = section.get("expected")
        socket_candidates = _int_value(section.get("socketCandidateCount"))
        if detail == "compact":
            print(f"  {name}: {_format_label_count(discovered, expected_raw)}, socket candidates={socket_candidates}")
        else:
            expected_text = str(expected_raw) if expected_raw is not None else "?"
            print(f"  {name}: {discovered} / {expected_text} discovered, socket candidates={socket_candidates}")

    warnings = audit.get("validationWarnings")
    if isinstance(warnings, list) and warnings:
        if detail == "compact":
            _print_warning_groups(warnings, indent="  ")
        else:
            print("  Audit warnings:")
            for warning in warnings[:8]:
                if isinstance(warning, dict):
                    print(f"    - {_augment_warning_summary(warning)}")
                else:
                    print(f"    - {warning}")
            remaining = len(warnings) - 8
            if remaining > 0:
                print(f"    - ... {remaining} more warning(s); inspect scraper/out/poe2db_poc_diagnostics.json")

def main() -> int:
    parser = argparse.ArgumentParser(description="PoE2DB planner data import POC")
    parser.add_argument("--force-refresh", action="store_true", help="Ignore cache and re-download all locked POC target pages")
    parser.add_argument("--build-mode", choices=["dev", "strict"], default="dev", help="dev allows local/cache fallbacks; strict disables previous generated output reuse and stale-cache fallback")
    parser.add_argument("--update-snapshots", action="store_true", help="Fetch supported category + subtype HTML into .cache and data before building")
    parser.add_argument("--categories", default="Gloves,Boots,Helmets", help="Comma-separated snapshot categories for --update-snapshots. Examples: Gloves,Boots,Helmets,Body Armours,Shields,Foci,Quivers,Rings,Amulets,Belts,Weapons")
    parser.add_argument("--skip-unique-details", action="store_true", help="With --update-snapshots, refresh class/subtype pages but skip unique detail page downloads")
    parser.add_argument("--debug", action="store_true", help="Also write scraper/out/poe2db_poc_debug.json")
    parser.add_argument("--write-schema", action="store_true", help="Also write scraper/out/poe2db_poc_schema.json")
    parser.add_argument("--write-snapshots", action="store_true", help="Write dated data/snapshots entries during the payload build")
    parser.add_argument("--write-modifier-html-cache", action="store_true", help="Persist fetched ModifiersCalc full HTML fixtures under scraper/data")
    parser.add_argument("--copy-web", action="store_true", help="Copy generated payload/report files into ../web/public/data when the web project exists")
    parser.add_argument("--slim-ui-payload", action="store_true", help="Write the smaller future runtime payload without legacy unique arrays or inline diagnostics")
    parser.add_argument("--report-detail", choices=["compact", "full"], default="compact", help="Console summary detail level. compact keeps the CLI readable; full prints per-class rows and warning details.")
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto", help="Colorize console output. auto uses color only for interactive terminals.")
    parser.add_argument("--no-color", action="store_true", help="Alias for --color never; useful for CI logs and redirected output.")
    args = parser.parse_args()
    configure_color("never" if args.no_color else args.color)

    project_root = Path(__file__).resolve().parent
    paths = BuildPaths(project_root=project_root)
    repo_root = paths.repo_root
    paths.out_dir.mkdir(parents=True, exist_ok=True)
    if args.copy_web:
        paths.web_data_dir.mkdir(parents=True, exist_ok=True)

    if args.update_snapshots:
        report = update_category_snapshots(
            paths,
            categories=[part for part in args.categories.split(",") if part.strip()],
            force_refresh=True,
            include_unique_details=not args.skip_unique_details,
            verbose=True,
        )
        paths.out_dir.mkdir(parents=True, exist_ok=True)
        snapshot_report_path = paths.out_dir / "poe2db_snapshot_update_report.json"
        _write_json_artifact(snapshot_report_path, report, repo_root=repo_root)
        _print_outcome("OK", f"Updated PoE2DB snapshots for: {', '.join(report['categories'].keys())}")

    try:
        ui_payload, debug_payload = build_poc_payload(
            paths,
            force_refresh=args.force_refresh and not args.update_snapshots,
            build_mode=args.build_mode,
            write_snapshots=args.write_snapshots,
            write_modifier_html_cache=args.write_modifier_html_cache,
        )
    except ValidationError as exc:
        print(label("Validation failed:", "error"), file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    runtime_options = RuntimePayloadOptions.from_slim_flag(args.slim_ui_payload)
    ui_runtime_payload = runtime_payload_from_options(ui_payload, runtime_options)
    _write_json_artifact(paths.ui_json_path, ui_runtime_payload, repo_root=repo_root)
    if args.slim_ui_payload:
        _print_outcome("INFO", "Wrote slim UI payload: inline diagnostics and legacy unique arrays are available in diagnostics/debug artifacts only.")

    if args.copy_web:
        _copy_artifact(paths.ui_json_path, paths.web_ui_json_path, repo_root=repo_root)
        legacy_web_src_json_path = paths.web_root / "src" / "data" / "poe2db_poc_ui.json"
        if legacy_web_src_json_path.parent.exists():
            _copy_artifact(paths.ui_json_path, legacy_web_src_json_path, repo_root=repo_root)

    health_report = ui_payload.get("payloadHealth") or {}
    _write_json_artifact(paths.health_report_json_path, health_report, repo_root=repo_root)

    scraper_diagnostics = diagnostics_payload(
        ui_payload,
        build_options=debug_payload.get("buildOptions") if isinstance(debug_payload, dict) else None,
        runtime_options=runtime_options.as_dict(),
    )
    _write_json_artifact(paths.diagnostics_json_path, scraper_diagnostics, repo_root=repo_root)

    if args.copy_web:
        _copy_artifact(paths.health_report_json_path, paths.web_health_report_json_path, repo_root=repo_root)
        _copy_artifact(paths.diagnostics_json_path, paths.web_diagnostics_json_path, repo_root=repo_root)
    print_payload_health_report(health_report, detail=args.report_detail)
    print_augment_coverage_summary(ui_payload, detail=args.report_detail)
    print_augment_catalogue_summary(ui_payload, detail=args.report_detail)
    print_socket_candidate_guardrail_summary(ui_payload, detail=args.report_detail)
    print_augment_index_audit_summary(ui_payload, detail=args.report_detail)

    if args.debug:
        _write_json_artifact(paths.debug_json_path, debug_payload, repo_root=repo_root)

    if args.write_schema:
        _write_json_artifact(paths.json_schema_path, ui_payload_json_schema(), repo_root=repo_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
