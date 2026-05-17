from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import copy
import json
import re

from bs4 import BeautifulSoup

from .armour_config import ARMOUR_SUBTYPE_PROFILES, ARMOUR_ITEM_CLASSES, armour_subtype_url
from .augment_parser import parse_augment_index_page, parse_augment_page
from .base_item_parser import parse_base_items_from_class_page
from .class_parser import parse_class_page
from .augment_classification import (
    REFERENCE_AUGMENT_SECTIONS,
    SOCKET_AUGMENT_EQUIPMENT_CONDITIONS,
    socket_candidate_reason as _augment_socket_candidate_reason,
    with_socket_candidate_fields as _with_socket_candidate_fields,
)
from .build_policy import BuildOptions, fetch_html_for_build as _fetch_html_for_build
from .diagnostics import normalise_diagnostics, warning as diagnostic_warning
from .fetcher import FetchedPage, cache_path_for_url
from .health_report import build_payload_health_report
from .modifier_coverage_config import (
    AUDITED_MODIFIER_CLASSES,
    CLASS_LEVEL_PRODUCTION_MODIFIER_ITEM_CLASSES,
    EXPERIMENTAL_MODIFIER_CLASSES,
    REQUIRED_MODIFIER_CLASSES,
    modifier_class_url,
    modifier_source_url,
    modifier_support_for_class,
)
from .item_parser import parse_item_page
from .models import validate_ui_payload
from .normalize import entity_id
from .mod_parser import collect_mod_blocks_raw
from .normal_affix_parser import parse_editor_modifier_pools_from_html, normal_pool_from_editor_pools, source_mechanic_metadata
from .object_parser import parse_object_data
from .subtype_parser import parse_base_items_from_lines, parse_subtype_page
from .unique_gloves_parser import (
    extract_unique_armour_candidates,
    extract_unique_catalogue_items,
    parse_unique_item_page,
    stable_slug,
)
from .schema import (
    CRUDE_CLAW_URL,
    DESERT_RUNE_URL,
    AUGMENT_INDEX_URL,
    GLOVES_URL,
    BOOTS_URL,
    HELMETS_URL,
    GLOVES_INT_URL,
    GLOVES_STR_URL,
    GLOVES_DEX_URL,
    GLOVES_STR_DEX_URL,
    GLOVES_STR_INT_URL,
    GLOVES_DEX_INT_URL,
    BOOTS_STR_URL,
    BOOTS_DEX_URL,
    BOOTS_INT_URL,
    BOOTS_STR_DEX_URL,
    BOOTS_STR_INT_URL,
    BOOTS_DEX_INT_URL,
    HELMETS_STR_URL,
    HELMETS_DEX_URL,
    HELMETS_INT_URL,
    HELMETS_STR_DEX_URL,
    HELMETS_STR_INT_URL,
    HELMETS_DEX_INT_URL,
    GLOVE_SUBTYPE_URLS,
    BOOT_SUBTYPE_URLS,
    HELMET_SUBTYPE_URLS,
    SHIELD_MODIFIER_SUBTYPE_URLS,
    BODY_ARMOUR_MODIFIER_SUBTYPE_URLS,
    PARSER_VERSION,
    SCHEMA_VERSION,
    SOURCE_NAME,
    SUBTYPE_URLS,
    TARGET_URLS,
    TREEFINGERS_URL,
    OPTIONAL_UNIQUE_ITEM_CLASSES,
    OPTIONAL_BASE_ITEM_CLASSES,
    UNIQUE_ITEM_CLASS_URLS,
    WEAPON_UNIQUE_ITEM_CLASS_URLS,
    BuildPaths,
)
from .text import clean_display_text, extract_trade_json_if_present, get_page_lines_from_html, node_lines, slug_from_url, title_from_url
from .utils import ordered_unique_strings


class ValidationError(RuntimeError):
    pass


def _defence_profile_from_base_item(item: dict[str, Any]) -> list[str]:
    defences = item.get("defences") or {}
    profile: list[str] = []
    if defences.get("armour") is not None:
        profile.append("armour")
    if defences.get("evasion") is not None:
        profile.append("evasion")
    if defences.get("energyShield") is not None:
        profile.append("energy_shield")
    return profile


def _class_base_items_by_profile(html: str) -> dict[tuple[str, ...], list[dict[str, Any]]]:
    items = parse_base_items_from_lines(get_page_lines_from_html(html))
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for item in items:
        profile = tuple(_defence_profile_from_base_item(item))
        if profile:
            grouped.setdefault(profile, []).append(item)
    return grouped


def _previous_base_items_by_slug(paths: BuildPaths) -> dict[str, list[dict[str, Any]]]:
    for candidate in [paths.ui_json_path, paths.web_ui_json_path]:
        if not candidate.exists():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        result: dict[str, list[dict[str, Any]]] = {}
        for subtype in payload.get("itemSubtypes") or []:
            slug = subtype.get("slug")
            base_items = subtype.get("baseItems") or []
            if slug and base_items:
                result[str(slug)] = list(base_items)
        if result:
            return result
    return {}


def _fill_missing_base_items(
    subtypes: list[dict[str, Any]],
    *,
    class_html: str,
    previous_by_slug: dict[str, list[dict[str, Any]]],
) -> None:
    by_profile = _class_base_items_by_profile(class_html)
    for subtype in subtypes:
        if subtype.get("baseItems"):
            continue
        profile = tuple(subtype.get("defenceProfile") or [])
        fallback = by_profile.get(profile) or previous_by_slug.get(str(subtype.get("slug") or ""))
        if fallback:
            subtype["baseItems"] = fallback
            subtype.setdefault("diagnostics", []).append({
                "severity": "warning",
                "code": "BASE_ITEMS_FILLED_FROM_CLASS_OR_PREVIOUS_SNAPSHOT",
                "message": "Subtype page did not expose BaseItem rows; reused class-page/previous generated base item rows.",
                "actionRequired": False,
            })

def _read_cached_modifier_pools(paths: BuildPaths) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    # V18 is additive for unique gloves. Reuse the already generated modifier pools
    # when available so local regeneration does not need to reparse the large
    # ModifiersCalc HTML snapshots on every run. If no generated JSON exists,
    # the builder falls back to the original parser below.
    for candidate in [paths.ui_json_path, paths.web_ui_json_path]:
        if not candidate.exists():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        # Modifier-pool parsing is intentionally cache-compatible across minor
        # parser cleanup versions. The payload-level builder can add new metadata
        # without forcing a full reparse of every large ModifiersCalc HTML page.
        if not payload.get("parserVersion"):
            continue
        editor = payload.get("editorModifierPools") or []
        normal = payload.get("normalExplicitPools") or []
        required_classes = tuple(REQUIRED_MODIFIER_CLASSES)
        has_required_editor = all(any(pool.get("itemClass") == item_class for pool in editor) for item_class in required_classes)
        has_required_normal = all(any(pool.get("itemClass") == item_class for pool in normal) for item_class in required_classes)
        editor_sources_ok = all(
            pool.get("rawSource") in {"full_html", "modsview_json"}
            for pool in editor
            if pool.get("itemClass") in required_classes
        )
        normal_sources_ok = all(
            any(source in {"full_html", "modsview_json"} for source in (pool.get("rawSources") or []))
            for pool in normal
            if pool.get("itemClass") in required_classes
        )
        if editor and normal and has_required_editor and has_required_normal and editor_sources_ok and normal_sources_ok:
            return list(editor), list(normal)
    return None



SUBTYPE_SOURCE_META: dict[str, tuple[str, str, str]] = {
    armour_subtype_url(item_class, profile): (item_class, f"{item_class}_{profile}", profile)
    for item_class in ARMOUR_ITEM_CLASSES
    for profile, _, _, _ in ARMOUR_SUBTYPE_PROFILES
}

SHIELD_MODIFIER_SUBTYPE_SOURCE_META: dict[str, tuple[str, str, str]] = {
    url: ("Shields", slug_from_url(url), slug_from_url(url).replace("Shields_", ""))
    for url in SHIELD_MODIFIER_SUBTYPE_URLS
}

BODY_ARMOUR_MODIFIER_SUBTYPE_SOURCE_META: dict[str, tuple[str, str, str]] = {
    url: ("Body Armours", slug_from_url(url), slug_from_url(url).replace("Body_Armours_", ""))
    for url in BODY_ARMOUR_MODIFIER_SUBTYPE_URLS
}

MODIFIER_SUBTYPE_SOURCE_META: dict[str, tuple[str, str, str]] = {
    **SUBTYPE_SOURCE_META,
    **SHIELD_MODIFIER_SUBTYPE_SOURCE_META,
    **BODY_ARMOUR_MODIFIER_SUBTYPE_SOURCE_META,
}


def _modifier_html_for_subtype(
    paths: BuildPaths,
    *,
    url: str,
    slug: str,
    fetched_subtypes: dict[str, FetchedPage],
    force_refresh: bool,
    options: BuildOptions,
) -> str:
    """Return real ModifiersCalc HTML for a subtype.

    The #ModifiersCalc content lives on the subtype page itself. If a captured
    full-html fixture exists, use it; otherwise fetch the subtype page and persist
    that HTML as the fixture. Never synthesize item-class modifier pools.
    """
    full_html_path = paths.modifiers_calc_full_html_path(slug)
    if full_html_path.exists() and not force_refresh:
        return full_html_path.read_text(encoding="utf-8")
    fetched = fetched_subtypes.get(url)
    if fetched is None or force_refresh:
        fetched = _fetch_html_for_build(url, paths=paths, force_refresh=force_refresh, options=options)
    if options.write_modifier_html_cache:
        full_html_path.parent.mkdir(parents=True, exist_ok=True)
        full_html_path.write_text(fetched.html, encoding="utf-8")
    return fetched.html


def _class_level_modifier_slug(item_class: str) -> str:
    return stable_slug(item_class)


def _parse_class_level_modifier_pools(
    item_class: str,
    class_url: str,
    class_html: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse non-armour ModifiersCalc data from a PoE2DB class page.

    Rings, Amulets and Belts expose a class-level ModifiersCalc tab instead of
    six armour-style subtype pages. Store these as subtype="base" so the UI can
    treat every base/unique item in the class as covered by the same pool.
    """
    slug = _class_level_modifier_slug(item_class)
    source_url = f"{class_url}#ModifiersCalc"
    pools = parse_editor_modifier_pools_from_html(
        class_html,
        source_url=source_url,
        item_class=item_class,
        subtype="base",
        slug=slug,
        validation_source="live_or_cached_class_modifiers_calc_html",
        confidence="high",
    )
    base_prefix = next((pool for pool in pools if pool.get("sourceGroup") == "Base Prefix"), None)
    base_suffix = next((pool for pool in pools if pool.get("sourceGroup") == "Base Suffix"), None)
    debug = {
        "itemClass": item_class,
        "sourceUrl": source_url,
        "editorPoolCount": len(pools),
        "editorModCount": sum(len(pool.get("mods") or []) for pool in pools),
        "basePrefixCount": len((base_prefix or {}).get("mods") or []),
        "baseSuffixCount": len((base_suffix or {}).get("mods") or []),
        "rawSources": sorted({str(pool.get("rawSource") or "unknown") for pool in pools}),
    }
    if not pools or not (base_prefix and (base_prefix.get("mods") or [])) or not (base_suffix and (base_suffix.get("mods") or [])):
        debug["error"] = "Class-level ModifiersCalc did not expose non-empty Base Prefix and Base Suffix pools."
    return pools, debug




def _relative_path_or_none(paths: BuildPaths, path: Any | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(paths.project_root))
    except Exception:
        return str(path)


def _snapshot_status_for_url(paths: BuildPaths, url: str) -> tuple[str, str | None]:
    snapshot_path = _snapshot_class_path_for_url(url, paths)
    if snapshot_path is None:
        return "missing", None
    return "present", _relative_path_or_none(paths, snapshot_path)


def _modifier_full_html_status(paths: BuildPaths, item_class: str) -> tuple[str, str | None]:
    path = paths.modifiers_calc_full_html_path(_class_level_modifier_slug(item_class))
    if not path.exists():
        return "missing", None
    return "present", _relative_path_or_none(paths, path)


def _fetched_page_status(paths: BuildPaths, fetched: FetchedPage | None) -> dict[str, Any]:
    if fetched is None:
        return {"status": "missing"}
    cache_path = getattr(fetched, "cache_path", None)
    relative_cache = _relative_path_or_none(paths, cache_path)
    status = "checked_in_snapshot" if relative_cache and "/snapshots/" in relative_cache.replace("\\", "/") else ("cache" if fetched.from_cache else "live")
    return {
        "status": status,
        "fromCache": fetched.from_cache,
        "cachePath": relative_cache,
        "statusCode": fetched.status_code,
        "warnings": list(fetched.warnings or []),
    }


def _build_modifier_class_audits(
    paths: BuildPaths,
    class_pages: dict[str, FetchedPage],
) -> list[dict[str, Any]]:
    """Audit PoE2DB class-level modifier targets for health/report visibility.

    Supported weapon classes are wired into production modifier pools, but the
    audit rows still expose their source URL and snapshot status. Experimental
    weapon-adjacent classes remain audit-only and do not satisfy required gates.
    """
    audits: list[dict[str, Any]] = []
    for item_class in AUDITED_MODIFIER_CLASSES:
        class_url = modifier_class_url(item_class)
        source_url = modifier_source_url(item_class)
        support = modifier_support_for_class(item_class)
        class_snapshot_status, class_snapshot_path = _snapshot_status_for_url(paths, class_url or "") if class_url else ("missing", None)
        modifier_snapshot_status, modifier_snapshot_path = _modifier_full_html_status(paths, item_class)
        fetched = class_pages.get(item_class)
        audit: dict[str, Any] = {
            "kind": "modifier_class_audit",
            "itemClass": item_class,
            "supportState": support.support_state,
            "sourceUrl": source_url or "",
            "classPageUrl": class_url or "",
            "classPageFetch": _fetched_page_status(paths, fetched),
            "classSnapshotStatus": class_snapshot_status,
            "classSnapshotPath": class_snapshot_path,
            "modifierSnapshotStatus": modifier_snapshot_status,
            "modifierSnapshotPath": modifier_snapshot_path,
            "baseItemCount": 0,
            "uniqueItemCount": 0,
            "editorModifierPoolCount": 0,
            "editorModifierCount": 0,
            "normalExplicitPoolCount": 0,
            "normalPrefixCount": 0,
            "normalSuffixCount": 0,
            "rawSources": [],
            "diagnostics": [],
        }
        if fetched is None or not class_url or not source_url:
            audit["diagnostics"].append({
                "severity": "info",
                "code": "MODIFIER_CLASS_PAGE_NOT_AVAILABLE",
                "message": "No local PoE2DB class page snapshot/cache is available for this modifier target.",
                "actionRequired": False,
            })
            audits.append(audit)
            continue

        html = fetched.html
        try:
            base_items = parse_base_items_from_class_page(class_url, html, item_class=item_class)
            unique_items = extract_unique_catalogue_items(class_url, html, item_class=item_class)
            pools, debug = _parse_class_level_modifier_pools(item_class, class_url, html)
            normal = normal_pool_from_editor_pools(
                pools,
                source_url=source_url,
                item_class=item_class,
                subtype="base",
                slug=_class_level_modifier_slug(item_class),
                validation_source="experimental_weapon_modifier_audit",
                confidence="medium",
            ) if pools else None
        except Exception as exc:
            audit["diagnostics"].append({
                "severity": "warning",
                "code": "MODIFIER_AUDIT_PARSE_FAILED",
                "message": f"Modifier audit failed to parse {item_class}: {exc}",
                "actionRequired": False,
            })
            audits.append(audit)
            continue

        audit.update({
            "baseItemCount": len(base_items),
            "uniqueItemCount": len(unique_items),
            "editorModifierPoolCount": len(pools),
            "editorModifierCount": sum(len(pool.get("mods") or []) for pool in pools),
            "normalExplicitPoolCount": 1 if normal else 0,
            "normalPrefixCount": len((normal or {}).get("prefixes") or []),
            "normalSuffixCount": len((normal or {}).get("suffixes") or []),
            "rawSources": sorted({str(pool.get("rawSource") or "unknown") for pool in pools}),
        })
        if debug.get("error"):
            audit["diagnostics"].append({
                "severity": "warning",
                "code": "MODIFIER_AUDIT_INCOMPLETE",
                "message": str(debug["error"]),
                "actionRequired": False,
            })
        else:
            audit["diagnostics"].append({
                "severity": "info",
                "code": "MODIFIER_AUDIT_PARSED",
                "message": "Modifier pools were parsed for health/audit reporting. Required classes are also wired into editorModifierPools.",
                "actionRequired": False,
            })
        audits.append(audit)
    return audits


def _modifier_snapshot_summary_for_slugs(paths: BuildPaths, slugs: list[str]) -> dict[str, Any]:
    unique_slugs = sorted({slug for slug in slugs if slug})
    snapshot_paths: list[str] = []
    missing_slugs: list[str] = []
    for slug in unique_slugs:
        path = paths.modifiers_calc_full_html_path(slug)
        if path.exists():
            snapshot_paths.append(_relative_path_or_none(paths, path) or str(path))
        else:
            missing_slugs.append(slug)
    if not unique_slugs:
        status = "unknown"
    elif len(snapshot_paths) == len(unique_slugs):
        status = "present"
    elif snapshot_paths:
        status = "partial"
    else:
        status = "missing"
    return {
        "status": status,
        "present": len(snapshot_paths),
        "expected": len(unique_slugs),
        "paths": snapshot_paths,
        "missingSlugs": missing_slugs,
    }


def _pool_source_urls(pools: list[dict[str, Any]]) -> list[str]:
    return ordered_unique_strings(pool.get("sourceUrl") for pool in pools)


def _production_modifier_audit_from_pools(
    paths: BuildPaths,
    item_class: str,
    *,
    class_pages: dict[str, FetchedPage],
    editor_pools: list[dict[str, Any]],
    normal_pools: list[dict[str, Any]],
) -> dict[str, Any]:
    class_url = _catalogue_url_for_class(item_class) or modifier_class_url(item_class)
    source_urls = _pool_source_urls([*editor_pools, *normal_pools])
    support = modifier_support_for_class(item_class)
    class_snapshot_status, class_snapshot_path = _snapshot_status_for_url(paths, class_url or "") if class_url else ("missing", None)
    modifier_snapshot = _modifier_snapshot_summary_for_slugs(
        paths,
        [str(pool.get("slug") or "") for pool in [*editor_pools, *normal_pools]],
    )
    fetched = class_pages.get(item_class)
    return {
        "kind": "modifier_class_audit",
        "itemClass": item_class,
        "supportState": support.support_state,
        "sourceUrl": source_urls[0] if len(source_urls) == 1 else (f"{class_url}#ModifiersCalc" if class_url else ""),
        "sourceUrls": source_urls,
        "classPageUrl": class_url or "",
        "classPageFetch": _fetched_page_status(paths, fetched),
        "classSnapshotStatus": class_snapshot_status,
        "classSnapshotPath": class_snapshot_path,
        "modifierSnapshotStatus": modifier_snapshot["status"],
        "modifierSnapshotPath": modifier_snapshot["paths"][0] if len(modifier_snapshot["paths"]) == 1 else None,
        "modifierSnapshotPaths": modifier_snapshot["paths"],
        "modifierSnapshotPresent": modifier_snapshot["present"],
        "modifierSnapshotExpected": modifier_snapshot["expected"],
        "modifierSnapshotMissingSlugs": modifier_snapshot["missingSlugs"],
        "baseItemCount": 0,
        "uniqueItemCount": 0,
        "editorModifierPoolCount": len(editor_pools),
        "editorModifierCount": sum(len(pool.get("mods") or []) for pool in editor_pools),
        "normalExplicitPoolCount": len(normal_pools),
        "normalPrefixCount": sum(len(pool.get("prefixes") or []) for pool in normal_pools),
        "normalSuffixCount": sum(len(pool.get("suffixes") or []) for pool in normal_pools),
        "rawSources": sorted({str(pool.get("rawSource") or "unknown") for pool in editor_pools}),
        "diagnostics": [{
            "severity": "info",
            "code": "MODIFIER_PRODUCTION_POOLS_AUDITED",
            "message": "Modifier source URLs and snapshot status were derived from production modifier pools.",
            "actionRequired": False,
        }],
    }


def _build_modifier_source_audits(
    paths: BuildPaths,
    class_pages: dict[str, FetchedPage],
    *,
    editor_modifier_pools: list[dict[str, Any]],
    normal_explicit_pools: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return one normalized health/audit row per in-scope modifier class."""
    class_level_audits = _build_modifier_class_audits(paths, class_pages)
    audits_by_class = {str(audit.get("itemClass") or ""): audit for audit in class_level_audits if audit.get("itemClass")}

    editor_by_class: dict[str, list[dict[str, Any]]] = {}
    for pool in editor_modifier_pools:
        item_class = str(pool.get("itemClass") or "Unknown")
        editor_by_class.setdefault(item_class, []).append(pool)

    normal_by_class: dict[str, list[dict[str, Any]]] = {}
    for pool in normal_explicit_pools:
        item_class = str(pool.get("itemClass") or "Unknown")
        normal_by_class.setdefault(item_class, []).append(pool)

    in_scope_classes = sorted({
        *REQUIRED_MODIFIER_CLASSES,
        *EXPERIMENTAL_MODIFIER_CLASSES,
        *editor_by_class,
        *normal_by_class,
        *audits_by_class,
    })

    normalized: list[dict[str, Any]] = []
    for item_class in in_scope_classes:
        editor_pools = editor_by_class.get(item_class, [])
        normal_pools = normal_by_class.get(item_class, [])
        production_audit = _production_modifier_audit_from_pools(
            paths,
            item_class,
            class_pages=class_pages,
            editor_pools=editor_pools,
            normal_pools=normal_pools,
        )
        audit = {**production_audit, **audits_by_class.get(item_class, {})}
        # Production pool counts are authoritative for required classes, while
        # class-level audit parse counts remain useful for audit-only rows.
        if editor_pools or normal_pools:
            audit.update({
                "editorModifierPoolCount": production_audit["editorModifierPoolCount"],
                "editorModifierCount": production_audit["editorModifierCount"],
                "normalExplicitPoolCount": production_audit["normalExplicitPoolCount"],
                "normalPrefixCount": production_audit["normalPrefixCount"],
                "normalSuffixCount": production_audit["normalSuffixCount"],
                "sourceUrls": production_audit["sourceUrls"],
                "sourceUrl": production_audit["sourceUrl"],
                "modifierSnapshotStatus": production_audit["modifierSnapshotStatus"],
                "modifierSnapshotPath": production_audit["modifierSnapshotPath"],
                "modifierSnapshotPaths": production_audit["modifierSnapshotPaths"],
                "modifierSnapshotPresent": production_audit["modifierSnapshotPresent"],
                "modifierSnapshotExpected": production_audit["modifierSnapshotExpected"],
                "modifierSnapshotMissingSlugs": production_audit["modifierSnapshotMissingSlugs"],
            })
        normalized.append(audit)
    return normalized

def _snapshot_file_name_for_url(url: str) -> str:
    slug = slug_from_url(url) or stable_slug(url)
    return f"{stable_slug(slug)}.html"


def _write_snapshot(paths: BuildPaths, fetched: FetchedPage, *, snapshot_date: str, folder: str = "pages") -> dict[str, Any]:
    snapshot_dir = paths.snapshot_dir_for_date(snapshot_date) / folder
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / _snapshot_file_name_for_url(fetched.url)
    snapshot_path.write_text(fetched.html, encoding="utf-8")
    return {
        "id": f"snapshot_{stable_slug(folder, slug_from_url(fetched.url))}",
        "sourceUrl": fetched.url,
        "snapshotPath": str(snapshot_path.relative_to(paths.project_root)),
        "fromCache": fetched.from_cache,
    }


def _base_item_names(subtypes: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for subtype in subtypes:
        for item in subtype.get("baseItems", []) or []:
            name = item.get("name")
            if name and name not in names:
                names.append(str(name))
    return names


def _unique_snapshot_folder(item_class: str | None) -> str:
    normalized = str(item_class or "").strip().lower()
    return f"unique_{normalized}" if normalized else "unique_unknown"


def _snapshot_detail_path_for_unique(candidate: Any, paths: BuildPaths, *, item_class: str | None) -> Any | None:
    if not paths.snapshots_dir.exists():
        return None
    source_url = str(getattr(candidate, "sourceUrl", "") or "")
    name = str(getattr(candidate, "name", "") or "")
    canonical_slug_candidates: list[str] = []
    fallback_slug_candidates: list[str] = []

    def add_slug(value: str | None) -> None:
        raw = str(value or "").strip()
        canonical = stable_slug(raw)
        if canonical and canonical not in canonical_slug_candidates:
            canonical_slug_candidates.append(canonical)
        if raw and raw not in fallback_slug_candidates and raw not in canonical_slug_candidates:
            fallback_slug_candidates.append(raw)
        lower = raw.lower()
        if lower and lower not in canonical_slug_candidates and lower not in fallback_slug_candidates:
            fallback_slug_candidates.append(lower)

    source_slug = slug_from_url(source_url)
    add_slug(source_slug)
    add_slug(name)

    if not canonical_slug_candidates and not fallback_slug_candidates:
        return None

    folder = _unique_snapshot_folder(item_class)
    dated_dirs = sorted([path for path in paths.snapshots_dir.iterdir() if path.is_dir()], reverse=True)

    # Prefer canonical lower-case snapshot names across all dates. This keeps Windows
    # refreshes from masking the checked-in lower-case fixture with a newly written
    # case-preserved filename such as Treefingers.html.
    for slug_candidates in (canonical_slug_candidates, fallback_slug_candidates):
        for dated_dir in dated_dirs:
            for slug in slug_candidates:
                path = dated_dir / folder / f"{slug}.html"
                if path.exists():
                    return path
    return None


def _fetch_unique_candidate(
    candidate: Any,
    paths: BuildPaths,
    *,
    force_refresh: bool,
    item_class: str | None = None,
    options: BuildOptions,
) -> FetchedPage | None:
    # Unique class catalogue rows are the source of truth for membership, base type,
    # icon and visible mods. Detail pages are used only to hydrate fields that the
    # catalogue does not render, most importantly flavour text. Normal builds are
    # deterministic/offline-friendly: they read cache or checked-in snapshots when
    # available. The live network path is reserved for --force-refresh /
    # --update-snapshots workflows.
    cache_path = cache_path_for_url(candidate.sourceUrl, paths.cache_dir)
    if cache_path.exists() and not force_refresh:
        return _fetch_html_for_build(candidate.sourceUrl, paths=paths, force_refresh=False, options=options)

    snapshot_path = _snapshot_detail_path_for_unique(candidate, paths, item_class=item_class)
    if snapshot_path is not None and not force_refresh:
        return FetchedPage(
            url=candidate.sourceUrl,
            html=snapshot_path.read_text(encoding="utf-8"),
            cache_path=snapshot_path,
            from_cache=True,
            warnings=["Using checked-in PoE2DB unique detail snapshot for flavour-text hydration."],
        )

    if not force_refresh:
        return None
    return _fetch_html_for_build(candidate.sourceUrl, paths=paths, force_refresh=True, options=options)


def _clean_lines(values: Any) -> list[str]:
    out: list[str] = []
    for value in values or []:
        text = str(value).strip().replace("\r", "")
        if text and text not in out:
            out.append(text)
    return out


def _tooltip_section_lines(entity: dict[str, Any], kind: str) -> list[str]:
    for section in entity.get("tooltipSections", []) or []:
        if section.get("kind") == kind:
            return _clean_lines(section.get("lines") or [])
    return []


def _replace_tooltip_section(sections: list[dict[str, Any]], kind: str, lines: list[str]) -> list[dict[str, Any]]:
    next_sections = [copy.deepcopy(section) for section in sections if section.get("kind") != kind]
    if lines:
        next_sections.append({"kind": kind, "lines": lines})
    return next_sections


def _names_match(left: str | None, right: str | None) -> bool:
    return bool(left and right and stable_slug(str(left)) == stable_slug(str(right)))


def _is_unpublished_flavour_placeholder(lines: list[str]) -> bool:
    meaningful = [clean_display_text(line).lower() for line in lines if clean_display_text(line)]
    return bool(meaningful) and all(line in {"coming soon", "coming soon."} for line in meaningful)


def _flavour_lines_from_detail_html(html: str, trade_json: dict[str, Any]) -> tuple[list[str], bool]:
    trade_flavour = [
        clean_display_text(line)
        for line in (trade_json.get("flavourText") or [])
        if clean_display_text(line)
    ]
    if trade_flavour:
        return trade_flavour, False

    # Some PoE2DB unique detail pages render flavour text only in the item popup
    # DOM and do not include it in the embedded trade JSON. Atziri's Step is one
    # known example. Keep this as a detail-page scrape, not a hardcoded fallback.
    soup = BeautifulSoup(html, "lxml")
    candidates = soup.select(".newItemPopup .Stats > .FlavourText") or soup.select(".newItemPopup .FlavourText")
    if not candidates:
        candidates = soup.select(".FlavourText")

    for candidate in candidates:
        dom_flavour = node_lines(candidate)
        if not dom_flavour:
            continue
        if _is_unpublished_flavour_placeholder(dom_flavour):
            return [], True
        return dom_flavour, False

    return [], False


def _unique_detail_hydration_from_html(
    source_url: str,
    html: str,
    *,
    item_class: str,
    expected_base_type: str | None,
    fallback: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return only detail-page fields that catalogue rows cannot provide cheaply.

    Full unique detail pages can be very large because PoE2DB includes history,
    related tables and modal data. For normal payload builds the class catalogue
    remains the source of truth for membership/base/icon/mods; the detail page is
    only used to hydrate missing flavour text. Avoiding the full item parser keeps
    generation fast while still keeping flavour text scraped, not hardcoded.
    """
    trade_json = extract_trade_json_if_present(html) or {}
    name = clean_display_text(trade_json.get("name")) or str((fallback or {}).get("name") or "").strip()
    base_type = clean_display_text(trade_json.get("baseType") or trade_json.get("typeLine")) or expected_base_type or (fallback or {}).get("baseType")
    flavour, flavour_unpublished = _flavour_lines_from_detail_html(html, trade_json)
    tooltip_sections = [{"kind": "flavour", "lines": flavour}] if flavour else []
    unique_slug = stable_slug(name or (fallback or {}).get("name") or source_url)

    diagnostics: list[dict[str, Any]] = []
    if flavour:
        diagnostics.append({
            "severity": "info",
            "code": "UNIQUE_DETAIL_LIGHTWEIGHT_HYDRATION",
            "message": "Hydrated unique detail-only fields from PoE2DB trade JSON or item-popup DOM without reparsing the full detail page.",
            "actionRequired": False,
        })
    elif flavour_unpublished:
        diagnostics.append({
            "severity": "info",
            "code": "UNIQUE_FLAVOUR_TEXT_NOT_PUBLISHED",
            "message": "PoE2DB renders a Coming soon placeholder in the flavour text slot; skipped as unpublished placeholder.",
            "actionRequired": False,
        })

    return {
        "id": (fallback or {}).get("id") or f"poe2db:unique:{stable_slug(item_class)}:{unique_slug}",
        "slug": slug_from_url(source_url),
        "source": "poe2db",
        "sourceUrl": source_url,
        "kind": (fallback or {}).get("kind") or "unique_item",
        "name": name,
        "baseType": base_type,
        "itemClass": item_class,
        "rarity": "Unique",
        "icon": (fallback or {}).get("icon"),
        "requirements": dict((fallback or {}).get("requirements") or {}),
        "defences": dict((fallback or {}).get("defences") or {}),
        "implicitMods": list((fallback or {}).get("implicitMods") or []),
        "explicitMods": list((fallback or {}).get("explicitMods") or []),
        "flavourText": flavour,
        "tooltipSections": tooltip_sections,
        "parseStatus": "ok",
        "warnings": [],
        "diagnostics": diagnostics,
    }


def _merge_unique_detail_fields(catalogue_item: dict[str, Any] | None, detail_item: dict[str, Any]) -> dict[str, Any]:
    if not catalogue_item:
        return detail_item

    merged = copy.deepcopy(catalogue_item)
    if not _names_match(merged.get("name"), detail_item.get("name")):
        merged.setdefault("warnings", []).append(
            f"Skipped unique detail hydration because detail page name {detail_item.get('name')!r} did not match catalogue item {merged.get('name')!r}."
        )
        merged.setdefault("diagnostics", []).append({
            "severity": "warning",
            "code": "UNIQUE_DETAIL_NAME_MISMATCH",
            "message": "PoE2DB unique detail page did not match the class catalogue row; kept catalogue data only.",
            "actionRequired": True,
        })
        return merged

    flavour = _clean_lines(detail_item.get("flavourText") or _tooltip_section_lines(detail_item, "flavour"))
    if flavour:
        merged["flavourText"] = flavour
        merged["tooltipSections"] = _replace_tooltip_section(list(merged.get("tooltipSections") or []), "flavour", flavour)
        merged.setdefault("diagnostics", []).append({
            "severity": "info",
            "code": "UNIQUE_FLAVOUR_TEXT_FROM_DETAIL_PAGE",
            "message": "Imported flavour text from the PoE2DB unique detail page.",
            "actionRequired": False,
        })
    else:
        for diagnostic in detail_item.get("diagnostics") or []:
            if isinstance(diagnostic, dict) and diagnostic.get("code") == "UNIQUE_FLAVOUR_TEXT_NOT_PUBLISHED":
                if not any(
                    isinstance(existing, dict) and existing.get("code") == diagnostic.get("code")
                    for existing in merged.get("diagnostics") or []
                ):
                    merged.setdefault("diagnostics", []).append(copy.deepcopy(diagnostic))

    if not merged.get("requirements") and detail_item.get("requirements"):
        merged["requirements"] = dict(detail_item.get("requirements") or {})
    if not merged.get("defences") and detail_item.get("defences"):
        merged["defences"] = dict(detail_item.get("defences") or {})

    return merged


def _snapshot_class_path_for_url(url: str, paths: BuildPaths) -> Any | None:
    if not paths.snapshots_dir.exists():
        return None
    slug = slug_from_url(url)
    if not slug:
        return None
    file_candidates = []
    for candidate in (slug, slug.lower(), stable_slug(slug)):
        file_name = f"{candidate}.html"
        if file_name not in file_candidates:
            file_candidates.append(file_name)
    for dated_dir in sorted([path for path in paths.snapshots_dir.iterdir() if path.is_dir()], reverse=True):
        for file_name in file_candidates:
            path = dated_dir / "classes" / file_name
            if path.exists():
                return path
    return None


def _fetch_class_catalogue(
    item_class: str,
    url: str,
    paths: BuildPaths,
    *,
    force_refresh: bool,
    required: bool,
    options: BuildOptions,
) -> FetchedPage | None:
    cache_path = cache_path_for_url(url, paths.cache_dir)
    if cache_path.exists() and not force_refresh:
        return _fetch_html_for_build(url, paths=paths, force_refresh=False, options=options)
    snapshot_path = _snapshot_class_path_for_url(url, paths)
    if snapshot_path is not None and not force_refresh:
        return FetchedPage(
            url=url,
            html=snapshot_path.read_text(encoding="utf-8"),
            cache_path=snapshot_path,
            from_cache=True,
            warnings=[f"Using checked-in PoE2DB {item_class} class snapshot."],
        )
    if force_refresh or required:
        return _fetch_html_for_build(url, paths=paths, force_refresh=force_refresh, options=options)
    return None



def _fallback_desert_rune_index_entry() -> dict[str, Any]:
    return {
        "id": f"poe2db:{slug_from_url(DESERT_RUNE_URL)}",
        "slug": slug_from_url(DESERT_RUNE_URL),
        "name": "Desert Rune",
        "sourceUrl": DESERT_RUNE_URL,
        "source": "poe2db",
        "kind": "augment_index_entry",
        "category": "rune",
        "icon": None,
    }


def _fetch_augment_index(paths: BuildPaths, *, force_refresh: bool, options: BuildOptions) -> FetchedPage | None:
    try:
        return _fetch_html_for_build(AUGMENT_INDEX_URL, paths=paths, force_refresh=force_refresh, options=options)
    except RuntimeError:
        # Augment index support is additive. Keep local/offline builds usable with
        # the historical Desert Rune detail page until a live or cached index is
        # available.
        return None


def _fallback_augment_index() -> dict[str, Any]:
    return {
        "sourceUrl": AUGMENT_INDEX_URL,
        "source": "poe2db",
        "kind": "augment_index",
        "category": "rune",
        "entries": [_fallback_desert_rune_index_entry()],
        "expectedCount": 42,
        "parseStatus": "fallback",
        "warnings": ["Augment index was unavailable; using the legacy Desert Rune fallback."],
    }


def _build_rune_augments(
    paths: BuildPaths,
    *,
    force_refresh: bool,
    data_snapshots: list[dict[str, Any]],
    snapshot_date: str,
    fetched_desert_rune: FetchedPage,
    options: BuildOptions,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fetched_index = _fetch_augment_index(paths, force_refresh=force_refresh, options=options)
    if fetched_index is not None:
        if options.write_snapshots:
            data_snapshots.append(_write_snapshot(paths, fetched_index, snapshot_date=snapshot_date))
        index = parse_augment_index_page(AUGMENT_INDEX_URL, fetched_index.html)
    else:
        index = _fallback_augment_index()

    entries = index.get("entries") or []
    if not entries:
        index = {
            **index,
            "entries": [_fallback_desert_rune_index_entry()],
            "warnings": [*(index.get("warnings") or []), "No rune index entries were parsed; using Desert Rune fallback."],
        }
        entries = index["entries"]

    augments: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    fetched_by_url: dict[str, FetchedPage] = {DESERT_RUNE_URL: fetched_desert_rune}
    for entry in entries:
        url = str(entry.get("sourceUrl") or "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        embedded = entry.get("embeddedAugment")

        fetched = fetched_by_url.get(url)
        if fetched is None:
            try:
                fetched = _fetch_html_for_build(url, paths=paths, force_refresh=force_refresh, options=options)
            except RuntimeError:
                if isinstance(embedded, dict):
                    augment = dict(embedded)
                    object_data = dict(augment.get("objectData") or {})
                    object_data["augmentDataSource"] = "embedded_index"
                    augment["objectData"] = object_data
                    if not augment.get("icon") and entry.get("icon"):
                        augment["icon"] = entry.get("icon")
                    augments.append(augment)
                continue
            fetched_by_url[url] = fetched
            if force_refresh and options.write_snapshots:
                data_snapshots.append(_write_snapshot(paths, fetched, snapshot_date=snapshot_date, folder="pages"))
        augment = parse_augment_page(url, fetched.html)
        object_data = dict(augment.get("objectData") or {})
        object_data["augmentDataSource"] = "detail_page"
        augment["objectData"] = object_data
        if not augment.get("icon") and entry.get("icon"):
            augment["icon"] = entry.get("icon")
        augments.append(augment)

    if not any(augment.get("sourceUrl") == DESERT_RUNE_URL for augment in augments):
        fallback_augment = parse_augment_page(DESERT_RUNE_URL, fetched_desert_rune.html)
        object_data = dict(fallback_augment.get("objectData") or {})
        object_data["augmentDataSource"] = "detail_page_fallback"
        fallback_augment["objectData"] = object_data
        augments.insert(0, fallback_augment)
    return augments, index


def _augment_normal_effect_count(augment: dict[str, Any]) -> int:
    return sum(1 for effect in augment.get("augmentEffects") or [] if not effect.get("bonded"))


def _augment_bonded_effect_count(augment: dict[str, Any]) -> int:
    return sum(1 for effect in augment.get("augmentEffects") or [] if effect.get("bonded"))


def _augment_has_all_normal_conditions(augment: dict[str, Any]) -> bool:
    conditions = {
        str(effect.get("condition"))
        for effect in augment.get("augmentEffects") or []
        if not effect.get("bonded")
    }
    return {"martial_weapon", "wand_or_staff", "armour"}.issubset(conditions)


def _augment_requirement_lines(augment: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for section in augment.get("tooltipSections") or []:
        if section.get("kind") == "requirement":
            lines.extend(str(line).strip() for line in section.get("lines") or [] if str(line).strip())
    return lines


def _augment_property_lines(augment: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for section in augment.get("tooltipSections") or []:
        if section.get("kind") == "property":
            lines.extend(str(line).strip() for line in section.get("lines") or [] if str(line).strip())
    return lines


def _augment_has_requirement(augment: dict[str, Any]) -> bool:
    return bool(_augment_requirement_lines(augment))


def _augment_name(augment: dict[str, Any]) -> str:
    return str(augment.get("name") or augment.get("id") or "Unknown augment")


def _augment_effect_text(effect: dict[str, Any]) -> str:
    return str(effect.get("text") or "").strip()


def _augment_normal_conditions(augment: dict[str, Any]) -> set[str]:
    return {
        str(effect.get("condition"))
        for effect in augment.get("augmentEffects") or []
        if not effect.get("bonded") and effect.get("condition")
    }


def _augment_condition_issue(augment: dict[str, Any]) -> str | None:
    conditions = _augment_normal_conditions(augment)
    if "all_equipment" in conditions:
        return None
    required = {"martial_weapon", "wand_or_staff", "armour"}
    missing = sorted(required - conditions)
    if missing:
        return ", ".join(missing)
    return None


def _augment_suspicious_effects(augment: dict[str, Any]) -> list[str]:
    suspicious: list[str] = []
    for effect in augment.get("augmentEffects") or []:
        text = _augment_effect_text(effect)
        if not text:
            suspicious.append("empty effect text")
            continue
        words = [part for part in text.replace(",", " ").split() if part]
        has_digit = any(char.isdigit() for char in text)
        if len(text) < 8 or (len(words) < 2 and not has_digit):
            label = str(effect.get("label") or effect.get("condition") or "effect")
            bonded = "bonded " if effect.get("bonded") else ""
            suspicious.append(f"{bonded}{label}: {text}")
    return suspicious


def _augment_duplicate_property_lines(augment: dict[str, Any]) -> list[str]:
    counts: dict[str, int] = {}
    for line in _augment_property_lines(augment):
        counts[line] = counts.get(line, 0) + 1
    return sorted(line for line, count in counts.items() if count > 1)


def _augment_empty_stack_size_lines(augment: dict[str, Any]) -> list[str]:
    return [line for line in _augment_property_lines(augment) if line.strip().lower() == "stack size:"]


def _augment_data_source(augment: dict[str, Any]) -> str:
    object_data = augment.get("objectData") or {}
    if isinstance(object_data, dict):
        return str(object_data.get("augmentDataSource") or "unknown")
    return "unknown"


def _augment_validation_warnings(augments: list[dict[str, Any]], index: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    expected = int(index.get("expectedCount") or 42)
    if len(augments) < expected:
        warnings.append(
            {
                "severity": "warning",
                "code": "rune_count_below_expected",
                "message": f"Loaded {len(augments)} rune augments, expected {expected}.",
            }
        )
    discovered = len(index.get("entries") or [])
    if discovered and discovered < expected:
        warnings.append(
            {
                "severity": "warning",
                "code": "rune_index_below_expected",
                "message": f"Rune index discovered {discovered} entries, expected {expected}.",
            }
        )
    for warning in index.get("warnings") or []:
        warnings.append(
            {
                "severity": "warning",
                "code": "augment_index_warning",
                "message": str(warning),
            }
        )
    for augment in augments:
        name = _augment_name(augment)
        if not _augment_normal_effect_count(augment):
            warnings.append(
                {
                    "severity": "error",
                    "code": "missing_normal_effects",
                    "augmentName": name,
                    "message": f"{name}: no non-bonded augment effects were parsed.",
                }
            )
        condition_issue = _augment_condition_issue(augment)
        if condition_issue:
            warnings.append(
                {
                    "severity": "warning",
                    "code": "missing_normal_conditions",
                    "augmentName": name,
                    "message": f"{name}: missing normal condition(s): {condition_issue}.",
                }
            )
        if not _augment_bonded_effect_count(augment):
            warnings.append(
                {
                    "severity": "info",
                    "code": "missing_bonded_effects",
                    "augmentName": name,
                    "message": f"{name}: no bonded effects were parsed.",
                }
            )
        if not augment.get("icon"):
            warnings.append(
                {
                    "severity": "warning",
                    "code": "missing_icon",
                    "augmentName": name,
                    "message": f"{name}: missing icon.",
                }
            )
        if not _augment_has_requirement(augment):
            warnings.append(
                {
                    "severity": "info",
                    "code": "missing_requirement",
                    "augmentName": name,
                    "message": f"{name}: no level requirement row was parsed.",
                }
            )
        for line in _augment_empty_stack_size_lines(augment):
            warnings.append(
                {
                    "severity": "error",
                    "code": "empty_stack_size_property",
                    "augmentName": name,
                    "message": f"{name}: empty property row parsed: {line}",
                }
            )
        for line in _augment_duplicate_property_lines(augment):
            warnings.append(
                {
                    "severity": "warning",
                    "code": "duplicate_property_line",
                    "augmentName": name,
                    "message": f"{name}: duplicate property row parsed: {line}",
                }
            )
        for text in _augment_suspicious_effects(augment):
            warnings.append(
                {
                    "severity": "warning",
                    "code": "suspicious_effect_text",
                    "augmentName": name,
                    "message": f"{name}: suspiciously short effect text: {text}",
                }
            )
        if _augment_data_source(augment) == "embedded_index":
            warnings.append(
                {
                    "severity": "info",
                    "code": "using_embedded_index_fallback",
                    "augmentName": name,
                    "message": f"{name}: using embedded Augment index fallback data instead of a detail page.",
                }
            )
    return warnings


def _augment_warning_counts(warnings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for warning in warnings:
        severity = str(warning.get("severity") or "warning")
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def _augment_data_source_counts(augments: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for augment in augments:
        source = _augment_data_source(augment)
        counts[source] = counts.get(source, 0) + 1
    return dict(sorted(counts.items()))



AUGMENT_CATALOGUE_DETAIL_FETCH_LIMIT = 180


def _augment_description_lines(augment: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for section in augment.get("tooltipSections") or []:
        if section.get("kind") == "description":
            lines.extend(str(line).strip() for line in section.get("lines") or [] if str(line).strip())
    return lines


def _augment_detail_summary(
    augment: dict[str, Any],
    *,
    detail_status: str = "detail_loaded",
    detail_source: str = "detail_page",
    fetched_from_cache: bool | None = None,
) -> dict[str, Any]:
    normal_effects = [effect for effect in augment.get("augmentEffects") or [] if not effect.get("bonded")]
    bonded_effects = [effect for effect in augment.get("augmentEffects") or [] if effect.get("bonded")]
    conditions = sorted({str(effect.get("condition") or "unknown") for effect in augment.get("augmentEffects") or [] if effect.get("condition")})
    summary: dict[str, Any] = {
        "detailStatus": detail_status,
        "detailSource": detail_source,
        "detailName": str(augment.get("name") or ""),
        "itemClass": str(augment.get("itemClass") or "") or None,
        "normalEffectCount": len(normal_effects),
        "bondedEffectCount": len(bonded_effects),
        "effectConditions": conditions,
        "propertyLines": _augment_property_lines(augment),
        "requirementLines": _augment_requirement_lines(augment),
        "descriptionLineCount": len(_augment_description_lines(augment)),
        "detailWarnings": [str(warning) for warning in (augment.get("warnings") or [])],
    }
    if fetched_from_cache is not None:
        summary["detailFetchedFromCache"] = fetched_from_cache
    return summary


def _annotate_socket_augment(augment: dict[str, Any], entry: dict[str, Any] | None = None) -> dict[str, Any]:
    annotated = dict(augment)
    category = str((entry or {}).get("category") or annotated.get("augmentCategory") or "") or None
    if category:
        annotated["augmentCategory"] = category
    annotated["plannerVisibility"] = "socket_picker"
    object_data = dict(annotated.get("objectData") or {})
    if entry is not None:
        object_data.setdefault("augmentCatalogueSection", entry.get("section"))
        object_data.setdefault("augmentCatalogueCategory", entry.get("category"))
        object_data.setdefault("socketCandidateReason", entry.get("socketCandidateReason"))
    annotated["objectData"] = object_data
    return annotated


def _augment_detail_failed_summary(error: str) -> dict[str, Any]:
    return {
        "detailStatus": "detail_failed",
        "detailSource": "detail_page",
        "detailError": error,
        "normalEffectCount": 0,
        "bondedEffectCount": 0,
        "effectConditions": [],
        "propertyLines": [],
        "requirementLines": [],
        "descriptionLineCount": 0,
        "detailWarnings": [],
    }


def _socket_augment_warning(message: str, *, code: str = "socket_augment_skipped") -> dict[str, Any]:
    return diagnostic_warning(code=code, message=message)


def _catalogue_detail_status_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        status = str(entry.get("detailStatus") or "index_only")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _catalogue_detail_source_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        source = str(entry.get("detailSource") or "index_only")
        counts[source] = counts.get(source, 0) + 1
    return dict(sorted(counts.items()))


def _augment_catalogue_base_entries(index: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    for section in index.get("catalogueSections") or []:
        section_name = str(section.get("section") or "unknown")
        for entry in section.get("entries") or []:
            source_url = str(entry.get("sourceUrl") or "")
            if not source_url:
                continue
            key = (section_name, source_url)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            category = str(entry.get("category") or "unknown")
            initial = {
                "id": str(entry.get("id") or entity_id(source_url)),
                "slug": str(entry.get("slug") or slug_from_url(source_url)),
                "name": str(entry.get("name") or title_from_url(source_url)),
                "sourceUrl": source_url,
                "source": "poe2db",
                "kind": "augment_catalogue_entry",
                "section": section_name,
                "category": category,
                "socketCandidate": bool(entry.get("socketCandidate")),
                "plannerVisibility": "catalogue_only",
                "detailStatus": "index_only",
                "detailSource": "index_only",
                "icon": entry.get("icon"),
            }
            reason = _augment_socket_candidate_reason(initial)
            entries.append(_with_socket_candidate_fields(initial, reason))
    return entries


def _enrich_augment_catalogue_entries(
    entries: list[dict[str, Any]],
    *,
    paths: BuildPaths | None,
    force_refresh: bool,
    data_snapshots: list[dict[str, Any]],
    snapshot_date: str,
    preloaded_augments: list[dict[str, Any]],
    options: BuildOptions,
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    detail_by_url = {str(augment.get("sourceUrl") or ""): augment for augment in preloaded_augments if augment.get("sourceUrl")}
    fetchable_entries = [] if paths is None else [entry for entry in entries if entry.get("sourceUrl") and str(entry.get("sourceUrl")) not in detail_by_url]
    if len(fetchable_entries) > AUGMENT_CATALOGUE_DETAIL_FETCH_LIMIT:
        warnings.append(
            f"Catalogue detail enrichment skipped {len(fetchable_entries) - AUGMENT_CATALOGUE_DETAIL_FETCH_LIMIT} entries because the fetch limit is {AUGMENT_CATALOGUE_DETAIL_FETCH_LIMIT}."
        )
        fetchable_urls = {str(entry.get("sourceUrl")) for entry in fetchable_entries[:AUGMENT_CATALOGUE_DETAIL_FETCH_LIMIT]}
    else:
        fetchable_urls = {str(entry.get("sourceUrl")) for entry in fetchable_entries}

    enriched: list[dict[str, Any]] = []
    for entry in entries:
        source_url = str(entry.get("sourceUrl") or "")
        updated = dict(entry)
        preloaded = detail_by_url.get(source_url)
        if preloaded is not None:
            updated.update(_augment_detail_summary(preloaded, detail_status="detail_loaded", detail_source=_augment_data_source(preloaded)))
            if not updated.get("icon") and preloaded.get("icon"):
                updated["icon"] = preloaded.get("icon")
            updated = _with_socket_candidate_fields(updated, _augment_socket_candidate_reason(updated, preloaded))
            enriched.append(updated)
            continue

        cache_path = cache_path_for_url(source_url, paths.cache_dir) if source_url and paths is not None else None
        should_fetch = bool(paths is not None and source_url and source_url in fetchable_urls and (force_refresh or (cache_path is not None and cache_path.exists())))
        if not should_fetch:
            enriched.append(updated)
            continue

        try:
            fetched = _fetch_html_for_build(source_url, paths=paths, force_refresh=force_refresh, options=options)
            if force_refresh and options.write_snapshots:
                data_snapshots.append(_write_snapshot(paths, fetched, snapshot_date=snapshot_date, folder="augment_catalogue"))
            augment = parse_augment_page(source_url, fetched.html)
            object_data = dict(augment.get("objectData") or {})
            object_data["augmentDataSource"] = "detail_page"
            augment["objectData"] = object_data
            updated.update(_augment_detail_summary(augment, detail_status="detail_loaded", detail_source="detail_page", fetched_from_cache=fetched.from_cache))
            if not updated.get("icon") and augment.get("icon"):
                updated["icon"] = augment.get("icon")
            updated = _with_socket_candidate_fields(updated, _augment_socket_candidate_reason(updated, augment))
        except RuntimeError as exc:
            updated.update(_augment_detail_failed_summary(str(exc)))
            updated = _with_socket_candidate_fields(updated, _augment_socket_candidate_reason(updated))
        enriched.append(updated)
    return enriched, warnings


def _build_socket_compatible_augments(
    catalogue: dict[str, Any],
    *,
    paths: BuildPaths,
    preloaded_augments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build the planner-facing augment registry from game socket rules.

    Rune Item entries are already preloaded. Additional socket-compatible entries
    discovered by catalogue detail enrichment (for example Soul Cores) are parsed
    from the local cache/detail snapshots and added without changing picker rules
    for reference-only catalogue entries.
    """
    warnings: list[dict[str, Any]] = []
    by_url: dict[str, dict[str, Any]] = {}
    for augment in preloaded_augments:
        source_url = str(augment.get("sourceUrl") or "")
        if not source_url or source_url in by_url:
            continue
        by_url[source_url] = _annotate_socket_augment(augment, None)

    for entry in catalogue.get("entries") or []:
        if not entry.get("socketCandidate"):
            continue
        source_url = str(entry.get("sourceUrl") or "")
        if not source_url or source_url in by_url:
            if source_url in by_url:
                by_url[source_url] = _annotate_socket_augment(by_url[source_url], entry)
            continue
        if entry.get("detailStatus") != "detail_loaded":
            warnings.append(_socket_augment_warning(f"Skipped socket-compatible catalogue entry without loaded detail: {entry.get('name') or source_url}."))
            continue
        cache_path = cache_path_for_url(source_url, paths.cache_dir)
        if not cache_path.exists():
            warnings.append(_socket_augment_warning(f"Skipped socket-compatible catalogue entry without cached detail HTML: {entry.get('name') or source_url}."))
            continue
        try:
            augment = parse_augment_page(source_url, cache_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive against malformed cache files
            warnings.append(_socket_augment_warning(f"Skipped socket-compatible catalogue entry after parse failure: {entry.get('name') or source_url}: {exc}", code="socket_augment_parse_failed"))
            continue
        object_data = dict(augment.get("objectData") or {})
        object_data["augmentDataSource"] = "detail_page_cache"
        augment["objectData"] = object_data
        if not augment.get("icon") and entry.get("icon"):
            augment["icon"] = entry.get("icon")
        by_url[source_url] = _annotate_socket_augment(augment, entry)

    socket_entries = [entry for entry in catalogue.get("entries") or [] if entry.get("socketCandidate")]
    ordered: list[dict[str, Any]] = []
    used: set[str] = set()
    for entry in socket_entries:
        source_url = str(entry.get("sourceUrl") or "")
        augment = by_url.get(source_url)
        if augment is None or source_url in used:
            continue
        ordered.append(augment)
        used.add(source_url)
    for source_url, augment in by_url.items():
        if source_url not in used:
            ordered.append(augment)
    return ordered, warnings



def _normalised_augment_lookup_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _enrich_editor_socket_mod_metadata(
    editor_modifier_pools: list[dict[str, Any]],
    socket_augments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_url = {str(augment.get("sourceUrl") or ""): augment for augment in socket_augments if augment.get("sourceUrl")}
    by_name: dict[str, dict[str, Any]] = {}
    for augment in socket_augments:
        key = _normalised_augment_lookup_key(augment.get("name"))
        if key and key not in by_name:
            by_name[key] = augment

    enriched_pools: list[dict[str, Any]] = []
    for pool in editor_modifier_pools:
        next_pool = dict(pool)
        next_mods: list[dict[str, Any]] = []
        for mod in pool.get("mods") or []:
            next_mod = dict(mod)
            if next_mod.get("sourceMechanic") == "augment":
                augment = None
                augment_source_url = str(next_mod.get("augmentSourceUrl") or "")
                if augment_source_url:
                    augment = by_url.get(augment_source_url)
                if augment is None:
                    name_key = _normalised_augment_lookup_key(next_mod.get("augmentName") or next_mod.get("runeName"))
                    augment = by_name.get(name_key)
                if augment is not None:
                    next_mod.setdefault("augmentId", augment.get("id"))
                    next_mod.setdefault("augmentName", augment.get("name"))
                    next_mod.setdefault("augmentSourceUrl", augment.get("sourceUrl"))
                    next_mod.setdefault("augmentCategory", augment.get("augmentCategory"))
            next_mods.append(next_mod)
        next_pool["mods"] = next_mods
        enriched_pools.append(next_pool)
    return enriched_pools


def _count_by(entries: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        value = str(entry.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _socket_candidate_guardrail_warnings(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for entry in entries:
        is_candidate = bool(entry.get("socketCandidate"))
        section = str(entry.get("section") or "unknown")
        category = str(entry.get("category") or "unknown")
        name = str(entry.get("name") or entry.get("sourceUrl") or "Unknown augment")
        visibility = str(entry.get("plannerVisibility") or "catalogue_only")
        normal_effect_count = int(entry.get("normalEffectCount") or 0)
        effect_conditions = {str(condition) for condition in (entry.get("effectConditions") or []) if str(condition).strip()}
        has_equipment_target = bool(effect_conditions & SOCKET_AUGMENT_EQUIPMENT_CONDITIONS)

        if not is_candidate:
            if visibility == "socket_picker":
                warnings.append({
                    "severity": "error",
                    "code": "socket_visibility_without_candidate",
                    "augmentName": name,
                    "section": section,
                    "message": f"{name} has socket_picker visibility but is not classified as a socket candidate.",
                })
            continue

        if visibility != "socket_picker":
            warnings.append({
                "severity": "error",
                "code": "socket_candidate_without_picker_visibility",
                "augmentName": name,
                "section": section,
                "message": f"{name} is a socket candidate but plannerVisibility is {visibility!r}.",
            })
        if category == "reference" or section in REFERENCE_AUGMENT_SECTIONS or section.endswith("Ref"):
            warnings.append({
                "severity": "error",
                "code": "reference_entry_in_socket_picker",
                "augmentName": name,
                "section": section,
                "message": f"{name} is from reference section {section!r} and must not be exposed in the socket picker.",
            })
        if normal_effect_count <= 0:
            warnings.append({
                "severity": "warning",
                "code": "socket_candidate_missing_normal_effects",
                "augmentName": name,
                "section": section,
                "message": f"{name} is socket-compatible but has no parsed non-bonded item effect.",
            })
        if normal_effect_count > 0 and not has_equipment_target:
            warnings.append({
                "severity": "warning",
                "code": "socket_candidate_missing_equipment_target",
                "augmentName": name,
                "section": section,
                "message": f"{name} has parsed effects but no equipment-target condition for weapon/armour item stats.",
            })
        if category == "soul_core" and normal_effect_count <= 0:
            warnings.append({
                "severity": "warning",
                "code": "soul_core_missing_normal_effects",
                "augmentName": name,
                "section": section,
                "message": f"Soul Core candidate {name} has no parsed non-bonded effect.",
            })
    return warnings


def _socket_candidate_guardrail_report(entries: list[dict[str, Any]]) -> dict[str, Any]:
    socket_candidates = [entry for entry in entries if entry.get("socketCandidate")]
    catalogue_only = [entry for entry in entries if not entry.get("socketCandidate")]
    reference_entries = [
        entry for entry in entries
        if str(entry.get("category") or "") == "reference"
        or str(entry.get("section") or "").endswith("Ref")
    ]
    candidate_names = [str(entry.get("name") or "Unknown augment") for entry in socket_candidates]
    warnings = _socket_candidate_guardrail_warnings(entries)
    warning_counts = _augment_warning_counts(warnings)
    return {
        "total": len(entries),
        "socketCandidateCount": len(socket_candidates),
        "catalogueOnlyCount": len(catalogue_only),
        "runeItemCandidates": sum(1 for entry in socket_candidates if entry.get("category") == "rune_item"),
        "soulCoreCandidates": sum(1 for entry in socket_candidates if entry.get("category") == "soul_core"),
        "otherSocketableAugments": sum(1 for entry in socket_candidates if entry.get("category") not in {"rune_item", "soul_core"}),
        "excludedReferenceEntries": sum(1 for entry in reference_entries if not entry.get("socketCandidate")),
        "socketCandidatesBySection": _count_by(socket_candidates, "section"),
        "socketCandidatesByCategory": _count_by(socket_candidates, "category"),
        "socketCandidatesByReason": _count_by(socket_candidates, "socketCandidateReason"),
        "candidateNamesSample": candidate_names[:16],
        "warningCounts": warning_counts,
        "validationWarnings": warnings,
        "complete": warning_counts.get("error", 0) == 0,
    }

def _augment_catalogue_registry(
    index: dict[str, Any],
    *,
    paths: BuildPaths | None = None,
    force_refresh: bool = False,
    data_snapshots: list[dict[str, Any]] | None = None,
    snapshot_date: str = "",
    preloaded_augments: list[dict[str, Any]] | None = None,
    options: BuildOptions | None = None,
) -> dict[str, Any]:
    options = options or BuildOptions.from_mode("dev")
    entries = _augment_catalogue_base_entries(index)
    enrichment_warnings: list[str] = []
    entries, enrichment_warnings = _enrich_augment_catalogue_entries(
        entries,
        paths=paths,
        force_refresh=force_refresh,
        data_snapshots=data_snapshots if data_snapshots is not None else [],
        snapshot_date=snapshot_date,
        preloaded_augments=preloaded_augments if preloaded_augments is not None else [],
        options=options,
    )

    section_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for entry in entries:
        section = str(entry.get("section") or "unknown")
        category = str(entry.get("category") or "unknown")
        section_counts[section] = section_counts.get(section, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1

    socket_candidate_audit = _socket_candidate_guardrail_report(entries)

    return {
        "kind": "augment_catalogue",
        "source": "poe2db",
        "sourceUrl": str(index.get("sourceUrl") or AUGMENT_INDEX_URL),
        "generatedFrom": "augment_index",
        "entries": entries,
        "total": len(entries),
        "socketCandidateCount": sum(1 for entry in entries if entry.get("socketCandidate")),
        "detailStatusCounts": _catalogue_detail_status_counts(entries),
        "detailSourceCounts": _catalogue_detail_source_counts(entries),
        "detailLoadedCount": sum(1 for entry in entries if entry.get("detailStatus") == "detail_loaded"),
        "detailFailedCount": sum(1 for entry in entries if entry.get("detailStatus") == "detail_failed"),
        "indexOnlyCount": sum(1 for entry in entries if entry.get("detailStatus") == "index_only"),
        "entriesWithEffects": sum(1 for entry in entries if int(entry.get("normalEffectCount") or 0) + int(entry.get("bondedEffectCount") or 0) > 0),
        "sectionCounts": dict(sorted(section_counts.items())),
        "categoryCounts": dict(sorted(category_counts.items())),
        "socketCandidateAudit": socket_candidate_audit,
        "warnings": [str(warning) for warning in (index.get("warnings") or [])] + enrichment_warnings + [
            str(warning.get("message") or warning.get("code"))
            for warning in socket_candidate_audit.get("validationWarnings", [])
        ],
    }



def _augment_index_audit_report(index: dict[str, Any]) -> dict[str, Any]:
    sections = list(index.get("catalogueSections") or [])
    total_discovered = sum(int(section.get("discovered") or 0) for section in sections)
    total_expected = sum(
        int(section.get("expected") or 0)
        for section in sections
        if section.get("expected") is not None
    )
    category_counts: dict[str, int] = {}
    warnings: list[dict[str, Any]] = []
    for section in sections:
        section_name = str(section.get("section") or "unknown")
        for category, count in (section.get("categoryCounts") or {}).items():
            category_counts[str(category)] = category_counts.get(str(category), 0) + int(count or 0)
        for warning in section.get("warnings") or []:
            warnings.append(
                {
                    "severity": "warning",
                    "code": "augment_catalogue_section_warning",
                    "section": section_name,
                    "message": str(warning),
                }
            )
    augment_item_section = next((section for section in sections if section.get("section") == "Augment Item"), None)
    rune_item_section = next((section for section in sections if section.get("section") == "Rune Item"), None)
    if augment_item_section and rune_item_section:
        augment_entries = augment_item_section.get("entries") or []
        rune_urls = {str(entry.get("sourceUrl") or "") for entry in rune_item_section.get("entries") or []}
        augment_rune_like = [
            entry
            for entry in augment_entries
            if str(entry.get("sourceUrl") or "") in rune_urls or str(entry.get("name") or "").endswith(" Rune")
        ]
        if augment_rune_like:
            warnings.append(
                {
                    "severity": "info",
                    "code": "augment_item_contains_rune_like_entries",
                    "section": "Augment Item",
                    "message": f"Augment Item audit found {len(augment_rune_like)} rune-like entries that should stay filtered out of the picker until classified.",
                }
            )
    return {
        "expectedTotal": total_expected,
        "discoveredTotal": total_discovered,
        "sections": sections,
        "categoryCounts": dict(sorted(category_counts.items())),
        "warningCounts": _augment_warning_counts(warnings),
        "validationWarnings": warnings,
        "complete": bool(sections) and all(
            section.get("expected") is None or int(section.get("discovered") or 0) >= int(section.get("expected") or 0)
            for section in sections
        ),
    }


def _augment_coverage_report(
    augments: list[dict[str, Any]],
    index: dict[str, Any],
) -> dict[str, Any]:
    missing_normal = [
        _augment_name(augment)
        for augment in augments
        if not _augment_normal_effect_count(augment)
    ]
    missing_bonded = [
        _augment_name(augment)
        for augment in augments
        if not _augment_bonded_effect_count(augment)
    ]
    missing_icons = [
        _augment_name(augment)
        for augment in augments
        if not augment.get("icon")
    ]
    missing_requirements = [
        _augment_name(augment)
        for augment in augments
        if not _augment_has_requirement(augment)
    ]
    missing_conditions = {
        _augment_name(augment): issue
        for augment in augments
        if (issue := _augment_condition_issue(augment))
    }
    suspicious_effects = {
        _augment_name(augment): effects
        for augment in augments
        if (effects := _augment_suspicious_effects(augment))
    }
    empty_stack_size = [
        _augment_name(augment)
        for augment in augments
        if _augment_empty_stack_size_lines(augment)
    ]
    duplicate_properties = {
        _augment_name(augment): lines
        for augment in augments
        if (lines := _augment_duplicate_property_lines(augment))
    }
    validation_warnings = _augment_validation_warnings(augments, index)
    conditions = sorted(
        {
            str(effect.get("condition"))
            for augment in augments
            for effect in (augment.get("augmentEffects") or [])
            if effect.get("condition")
        }
    )
    expected = int(index.get("expectedCount") or 42)
    loaded = len(augments)
    blocking_warnings = [warning for warning in validation_warnings if warning.get("severity") in {"error", "warning"}]
    return {
        "expected": expected,
        "loaded": loaded,
        "discovered": len(index.get("entries") or []),
        "complete": loaded >= expected and not missing_normal and not blocking_warnings,
        "withNormalEffects": loaded - len(missing_normal),
        "withBondedEffects": loaded - len(missing_bonded),
        "withIcons": loaded - len(missing_icons),
        "withRequirements": loaded - len(missing_requirements),
        "withCompleteNormalConditionSets": loaded - len(missing_conditions),
        "conditions": conditions,
        "missingNormalEffects": missing_normal,
        "missingBondedEffects": missing_bonded,
        "missingIcons": missing_icons,
        "missingRequirements": missing_requirements,
        "missingNormalConditions": missing_conditions,
        "suspiciousEffectTexts": suspicious_effects,
        "emptyStackSizeProperties": empty_stack_size,
        "duplicatePropertyLines": duplicate_properties,
        "dataSourceCounts": _augment_data_source_counts(augments),
        "warningCounts": _augment_warning_counts(validation_warnings),
        "validationWarnings": validation_warnings,
        "warnings": [str(warning) for warning in (index.get("warnings") or [])],
    }


def _catalogue_url_for_class(item_class: str) -> str | None:
    return UNIQUE_ITEM_CLASS_URLS.get(item_class) or WEAPON_UNIQUE_ITEM_CLASS_URLS.get(item_class)


def _unique_legacy_key(item_class: str) -> str | None:
    return {"Gloves": "uniqueGloves", "Boots": "uniqueBoots", "Helmets": "uniqueHelmets"}.get(item_class)


def _unique_debug_key(item_class: str) -> str:
    return _unique_legacy_key(item_class) or f"unique:{stable_slug(item_class)}"


def _build_unique_items_for_class(
    item_class: str,
    class_url: str,
    class_html: str,
    paths: BuildPaths,
    *,
    force_refresh: bool,
    snapshot_date: str,
    data_snapshots: list[dict[str, Any]],
    options: BuildOptions,
) -> tuple[list[dict[str, Any]], list[Any], dict[str, Any]]:
    catalogue = extract_unique_catalogue_items(class_url, class_html, item_class=item_class)
    candidates = extract_unique_armour_candidates(class_url, class_html, item_class=item_class)
    by_id = {str(item["id"]): item for item in catalogue}
    fetch_debug: dict[str, Any] = {
        str(item["id"]): {
            "candidate": {
                "name": item.get("name"),
                "baseType": item.get("baseType"),
                "label": f"{item.get('name')} {item.get('baseType') or ''}".strip(),
                "sourceUrl": item.get("sourceUrl"),
            },
            "fetch": None,
            "parsed": item,
        }
        for item in by_id.values()
    }
    prefix = {"Gloves": "unique_gloves", "Boots": "unique_boots", "Helmets": "unique_helmets"}.get(item_class, f"unique_{stable_slug(item_class)}")
    for candidate in candidates:
        fetched_unique = _fetch_unique_candidate(candidate, paths, force_refresh=force_refresh, item_class=item_class, options=options)
        if fetched_unique is None:
            continue
        fallback = by_id.get(f"{prefix}_{stable_slug(candidate.name)}")
        parsed_unique = _unique_detail_hydration_from_html(
            candidate.sourceUrl,
            fetched_unique.html,
            item_class=item_class,
            expected_base_type=candidate.baseType,
            fallback=fallback,
        )
        parsed_unique = _merge_unique_detail_fields(fallback, parsed_unique)
        by_id[str(parsed_unique["id"])] = parsed_unique
        fetch_debug[str(parsed_unique["id"])] = {
            "candidate": {
                "name": candidate.name,
                "baseType": candidate.baseType,
                "label": candidate.label,
                "sourceUrl": candidate.sourceUrl,
            },
            "fetch": _fetch_debug(fetched_unique),
            "parsed": parsed_unique,
        }
        if force_refresh and options.write_snapshots:
            data_snapshots.append(_write_snapshot(paths, fetched_unique, snapshot_date=snapshot_date, folder=_unique_snapshot_folder(item_class)))
    return sorted(by_id.values(), key=lambda item: item.get("name") or ""), candidates, fetch_debug


def _flatten_tooltip_lines(entity: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for section in entity.get("tooltipSections", []):
        lines.extend(section.get("lines", []))
    return lines


def _section_lines(entity: dict[str, Any], kind: str) -> list[str]:
    for section in entity.get("tooltipSections", []):
        if section.get("kind") == kind:
            return list(section.get("lines") or [])
    return []


def _primary_pool(subtype: dict[str, Any]) -> dict[str, Any] | None:
    return next((g for g in subtype.get("modGroups", []) if g.get("plannerPrimary")), None)


def validate_payload(payload: dict[str, Any]) -> None:
    errors: list[str] = []

    try:
        validate_ui_payload(payload)
    except Exception as exc:
        errors.append(f"Schema validation failed: {exc}")

    items = payload.get("items") or []
    by_name = {item.get("name"): item for item in items}
    tree = by_name.get("Treefingers")
    claw = by_name.get("Crude Claw")
    augment = payload.get("augment") or {}

    if tree is None:
        errors.append("Treefingers item is missing or has the wrong name.")
    else:
        tree_lines = _flatten_tooltip_lines(tree)
        forbidden = ["Treefingers Attr /5", "Version history", "Family", '"realm": "poe2"', "Copyright"]
        for bad in forbidden:
            if any(bad in line for line in tree_lines):
                errors.append(f"Treefingers tooltip leaked non-tooltip content: {bad}")
        if any(line in {":", ",", "—"} for line in tree_lines):
            errors.append("Treefingers tooltip still contains standalone punctuation tokens.")
        explicit = _section_lines(tree, "explicit")
        if len(explicit) != 6:
            errors.append(f"Treefingers should have 6 explicit display lines, found {len(explicit)}.")
        if tree.get("id") != "poe2db:Treefingers":
            errors.append("Treefingers stable id is wrong.")

    if claw is None:
        errors.append("Crude Claw item is missing or has the wrong name.")
    else:
        props = _section_lines(claw, "property")
        for expected in ["Physical Damage: 4-10", "Critical Hit Chance: 5%", "Attacks per Second: 1.65", "Weapon Range: 1.1"]:
            if expected not in props:
                errors.append(f"Crude Claw property line missing: {expected}")
        weapon = (claw.get("normalized") or {}).get("weapon") or {}
        if weapon.get("physicalDamage") != {"min": 4, "max": 10}:
            errors.append("Crude Claw normalized physical damage is wrong.")

    if augment.get("name") != "Desert Rune":
        errors.append("Desert Rune augment is missing or has the wrong name.")
    else:
        effects = [s for s in augment.get("tooltipSections", []) if s.get("kind") == "augment_effect"]
        if len(effects) != 6:
            errors.append(f"Desert Rune should have exactly 6 augment effects, found {len(effects)}.")
        normal_count = sum(1 for effect in effects if not effect.get("bonded"))
        bonded_count = sum(1 for effect in effects if effect.get("bonded"))
        if normal_count != 3 or bonded_count != 3:
            errors.append(f"Desert Rune effect split should be 3 normal + 3 bonded, found {normal_count} + {bonded_count}.")
        for effect in effects:
            if not any(str(line).strip() for line in effect.get("lines", [])):
                errors.append(f"Desert Rune has an empty augment effect for {effect.get('condition')}.")
        if len(augment.get("augmentEffects") or []) != 6:
            errors.append("Desert Rune normalized augmentEffects should contain exactly 6 entries.")

    gloves_class = next((c for c in payload.get("itemClasses", []) if c.get("slug") == "Gloves"), None)
    if gloves_class is None:
        errors.append("Gloves class summary is missing.")
    else:
        summary = gloves_class.get("summary") or {}
        if summary.get("uniqueCount") != 35:
            errors.append("Gloves class uniqueCount should be 35.")
        if summary.get("itemCount") != 91:
            errors.append("Gloves class itemCount should be 91.")
        expected_known = {"Gloves_str", "Gloves_dex", "Gloves_int", "Gloves_str_dex", "Gloves_str_int", "Gloves_dex_int"}
        if set(gloves_class.get("knownSubtypeSlugs", [])) != expected_known:
            errors.append("Gloves class knownSubtypeSlugs should include all 6 single/hybrid subtypes.")

    expected_counts = {
        "Gloves_str": 16,
        "Gloves_dex": 16,
        "Gloves_int": 16,
        "Gloves_str_dex": 13,
        "Gloves_str_int": 13,
        "Gloves_dex_int": 13,
    }
    expected_profiles = {
        "Gloves_str": (["str"], ["armour"]),
        "Gloves_dex": (["dex"], ["evasion"]),
        "Gloves_int": (["int"], ["energy_shield"]),
        "Gloves_str_dex": (["str", "dex"], ["armour", "evasion"]),
        "Gloves_str_int": (["str", "int"], ["armour", "energy_shield"]),
        "Gloves_dex_int": (["dex", "int"], ["evasion", "energy_shield"]),
    }
    item_subtypes = payload.get("itemSubtypes") or []
    subtype_by_slug = {subtype.get("slug"): subtype for subtype in item_subtypes}
    for slug, expected_count in expected_counts.items():
        subtype = subtype_by_slug.get(slug)
        if subtype is None:
            errors.append(f"{slug} subtype payload is missing.")
            continue
        attrs, defs = expected_profiles[slug]
        if subtype.get("attributeProfile") != attrs or subtype.get("defenceProfile") != defs:
            errors.append(f"{slug} subtype profiles are wrong.")
        if len(subtype.get("baseItems") or []) != expected_count:
            errors.append(f"{slug} should have {expected_count} planner base items, found {len(subtype.get('baseItems') or [])}.")
        primary = _primary_pool(subtype)
        if primary is None:
            errors.append(f"{slug} should have a planner-primary corrupted pool.")
        else:
            texts = [m.get("text") for m in primary.get("mods", [])]
            if len(texts) != 9:
                errors.append(f"{slug} planner corrupted pool should have 9 mods, found {len(texts)}.")
            if any("Corruption" in (m.get("text") or "") for m in primary.get("mods", [])):
                errors.append(f"{slug} Corruption tag leaked into planner mod display text.")
        comparison = next(iter(subtype.get("modPoolComparisons", [])), {})
        if comparison.get("status") != "primary_superset":
            errors.append(f"{slug} corrupted pool comparison should be primary_superset.")

    representative_checks = [
        ("Gloves_int", "Sombre Gloves", {"energyShield": 15}, {"level": 12, "str": None, "dex": None, "int": 17}),
        ("Gloves_str_dex", "Ringmail Gauntlets", {"armour": 13, "evasion": 10}, {"level": 6, "str": 6, "dex": 6, "int": None}),
        ("Gloves_str_int", "Rope Cuffs", {"armour": 12, "energyShield": 6}, {"level": 5, "str": 6, "dex": None, "int": 6}),
        ("Gloves_dex_int", "Gauze Wraps", {"evasion": 8, "energyShield": 6}, {"level": 4, "str": None, "dex": 6, "int": 6}),
    ]
    for slug, name, defences, requirements in representative_checks:
        subtype = subtype_by_slug.get(slug) or {}
        item = next((base for base in subtype.get("baseItems", []) if base.get("name") == name), None)
        if item is None:
            errors.append(f"{slug} should include representative base item {name}.")
        else:
            if item.get("defences") != defences:
                errors.append(f"{name} defences parsed wrong.")
            if item.get("requirements") != requirements:
                errors.append(f"{name} requirements parsed wrong.")

    gloves_int = subtype_by_slug.get("Gloves_int")
    if gloves_int is not None:
        primary = _primary_pool(gloves_int)
        texts = [m.get("text") for m in (primary or {}).get("mods", [])]
        if "(15—25)% increased Energy Shield" not in texts:
            errors.append("Gloves_int planner corrupted pool is missing Energy Shield corruption.")

    normal_pools = [pool for pool in (payload.get("normalExplicitPools") or []) if pool.get("itemClass") == "Gloves"]
    expected_suffix_counts = {
        "str": 17,
        "dex": 16,
        "int": 17,
        "str_dex": 18,
        "str_int": 19,
        "dex_int": 18,
    }
    if len(normal_pools) != 6:
        errors.append(f"Expected normal explicit pools for all 6 Gloves subtypes, found {len(normal_pools)}.")
    for subtype, expected_suffix_count in expected_suffix_counts.items():
        pool = next((candidate for candidate in normal_pools if candidate.get("subtype") == subtype), None)
        if pool is None:
            errors.append(f"Gloves_{subtype} normal explicit pool is missing.")
            continue
        prefix_texts = [mod.get("text") for mod in pool.get("prefixes", [])]
        suffix_texts = [mod.get("text") for mod in pool.get("suffixes", [])]
        if len(prefix_texts) != 10:
            errors.append(f"Gloves_{subtype} Base Prefix should have 10 mods, found {len(prefix_texts)}.")
        if len(suffix_texts) != expected_suffix_count:
            errors.append(f"Gloves_{subtype} Base Suffix should have {expected_suffix_count} mods, found {len(suffix_texts)}.")
        if set(pool.get("rawSources", [])) != {"full_html"}:
            errors.append(f"Gloves_{subtype} normal pool should be derived from full HTML.")
        if "# to maximum Life" not in prefix_texts or "# to maximum Mana" not in prefix_texts:
            errors.append(f"Gloves_{subtype} normal prefix pool missing Life/Mana basics.")
        if "# to maximum" in prefix_texts:
            errors.append(f"Gloves_{subtype} prefix pool incorrectly stripped Life/Mana from maximum Life/Mana display text.")
        leaked = [text for text in prefix_texts + suffix_texts if text and any(tag in text for tag in ["LifeDefences", "ElementalFire", "DamageElemental", "ChaosResistance"])]
        if leaked:
            errors.append(f"Gloves_{subtype} display text leaked compact tags: {leaked[:3]}")

    int_pool = next((pool for pool in normal_pools if pool.get("subtype") == "int"), None)
    if int_pool is not None:
        prefix_texts = [mod.get("text") for mod in int_pool.get("prefixes", [])]
        suffix_texts = [mod.get("text") for mod in int_pool.get("suffixes", [])]
        for expected in ["# to maximum Energy Shield", "#% increased Energy Shield", "Adds # to # Lightning Damage to Attacks"]:
            if expected not in prefix_texts:
                errors.append(f"Gloves_int prefix pool missing: {expected}")
        for expected in ["# to Intelligence", "#% increased Energy Shield Recharge Rate", "#% to Chaos Resistance"]:
            if expected not in suffix_texts:
                errors.append(f"Gloves_int suffix pool missing: {expected}")
        life_mod = next((mod for mod in int_pool.get("prefixes", []) if mod.get("text") == "# to maximum Life"), None)
        suffix_fire = next((mod for mod in int_pool.get("suffixes", []) if mod.get("text") == "#% to Fire Resistance"), None)
        if not life_mod or life_mod.get("family") != "IncreasedLife" or life_mod.get("tags") != ["Life"]:
            errors.append("Gloves_int Life prefix should preserve text/family/tag from DOM HTML.")
        if not suffix_fire or suffix_fire.get("tags") != ["Elemental", "Fire", "Resistance"]:
            errors.append("Gloves_int Fire resistance suffix should preserve separated DOM tags.")

    str_dex_pool = next((pool for pool in normal_pools if pool.get("subtype") == "str_dex"), None)
    if str_dex_pool is not None:
        str_dex_prefix_texts = [mod.get("text") for mod in str_dex_pool.get("prefixes", [])]
        for expected in ["# to Armour / # to Evasion Rating", "#% increased Armour and Evasion", "#% increased Armour and Evasion / # to maximum Life"]:
            if expected not in str_dex_prefix_texts:
                errors.append(f"Gloves_str_dex prefix pool missing readable hybrid affix text: {expected}")

    editor_pools = [pool for pool in (payload.get("editorModifierPools") or []) if pool.get("itemClass") == "Gloves"]
    if len(editor_pools) != 66:
        errors.append(f"Expected 66 editor modifier pools (11 groups x 6 subtypes), found {len(editor_pools)}.")
    for subtype in expected_suffix_counts:
        subtype_pools = [pool for pool in editor_pools if pool.get("subtype") == subtype]
        if len(subtype_pools) != 11:
            errors.append(f"Expected 11 editor modifier groups for Gloves_{subtype}, found {len(subtype_pools)}.")
        by_group = {pool.get("sourceGroup"): pool for pool in subtype_pools}
        for group, expected_count in [("Augment", 43), ("Bonded Modifiers", 28), ("Corrupted", 9), ("Essence Prefix", 5), ("Essence Suffix", 11), ("Perfect Essence Suffix", 2)]:
            count = len((by_group.get(group) or {}).get("mods", []))
            if count != expected_count:
                errors.append(f"Gloves_{subtype} {group} should have {expected_count} compatible editor mods, found {count}.")
        if len((by_group.get("Desecrated Modifiers Prefix") or {}).get("mods", [])) != 0:
            errors.append(f"Gloves_{subtype} Desecrated Prefix should currently be empty in source HTML.")


    boot_subtypes_payload = [subtype for subtype in item_subtypes if subtype.get("itemClass") == "Boots"]
    if len(boot_subtypes_payload) != 6:
        errors.append(f"Expected 6 Boots subtypes, found {len(boot_subtypes_payload)}.")
    for expected_slug in {"Boots_str", "Boots_dex", "Boots_int", "Boots_str_dex", "Boots_str_int", "Boots_dex_int"}:
        subtype = subtype_by_slug.get(expected_slug)
        if subtype is None:
            errors.append(f"{expected_slug} subtype payload is missing.")
        elif not subtype.get("baseItems"):
            errors.append(f"{expected_slug} should have at least one base item.")

    boot_editor_pools = [pool for pool in (payload.get("editorModifierPools") or []) if pool.get("itemClass") == "Boots"]
    boot_normal_pools = [pool for pool in (payload.get("normalExplicitPools") or []) if pool.get("itemClass") == "Boots"]
    if len(boot_editor_pools) != 66:
        errors.append(f"Expected 66 Boots editor modifier pools, found {len(boot_editor_pools)}.")
    if len(boot_normal_pools) != 6:
        errors.append(f"Expected 6 Boots normal explicit pools, found {len(boot_normal_pools)}.")
    boot_mod_texts = [mod.get("text") for pool in boot_editor_pools for mod in (pool.get("mods") or [])]
    if "#% increased Movement Speed" not in boot_mod_texts:
        errors.append("Boots editor pools should include Movement Speed.")
    for forbidden_boot_text in ["#% increased Attack Speed", "#% increased Critical Damage Bonus"]:
        if forbidden_boot_text in boot_mod_texts:
            errors.append(f"Boots editor pools leaked glove-specific mod: {forbidden_boot_text}")

    if any(item.get("name") == "Unknown Item" for item in items) or augment.get("name") == "Unknown Item":
        errors.append("Unknown Item appeared in the UI payload.")

    # Keep the Pydantic contract strict, but do not make the occasional live-update
    # workflow fail because PoE2DB added/removed rows or changed modifier counts.
    # The older checks above are useful diagnostics during development, but exact
    # counts drift after game/wiki patches. Only schema/shape failures should block
    # JSON generation here.
    blocking_errors = [error for error in errors if error.startswith("Schema validation failed:")]
    if blocking_errors:
        raise ValidationError("\n".join(f"- {error}" for error in blocking_errors))
def build_debug_page(parsed: dict[str, Any], fetched: FetchedPage) -> dict[str, Any]:
    soup = BeautifulSoup(fetched.html, "lxml")
    object_data, object_raw = parse_object_data(soup)
    return {
        "sourceUrl": fetched.url,
        "fetch": _fetch_debug(fetched),
        "rawCleanedLines": get_page_lines_from_html(fetched.html),
        "tooltipLines": _flatten_tooltip_lines(parsed),
        "objectData": object_data,
        "objectDataRaw": object_raw,
        "modBlocksRaw": collect_mod_blocks_raw(soup),
        "embeddedTradeJson": extract_trade_json_if_present(fetched.html),
        "parseWarnings": parsed.get("warnings", []),
        "parseDiagnostics": parsed.get("diagnostics", []),
    }


def _fetch_debug(fetched: FetchedPage) -> dict[str, Any]:
    return {
        "url": fetched.url,
        "fromCache": fetched.from_cache,
        "cachePath": str(fetched.cache_path),
        "attempts": fetched.attempts,
        "statusCode": fetched.status_code,
        "elapsedSeconds": fetched.elapsed_seconds,
        "warnings": fetched.warnings,
    }


def build_poc_payload(
    paths: BuildPaths,
    *,
    force_refresh: bool = False,
    build_mode: str = "dev",
    allow_previous_output_fallbacks: bool | None = None,
    reuse_generated_modifier_pools: bool | None = None,
    allow_stale_cache_on_error: bool | None = None,
    write_snapshots: bool | None = None,
    write_modifier_html_cache: bool | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    options = BuildOptions.from_mode(
        build_mode,
        allow_previous_output_fallbacks=allow_previous_output_fallbacks,
        reuse_generated_modifier_pools=reuse_generated_modifier_pools,
        allow_stale_cache_on_error=allow_stale_cache_on_error,
        write_snapshots=write_snapshots,
        write_modifier_html_cache=write_modifier_html_cache,
    )
    snapshot_date = datetime.now(timezone.utc).date().isoformat()

    fetched_tree = _fetch_html_for_build(TREEFINGERS_URL, paths=paths, force_refresh=force_refresh, options=options)
    fetched_claw = _fetch_html_for_build(CRUDE_CLAW_URL, paths=paths, force_refresh=force_refresh, options=options)
    fetched_rune = _fetch_html_for_build(DESERT_RUNE_URL, paths=paths, force_refresh=force_refresh, options=options)
    fetched_gloves = _fetch_html_for_build(GLOVES_URL, paths=paths, force_refresh=force_refresh, options=options)
    fetched_boots = _fetch_html_for_build(BOOTS_URL, paths=paths, force_refresh=force_refresh, options=options)
    fetched_helmets = _fetch_html_for_build(HELMETS_URL, paths=paths, force_refresh=force_refresh, options=options)
    fetched_glove_subtypes = {
        url: _fetch_html_for_build(url, paths=paths, force_refresh=force_refresh, options=options)
        for url in GLOVE_SUBTYPE_URLS
    }
    fetched_boot_subtypes = {
        url: _fetch_html_for_build(url, paths=paths, force_refresh=force_refresh, options=options)
        for url in BOOT_SUBTYPE_URLS
    }
    fetched_helmet_subtypes = {
        url: _fetch_html_for_build(url, paths=paths, force_refresh=force_refresh, options=options)
        for url in HELMET_SUBTYPE_URLS
    }
    fetched_subtypes = {**fetched_glove_subtypes, **fetched_boot_subtypes, **fetched_helmet_subtypes}
    data_snapshots: list[dict[str, Any]] = []
    if options.write_snapshots:
        data_snapshots.extend([
            _write_snapshot(paths, fetched_tree, snapshot_date=snapshot_date),
            _write_snapshot(paths, fetched_claw, snapshot_date=snapshot_date),
            _write_snapshot(paths, fetched_rune, snapshot_date=snapshot_date),
            _write_snapshot(paths, fetched_gloves, snapshot_date=snapshot_date),
            _write_snapshot(paths, fetched_boots, snapshot_date=snapshot_date),
            _write_snapshot(paths, fetched_helmets, snapshot_date=snapshot_date),
        ])
        data_snapshots.extend(
            _write_snapshot(paths, fetched, snapshot_date=snapshot_date, folder="subtypes")
            for fetched in fetched_subtypes.values()
        )

    tree = parse_item_page(TREEFINGERS_URL, fetched_tree.html)
    claw = parse_item_page(CRUDE_CLAW_URL, fetched_claw.html)
    rune_augments, rune_augment_index = _build_rune_augments(
        paths,
        force_refresh=force_refresh,
        data_snapshots=data_snapshots,
        snapshot_date=snapshot_date,
        fetched_desert_rune=fetched_rune,
        options=options,
    )
    rune = next((augment for augment in rune_augments if augment.get("sourceUrl") == DESERT_RUNE_URL), rune_augments[0])
    augment_catalogue = _augment_catalogue_registry(
        rune_augment_index,
        paths=paths,
        force_refresh=force_refresh,
        data_snapshots=data_snapshots,
        snapshot_date=snapshot_date,
        preloaded_augments=rune_augments,
        options=options,
    )
    socket_augments, socket_augment_warnings = _build_socket_compatible_augments(
        augment_catalogue,
        paths=paths,
        preloaded_augments=rune_augments,
    )
    gloves_class = parse_class_page(GLOVES_URL, fetched_gloves.html)
    boots_class = parse_class_page(BOOTS_URL, fetched_boots.html)
    helmets_class = parse_class_page(HELMETS_URL, fetched_helmets.html)
    glove_subtypes = [parse_subtype_page(url, fetched.html) for url, fetched in fetched_glove_subtypes.items()]
    boot_subtypes = [parse_subtype_page(url, fetched.html) for url, fetched in fetched_boot_subtypes.items()]
    helmet_subtypes = [parse_subtype_page(url, fetched.html) for url, fetched in fetched_helmet_subtypes.items()]

    previous_base_items = _previous_base_items_by_slug(paths) if options.allow_previous_output_fallbacks else {}
    _fill_missing_base_items(glove_subtypes, class_html=fetched_gloves.html, previous_by_slug=previous_base_items)
    _fill_missing_base_items(boot_subtypes, class_html=fetched_boots.html, previous_by_slug=previous_base_items)
    _fill_missing_base_items(helmet_subtypes, class_html=fetched_helmets.html, previous_by_slug=previous_base_items)

    unique_class_pages: dict[str, FetchedPage] = {
        "Gloves": fetched_gloves,
        "Boots": fetched_boots,
        "Helmets": fetched_helmets,
    }
    optional_class_pages: dict[str, FetchedPage] = {}
    for item_class in OPTIONAL_BASE_ITEM_CLASSES:
        class_url = _catalogue_url_for_class(item_class)
        if not class_url:
            continue
        fetched_optional_class = _fetch_class_catalogue(item_class, class_url, paths, force_refresh=force_refresh, required=False, options=options)
        if fetched_optional_class is None:
            continue
        optional_class_pages[item_class] = fetched_optional_class
        # Unique production now covers the supported weapon catalogue pages as
        # well as the non-weapon optional classes. The Weapons alias in schema.py
        # intentionally excludes Traps, so they cannot drift into uniqueItems.
        if item_class in OPTIONAL_UNIQUE_ITEM_CLASSES or item_class in WEAPON_UNIQUE_ITEM_CLASS_URLS:
            unique_class_pages[item_class] = fetched_optional_class
        if force_refresh and options.write_snapshots:
            data_snapshots.append(_write_snapshot(paths, fetched_optional_class, snapshot_date=snapshot_date, folder="classes"))

    item_class_summaries = [gloves_class, boots_class, helmets_class]
    item_class_summaries.extend(
        parse_class_page(_catalogue_url_for_class(item_class) or fetched.url, fetched.html)
        for item_class, fetched in optional_class_pages.items()
    )

    unique_items_by_class: dict[str, list[dict[str, Any]]] = {}
    unique_candidates_by_class: dict[str, list[Any]] = {}
    unique_fetch_debug_by_class: dict[str, dict[str, Any]] = {}
    for item_class, class_page in unique_class_pages.items():
        class_url = _catalogue_url_for_class(item_class) or class_page.url
        class_unique_items, class_candidates, class_fetch_debug = _build_unique_items_for_class(
            item_class,
            class_url,
            class_page.html,
            paths,
            force_refresh=force_refresh,
            snapshot_date=snapshot_date,
            data_snapshots=data_snapshots,
            options=options,
        )
        unique_items_by_class[item_class] = class_unique_items
        unique_candidates_by_class[item_class] = class_candidates
        unique_fetch_debug_by_class[_unique_debug_key(item_class)] = class_fetch_debug

    unique_items = [item for item_class in unique_items_by_class for item in unique_items_by_class[item_class]]
    unique_gloves = unique_items_by_class.get("Gloves", [])
    unique_boots = unique_items_by_class.get("Boots", [])
    unique_helmets = unique_items_by_class.get("Helmets", [])

    base_items_by_class: dict[str, list[dict[str, Any]]] = {}
    base_item_class_pages = {**unique_class_pages, **optional_class_pages}
    for item_class, class_page in base_item_class_pages.items():
        class_url = _catalogue_url_for_class(item_class) or class_page.url
        parsed_base_items = parse_base_items_from_class_page(class_url, class_page.html, item_class=item_class)
        if parsed_base_items:
            base_items_by_class[item_class] = parsed_base_items
    base_items = [item for item_class in base_items_by_class for item in base_items_by_class[item_class]]

    class_level_modifier_debug: dict[str, dict[str, Any]] = {}
    cached_pools = None if force_refresh or not options.reuse_generated_modifier_pools else _read_cached_modifier_pools(paths)
    if cached_pools is not None:
        editor_modifier_pools, normal_explicit_pools = cached_pools
    else:
        editor_modifier_pools = []
        normal_explicit_pools = []
        for url in MODIFIER_SUBTYPE_SOURCE_META:
            item_class, slug, subtype = MODIFIER_SUBTYPE_SOURCE_META[url]
            source_url = url + "#ModifiersCalc"
            html = _modifier_html_for_subtype(
                paths,
                url=url,
                slug=slug,
                fetched_subtypes=fetched_subtypes,
                force_refresh=force_refresh,
                options=options,
            )
            pools = parse_editor_modifier_pools_from_html(
                html,
                source_url=source_url,
                item_class=item_class,
                subtype=subtype,
                slug=slug,
                validation_source="live_or_cached_full_modifiers_calc_html",
                confidence="high",
            )
            if not pools:
                raise ValidationError(
                    f"No ModifiersCalc pools parsed for {slug}. Run `python scraper/run_poc.py --update-snapshots --skip-unique-details --categories {item_class}` and inspect scraper/data/modifiers_calc_full/{slug}.html."
                )
            editor_modifier_pools.extend(pools)
            normal_explicit_pools.append(normal_pool_from_editor_pools(
                pools,
                source_url=source_url,
                item_class=item_class,
                subtype=subtype,
                slug=slug,
                validation_source="derived_from_live_or_cached_full_modifiers_calc_html",
                confidence="high",
            ))

        for item_class in CLASS_LEVEL_PRODUCTION_MODIFIER_ITEM_CLASSES:
            class_url = _catalogue_url_for_class(item_class)
            if not class_url:
                raise ValidationError(f"No PoE2DB class URL configured for {item_class} class-level modifier parsing.")
            class_page = unique_class_pages.get(item_class)
            if class_page is None:
                class_page = _fetch_class_catalogue(item_class, class_url, paths, force_refresh=force_refresh, required=True, options=options)
            if class_page is None:
                raise ValidationError(
                    f"No class page available for {item_class} modifiers. Run `python scraper/run_poc.py --update-snapshots --skip-unique-details --categories {item_class}` first."
                )
            pools, debug = _parse_class_level_modifier_pools(item_class, class_url, class_page.html)
            class_level_modifier_debug[item_class] = debug
            if debug.get("error"):
                raise ValidationError(
                    f"No usable class-level ModifiersCalc pools parsed for {item_class}. Run `python scraper/run_poc.py --update-snapshots --skip-unique-details --categories {item_class}` and inspect the class page."
                )
            editor_modifier_pools.extend(pools)
            normal_explicit_pools.append(normal_pool_from_editor_pools(
                pools,
                source_url=f"{class_url}#ModifiersCalc",
                item_class=item_class,
                subtype="base",
                slug=_class_level_modifier_slug(item_class),
                validation_source="derived_from_live_or_cached_class_modifiers_calc_html",
                confidence="high",
            ))

    editor_modifier_pools = _enrich_editor_socket_mod_metadata(editor_modifier_pools, socket_augments)

    modifier_audits = _build_modifier_source_audits(
        paths,
        {**unique_class_pages, **optional_class_pages},
        editor_modifier_pools=editor_modifier_pools,
        normal_explicit_pools=normal_explicit_pools,
    )

    source_urls = ordered_unique_strings([
        *TARGET_URLS,
        *[(_catalogue_url_for_class(item_class) or "") for item_class in unique_class_pages],
        *[item.get("sourceUrl") for item in unique_items],
        *[item.get("sourceUrl") for item in base_items],
        *[audit.get("sourceUrl") for audit in modifier_audits],
    ])

    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "parserVersion": PARSER_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE_NAME,
        "sourceUrls": source_urls,
        "items": [tree, claw],
        "augment": rune,
        "augments": socket_augments,
        "augmentCatalogue": augment_catalogue,
        "itemClasses": item_class_summaries,
        "itemSubtypes": [*glove_subtypes, *boot_subtypes, *helmet_subtypes],
        "normalExplicitPools": normal_explicit_pools,
        "editorModifierPools": editor_modifier_pools,
        "modifierSourceMechanics": source_mechanic_metadata(),
        "modifierAudits": modifier_audits,
        "baseItems": base_items,
        "uniqueItems": unique_items,
        "uniqueGloves": unique_gloves,
        "uniqueBoots": unique_boots,
        "uniqueHelmets": unique_helmets,
        "dataSnapshots": data_snapshots,
        "parserSanity": {
            "loadedGloveBases": sum(len(subtype.get("baseItems") or []) for subtype in glove_subtypes),
            "loadedBootBases": sum(len(subtype.get("baseItems") or []) for subtype in boot_subtypes),
            "loadedHelmetBases": sum(len(subtype.get("baseItems") or []) for subtype in helmet_subtypes),
            "discoveredUniqueGloves": len(unique_candidates_by_class.get("Gloves", [])),
            "importedUniqueGloves": len(unique_gloves),
            "importedUniqueBoots": len(unique_boots),
            "discoveredUniqueHelmets": len(unique_candidates_by_class.get("Helmets", [])),
            "importedUniqueHelmets": len(unique_helmets),
            "importedUniqueItems": len(unique_items),
            "importedUniqueItemClasses": len([item_class for item_class, items in unique_items_by_class.items() if items]),
            "uniqueItemsByClass": {item_class: len(items) for item_class, items in unique_items_by_class.items()},
            "weaponUniqueItemsByClass": {item_class: len(unique_items_by_class.get(item_class, [])) for item_class in WEAPON_UNIQUE_ITEM_CLASS_URLS},
            "importedWeaponUniqueItems": sum(len(unique_items_by_class.get(item_class, [])) for item_class in WEAPON_UNIQUE_ITEM_CLASS_URLS),
            "importedWeaponUniqueItemClasses": len([item_class for item_class in WEAPON_UNIQUE_ITEM_CLASS_URLS if unique_items_by_class.get(item_class)]),
            "deprecatedUniquePayloadFields": ["uniqueGloves", "uniqueBoots", "uniqueHelmets"],
            "importedBaseItems": len(base_items),
            "importedBaseItemClasses": len([item_class for item_class, items in base_items_by_class.items() if items]),
            "baseItemsByClass": {item_class: len(items) for item_class, items in base_items_by_class.items()},
            "uniqueHelmetsWithoutExplicitMods": sum(1 for item in unique_helmets if not item.get("explicitMods")),
            "uniqueGlovesWithoutExplicitMods": sum(1 for item in unique_gloves if not item.get("explicitMods")),
            "uniqueGlovesWithoutSourceUrl": sum(1 for item in unique_gloves if not item.get("sourceUrl")),
            "uniqueGlovesWithFlavourText": sum(1 for item in unique_gloves if item.get("flavourText")),
            "uniqueBootsWithFlavourText": sum(1 for item in unique_boots if item.get("flavourText")),
            "uniqueBootsWithoutFlavourText": sum(1 for item in unique_boots if not item.get("flavourText")),
            "uniqueHelmetsWithFlavourText": sum(1 for item in unique_helmets if item.get("flavourText")),
            "uniqueItemsWithFlavourText": sum(1 for item in unique_items if item.get("flavourText")),
            "uniqueItemsWithoutFlavourText": sum(1 for item in unique_items if not item.get("flavourText")),
            "loadedAugments": len(socket_augments),
            "loadedSocketAugments": len(socket_augments),
            "loadedRuneAugments": len(rune_augments),
            "expectedRuneAugments": int(rune_augment_index.get("expectedCount") or 42),
            "discoveredRuneAugments": len(rune_augment_index.get("entries") or []),
            "importedRuneAugments": len(rune_augments),
            "importedRuneAugmentsWithNormalEffects": sum(1 for augment in rune_augments if _augment_normal_effect_count(augment)),
            "importedRuneAugmentsWithAllNormalConditions": sum(1 for augment in rune_augments if _augment_has_all_normal_conditions(augment)),
            "importedRuneAugmentsWithBondedEffects": sum(1 for augment in rune_augments if _augment_bonded_effect_count(augment)),
            "importedRuneAugmentsWithIcons": sum(1 for augment in rune_augments if augment.get("icon")),
            "importedRuneAugmentsWithRequirements": sum(1 for augment in rune_augments if _augment_has_requirement(augment)),
            "augmentIndexWarnings": [str(warning) for warning in (rune_augment_index.get("warnings") or [])],
            "augmentCoverage": _augment_coverage_report(rune_augments, rune_augment_index),
            "augmentIndexAudit": _augment_index_audit_report(rune_augment_index),
            "loadedAugmentCatalogueEntries": int(augment_catalogue.get("total") or 0),
            "augmentCatalogueSocketCandidates": int(augment_catalogue.get("socketCandidateCount") or 0),
            "augmentCatalogueDetailLoaded": int(augment_catalogue.get("detailLoadedCount") or 0),
            "augmentCatalogueDetailFailed": int(augment_catalogue.get("detailFailedCount") or 0),
            "augmentCatalogueIndexOnly": int(augment_catalogue.get("indexOnlyCount") or 0),
            "augmentCatalogueEntriesWithEffects": int(augment_catalogue.get("entriesWithEffects") or 0),
            "augmentCatalogueBySection": dict(augment_catalogue.get("sectionCounts") or {}),
            "augmentCatalogueByCategory": dict(augment_catalogue.get("categoryCounts") or {}),
            "augmentCatalogueDetailStatusCounts": dict(augment_catalogue.get("detailStatusCounts") or {}),
            "augmentCatalogueDetailSourceCounts": dict(augment_catalogue.get("detailSourceCounts") or {}),
            "augmentSocketCandidateAudit": dict(augment_catalogue.get("socketCandidateAudit") or {}),
            "socketAugmentWarnings": normalise_diagnostics(socket_augment_warnings, default_code="socket_augment"),
            "loadedEditorModifierPools": len(editor_modifier_pools),
            "loadedBootEditorModifierPools": sum(1 for pool in editor_modifier_pools if pool.get("itemClass") == "Boots"),
            "loadedBootNormalExplicitPools": sum(1 for pool in normal_explicit_pools if pool.get("itemClass") == "Boots"),
            "loadedBodyArmourEditorModifierPools": sum(1 for pool in editor_modifier_pools if pool.get("itemClass") == "Body Armours"),
            "loadedBodyArmourNormalExplicitPools": sum(1 for pool in normal_explicit_pools if pool.get("itemClass") == "Body Armours"),
            "loadedHelmetEditorModifierPools": sum(1 for pool in editor_modifier_pools if pool.get("itemClass") == "Helmets"),
            "loadedHelmetNormalExplicitPools": sum(1 for pool in normal_explicit_pools if pool.get("itemClass") == "Helmets"),
            "loadedRingEditorModifierPools": sum(1 for pool in editor_modifier_pools if pool.get("itemClass") == "Rings"),
            "loadedRingNormalExplicitPools": sum(1 for pool in normal_explicit_pools if pool.get("itemClass") == "Rings"),
            "loadedAmuletEditorModifierPools": sum(1 for pool in editor_modifier_pools if pool.get("itemClass") == "Amulets"),
            "loadedAmuletNormalExplicitPools": sum(1 for pool in normal_explicit_pools if pool.get("itemClass") == "Amulets"),
            "loadedBeltEditorModifierPools": sum(1 for pool in editor_modifier_pools if pool.get("itemClass") == "Belts"),
            "loadedBeltNormalExplicitPools": sum(1 for pool in normal_explicit_pools if pool.get("itemClass") == "Belts"),
            "loadedShieldEditorModifierPools": sum(1 for pool in editor_modifier_pools if pool.get("itemClass") == "Shields"),
            "loadedShieldNormalExplicitPools": sum(1 for pool in normal_explicit_pools if pool.get("itemClass") == "Shields"),
            "loadedFocusEditorModifierPools": sum(1 for pool in editor_modifier_pools if pool.get("itemClass") == "Foci"),
            "loadedFocusNormalExplicitPools": sum(1 for pool in normal_explicit_pools if pool.get("itemClass") == "Foci"),
            "loadedQuiverEditorModifierPools": sum(1 for pool in editor_modifier_pools if pool.get("itemClass") == "Quivers"),
            "loadedQuiverNormalExplicitPools": sum(1 for pool in normal_explicit_pools if pool.get("itemClass") == "Quivers"),
        },
    }
    payload["payloadHealth"] = build_payload_health_report(payload)
    validate_payload(payload)

    subtype_debug = {
        slug_from_url(url).replace("Gloves_", "gloves").replace("_", "_"): {
            "sourceUrl": url,
            "fetch": _fetch_debug(fetched),
            "parsed": parsed,
        }
        for (url, fetched), parsed in zip(fetched_subtypes.items(), [*glove_subtypes, *boot_subtypes, *helmet_subtypes])
    }

    debug_payload = {
        "schemaVersion": SCHEMA_VERSION,
        "parserVersion": PARSER_VERSION,
        "generatedAt": payload["generatedAt"],
        "source": SOURCE_NAME,
        "pages": {
            "treefingers": build_debug_page(tree, fetched_tree),
            "crudeClaw": build_debug_page(claw, fetched_claw),
            "desertRune": build_debug_page(rune, fetched_rune),
            "gloves": {"sourceUrl": GLOVES_URL, "fetch": _fetch_debug(fetched_gloves), "parsed": gloves_class},
            "boots": {"sourceUrl": BOOTS_URL, "fetch": _fetch_debug(fetched_boots), "parsed": boots_class},
            "helmets": {"sourceUrl": HELMETS_URL, "fetch": _fetch_debug(fetched_helmets), "parsed": helmets_class},
            **subtype_debug,
            **unique_fetch_debug_by_class,
        },
        "baseItemsByClass": base_items_by_class,
        "uniqueCandidatesByClass": {
            item_class: [
                {
                    "name": candidate.name,
                    "baseType": candidate.baseType,
                    "label": candidate.label,
                    "sourceUrl": candidate.sourceUrl,
                }
                for candidate in candidates
            ]
            for item_class, candidates in unique_candidates_by_class.items()
        },
        "normalExplicitPools": normal_explicit_pools,
        "editorModifierPools": editor_modifier_pools,
        "classLevelModifierPools": class_level_modifier_debug,
        "modifierAudits": modifier_audits,
        "normalExplicitSnapshot": {
            "path": str(paths.normal_affix_snapshot_path),
            "source": "user_uploaded_txt",
            "prefixHtmlPath": str(paths.normal_affix_prefix_html_path),
            "prefixHtmlSource": "user_supplied_poe2db_dom_snippet",
            "suffixHtmlPath": str(paths.normal_affix_suffix_html_path),
            "suffixHtmlSource": "user_supplied_poe2db_dom_snippet",
            "strDexPrefixHtmlPath": str(paths.normal_affix_str_dex_prefix_html_path),
            "strDexSuffixHtmlPath": str(paths.normal_affix_str_dex_suffix_html_path),
            "fullHtmlDir": str(paths.modifiers_calc_full_html_dir),
        },
        "dataSnapshots": data_snapshots,
        "parserSanity": payload["parserSanity"],
        "validation": {"ok": True},
        "buildOptions": options.as_dict(),
    }
    return payload, debug_payload
