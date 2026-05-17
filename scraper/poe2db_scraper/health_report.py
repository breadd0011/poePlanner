from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from .modifier_coverage_config import (
    EXCLUDED_ITEM_EDITOR_CLASSES,
    EXPERIMENTAL_MODIFIER_CLASSES,
    MODIFIER_CLASS_SUPPORT,
    REQUIRED_MODIFIER_CLASSES,
    modifier_support_for_class,
)
from .unique_gloves_parser import WEAPON_UNIQUE_CLASS_URL_SLUGS


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _unique_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = _as_list(payload.get("uniqueItems"))
    if items:
        return [item for item in items if isinstance(item, dict)]
    legacy: list[dict[str, Any]] = []
    for key in ("uniqueGloves", "uniqueBoots", "uniqueHelmets"):
        legacy.extend(item for item in _as_list(payload.get(key)) if isinstance(item, dict))
    return legacy


def _diagnostic_codes(item: dict[str, Any]) -> set[str]:
    codes: set[str] = set()
    for diagnostic in _as_list(item.get("diagnostics")):
        if isinstance(diagnostic, dict) and diagnostic.get("code"):
            codes.add(str(diagnostic["code"]))
    return codes


def _coverage(items: list[dict[str, Any]], field: str, *, unavailable_diagnostic_codes: set[str] | None = None) -> dict[str, Any]:
    unavailable_diagnostic_codes = unavailable_diagnostic_codes or set()
    with_field = [item for item in items if _is_non_empty(item.get(field))]
    unavailable = [
        str(item.get("name") or item.get("id") or "<unknown>")
        for item in items
        if not _is_non_empty(item.get(field)) and _diagnostic_codes(item).intersection(unavailable_diagnostic_codes)
    ]
    missing = [
        str(item.get("name") or item.get("id") or "<unknown>")
        for item in items
        if not _is_non_empty(item.get(field)) and not _diagnostic_codes(item).intersection(unavailable_diagnostic_codes)
    ]
    return {
        "total": len(items),
        "withValue": len(with_field),
        "missing": len(missing),
        "missingNames": missing,
        "unavailable": len(unavailable),
        "unavailableNames": unavailable,
    }


def _count_by_class(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        counts[str(item.get("itemClass") or "Unknown")] += 1
    return dict(sorted(counts.items()))


def _duplicate_names_within_class(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_class: dict[str, Counter[str]] = defaultdict(Counter)
    for item in items:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        by_class[str(item.get("itemClass") or "Unknown")][name] += 1

    duplicates: list[dict[str, Any]] = []
    for item_class in sorted(by_class):
        for name, count in sorted(by_class[item_class].items()):
            if count > 1:
                duplicates.append({"itemClass": item_class, "name": name, "count": count})
    return duplicates


def _base_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in _as_list(payload.get("baseItems")) if isinstance(item, dict)]


def _base_item_health(payload: dict[str, Any]) -> dict[str, Any]:
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in _base_items(payload):
        item_class = str(item.get("itemClass") or "Unknown")
        by_class[item_class].append(item)

    class_reports: dict[str, dict[str, Any]] = {}
    duplicate_names = _duplicate_names_within_class(_base_items(payload))

    for item_class in sorted(by_class):
        items = sorted(by_class[item_class], key=lambda item: str(item.get("name") or ""))
        class_reports[item_class] = {
            "total": len(items),
            "icon": _coverage(items, "icon"),
            "sourceUrl": _coverage(items, "sourceUrl"),
            "requirements": _coverage(items, "requirements"),
            "propertyLines": _coverage(items, "propertyLines"),
            "implicitMods": _coverage(items, "implicitMods"),
            "defences": _coverage(items, "defences"),
        }

    return {
        "total": sum(len(items) for items in by_class.values()),
        "byClass": class_reports,
        "duplicateNames": duplicate_names,
    }

def _unique_health(payload: dict[str, Any]) -> dict[str, Any]:
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in _unique_items(payload):
        item_class = str(item.get("itemClass") or "Unknown")
        by_class[item_class].append(item)

    class_reports: dict[str, dict[str, Any]] = {}
    duplicate_names: list[dict[str, Any]] = []
    global_name_counts = Counter(str(item.get("name") or "").strip() for item in _unique_items(payload) if item.get("name"))
    for name, count in global_name_counts.items():
        if count > 1:
            duplicate_names.append({"name": name, "count": count})

    for item_class in sorted(by_class):
        items = sorted(by_class[item_class], key=lambda item: str(item.get("name") or ""))
        class_reports[item_class] = {
            "total": len(items),
            "icon": _coverage(items, "icon"),
            "flavourText": _coverage(items, "flavourText", unavailable_diagnostic_codes={"UNIQUE_FLAVOUR_TEXT_NOT_PUBLISHED"}),
            "explicitMods": _coverage(items, "explicitMods"),
            "baseType": _coverage(items, "baseType"),
            "sourceUrl": _coverage(items, "sourceUrl"),
        }

    return {
        "total": sum(len(items) for items in by_class.values()),
        "byClass": class_reports,
        "duplicateNames": duplicate_names,
    }



def _weapon_unique_production_health(payload: dict[str, Any]) -> dict[str, Any]:
    """Report production readiness for the supported weapon/Talisman unique pipeline.

    Weapon classes with zero PoE2DB uniques are still reported as OK so the
    class inventory stays explicit without inventing expected items.
    """
    unique_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in _unique_items(payload):
        unique_by_class[str(item.get("itemClass") or "Unknown")].append(item)

    parser_sanity = payload.get("parserSanity") if isinstance(payload.get("parserSanity"), dict) else {}
    expected_by_class = parser_sanity.get("weaponUniqueItemsByClass") if isinstance(parser_sanity, dict) else {}
    if not isinstance(expected_by_class, dict):
        expected_by_class = {}

    by_class: dict[str, dict[str, Any]] = {}
    total_expected = 0
    total_imported = 0
    classes_with_uniques = 0
    classes_ok = 0
    missing_field_totals = {
        "icon": 0,
        "flavourText": 0,
        "explicitMods": 0,
        "baseType": 0,
        "sourceUrl": 0,
    }
    count_mismatches = 0

    for item_class, slug in WEAPON_UNIQUE_CLASS_URL_SLUGS.items():
        items = sorted(unique_by_class.get(item_class, []), key=lambda item: str(item.get("name") or ""))
        expected_total = int(expected_by_class.get(item_class, len(items)) or 0)
        total = len(items)
        icon = _coverage(items, "icon")
        flavour = _coverage(items, "flavourText", unavailable_diagnostic_codes={"UNIQUE_FLAVOUR_TEXT_NOT_PUBLISHED"})
        explicit = _coverage(items, "explicitMods")
        base_type = _coverage(items, "baseType")
        source_url = _coverage(items, "sourceUrl")
        field_reports = {
            "icon": icon,
            "flavourText": flavour,
            "explicitMods": explicit,
            "baseType": base_type,
            "sourceUrl": source_url,
        }
        missing_fields = [field for field, report in field_reports.items() if int(report.get("missing") or 0) > 0]
        for field, report in field_reports.items():
            missing_field_totals[field] += int(report.get("missing") or 0)
        count_matches = total == expected_total
        if not count_matches:
            count_mismatches += 1
        status = "ok" if count_matches and not missing_fields else ("count_mismatch" if not count_matches else "missing_fields")
        if status == "ok":
            classes_ok += 1
        if total > 0:
            classes_with_uniques += 1
        total_expected += expected_total
        total_imported += total
        by_class[item_class] = {
            "itemClass": item_class,
            "status": status,
            "sourceUrl": f"https://poe2db.tw/us/{slug}",
            "expectedTotal": expected_total,
            "total": total,
            "countMatchesParserSanity": count_matches,
            "zeroUniqueClass": expected_total == 0 and total == 0,
            "missingFields": missing_fields,
            "icon": icon,
            "flavourText": flavour,
            "explicitMods": explicit,
            "baseType": base_type,
            "sourceUrlCoverage": source_url,
        }

    status = "ok" if count_mismatches == 0 and all(value == 0 for value in missing_field_totals.values()) else "error"
    return {
        "status": status,
        "summary": {
            "weaponUniqueClasses": len(WEAPON_UNIQUE_CLASS_URL_SLUGS),
            "weaponUniqueClassesOk": classes_ok,
            "classesWithUniques": classes_with_uniques,
            "expectedUniqueItems": total_expected,
            "importedUniqueItems": total_imported,
            "countMismatches": count_mismatches,
            "missingIcon": missing_field_totals["icon"],
            "missingFlavourText": missing_field_totals["flavourText"],
            "missingExplicitMods": missing_field_totals["explicitMods"],
            "missingBaseType": missing_field_totals["baseType"],
            "missingSourceUrl": missing_field_totals["sourceUrl"],
        },
        "byClass": by_class,
    }

def _subtype_health(payload: dict[str, Any]) -> dict[str, Any]:
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    missing_base_items: list[dict[str, str]] = []
    missing_planner_primary: list[dict[str, str]] = []
    for subtype in _as_list(payload.get("itemSubtypes")):
        if not isinstance(subtype, dict):
            continue
        item_class = str(subtype.get("itemClass") or "Unknown")
        slug = str(subtype.get("slug") or subtype.get("id") or "<unknown>")
        by_class[item_class].append(subtype)
        if not _is_non_empty(subtype.get("baseItems")):
            missing_base_items.append({"itemClass": item_class, "slug": slug})
        mod_groups = _as_list(subtype.get("modGroups"))
        if not any(isinstance(group, dict) and group.get("plannerPrimary") for group in mod_groups):
            missing_planner_primary.append({"itemClass": item_class, "slug": slug})

    by_class_report: dict[str, dict[str, int]] = {}
    for item_class, subtypes in sorted(by_class.items()):
        by_class_report[item_class] = {
            "total": len(subtypes),
            "withBaseItems": sum(1 for subtype in subtypes if _is_non_empty(subtype.get("baseItems"))),
            "withPlannerPrimaryModGroup": sum(
                1
                for subtype in subtypes
                if any(isinstance(group, dict) and group.get("plannerPrimary") for group in _as_list(subtype.get("modGroups")))
            ),
        }

    return {
        "total": sum(len(items) for items in by_class.values()),
        "byClass": by_class_report,
        "missingBaseItems": missing_base_items,
        "missingPlannerPrimaryModGroups": missing_planner_primary,
    }


def _modifier_pool_health(payload: dict[str, Any]) -> dict[str, Any]:
    editor_pools = [pool for pool in _as_list(payload.get("editorModifierPools")) if isinstance(pool, dict)]
    normal_pools = [pool for pool in _as_list(payload.get("normalExplicitPools")) if isinstance(pool, dict)]

    editor_by_class: dict[str, dict[str, int]] = defaultdict(lambda: {"pools": 0, "mods": 0})
    for pool in editor_pools:
        item_class = str(pool.get("itemClass") or "Unknown")
        editor_by_class[item_class]["pools"] += 1
        editor_by_class[item_class]["mods"] += len(_as_list(pool.get("mods")))

    normal_by_class: dict[str, dict[str, int]] = defaultdict(lambda: {"pools": 0, "prefixes": 0, "suffixes": 0})
    for pool in normal_pools:
        item_class = str(pool.get("itemClass") or "Unknown")
        normal_by_class[item_class]["pools"] += 1
        normal_by_class[item_class]["prefixes"] += len(_as_list(pool.get("prefixes")))
        normal_by_class[item_class]["suffixes"] += len(_as_list(pool.get("suffixes")))

    return {
        "editor": {
            "poolCount": len(editor_pools),
            "modCount": sum(len(_as_list(pool.get("mods"))) for pool in editor_pools),
            "byClass": dict(sorted(editor_by_class.items())),
        },
        "normalExplicit": {
            "poolCount": len(normal_pools),
            "prefixCount": sum(len(_as_list(pool.get("prefixes"))) for pool in normal_pools),
            "suffixCount": sum(len(_as_list(pool.get("suffixes"))) for pool in normal_pools),
            "byClass": dict(sorted(normal_by_class.items())),
        },
    }


def _modifier_audit_by_class(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    audits: dict[str, dict[str, Any]] = {}
    for audit in _as_list(payload.get("modifierAudits")):
        if not isinstance(audit, dict):
            continue
        item_class = str(audit.get("itemClass") or "").strip()
        if item_class:
            audits[item_class] = audit
    return audits


def _normalize_defence_key(key: str) -> str | None:
    normalized = key.lower().replace(" ", "").replace("_", "").replace("-", "")
    if normalized in {"armour", "armor"}:
        return "armour"
    if normalized in {"evasion", "evasionrating"}:
        return "evasion"
    if normalized == "energyshield":
        return "energyShield"
    return None


def _base_defence_value(base: dict[str, Any], key: str) -> float:
    defences = base.get("defences") if isinstance(base.get("defences"), dict) else {}
    for raw_key, value in defences.items():
        if _normalize_defence_key(str(raw_key)) != key:
            continue
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def _infer_item_editor_subtype(base: dict[str, Any] | None, item_class: str) -> str:
    if not base:
        return "base"
    if item_class not in {"Shields", "Body Armours"}:
        return "base"
    has_armour = _base_defence_value(base, "armour") > 0
    has_evasion = _base_defence_value(base, "evasion") > 0
    has_energy_shield = _base_defence_value(base, "energyShield") > 0

    if has_armour and has_evasion:
        return "str_dex"
    if has_armour and has_energy_shield:
        return "str_int"
    if has_evasion and has_energy_shield:
        return "dex_int"
    if has_armour:
        return "str"
    if has_evasion:
        return "dex"
    if has_energy_shield:
        return "int"
    return "base"


def _pool_has_mods(pool: dict[str, Any]) -> bool:
    return len(_as_list(pool.get("mods"))) > 0


def _normal_pool_has_affixes(pool: dict[str, Any]) -> bool:
    return len(_as_list(pool.get("prefixes"))) + len(_as_list(pool.get("suffixes"))) > 0


def _item_editor_binding_health(payload: dict[str, Any]) -> dict[str, Any]:
    base_items = _base_items(payload)
    unique_items = _unique_items(payload)
    item_subtypes = [subtype for subtype in _as_list(payload.get("itemSubtypes")) if isinstance(subtype, dict)]
    editor_pools = [pool for pool in _as_list(payload.get("editorModifierPools")) if isinstance(pool, dict)]
    normal_pools = [pool for pool in _as_list(payload.get("normalExplicitPools")) if isinstance(pool, dict)]

    subtypes_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for subtype in item_subtypes:
        subtypes_by_class[str(subtype.get("itemClass") or "Unknown")].append(subtype)

    base_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for base in base_items:
        base_by_class[str(base.get("itemClass") or "Unknown")].append(base)

    unique_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unique in unique_items:
        unique_by_class[str(unique.get("itemClass") or "Unknown")].append(unique)

    editor_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pool in editor_pools:
        editor_by_class[str(pool.get("itemClass") or "Unknown")].append(pool)

    normal_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pool in normal_pools:
        normal_by_class[str(pool.get("itemClass") or "Unknown")].append(pool)

    audit_by_class = _modifier_audit_by_class(payload)
    required_classes = sorted(set(REQUIRED_MODIFIER_CLASSES))
    by_class: dict[str, dict[str, Any]] = {}
    total_options = 0
    bindable_options_total = 0
    options_with_editor = 0
    options_with_normal = 0
    untyped_special_total = 0
    missing_editor_total = 0
    missing_normal_total = 0
    missing_visible_classes = 0

    def pool_matches(pool: dict[str, Any], item_class: str, subtype_key: str, has_subtypes: bool, *, normal: bool = False) -> bool:
        if str(pool.get("itemClass") or "") != item_class:
            return False
        if normal and not _normal_pool_has_affixes(pool):
            return False
        if not normal and not _pool_has_mods(pool):
            return False
        pool_subtype = str(pool.get("subtype") or "")
        if has_subtypes:
            return pool_subtype == subtype_key
        return pool_subtype in {subtype_key, "base", ""}

    def class_has_base_pool(pools: list[dict[str, Any]], item_class: str, *, normal: bool = False) -> bool:
        return any(pool_matches(pool, item_class, "base", False, normal=normal) for pool in pools)

    def class_has_non_base_pool(pools: list[dict[str, Any]], item_class: str, *, normal: bool = False) -> bool:
        for pool in pools:
            if str(pool.get("itemClass") or "") != item_class:
                continue
            if normal and not _normal_pool_has_affixes(pool):
                continue
            if not normal and not _pool_has_mods(pool):
                continue
            if str(pool.get("subtype") or "base") not in {"base", ""}:
                return True
        return False

    def is_untyped_special_option(
        option: dict[str, Any],
        item_class: str,
        class_editor_pools: list[dict[str, Any]],
        class_normal_pools: list[dict[str, Any]],
    ) -> bool:
        # Some PoE2DB base items in defence-profile classes have no armour/evasion/ES
        # values, so the editor can only resolve them to subtype="base". PoE2DB
        # currently exposes those classes' modifier pools only by non-base defence
        # subtypes (for example str/dex/int), and there is no source-backed class
        # level pool to bind to. Do not guess a subtype; report these separately
        # instead of failing the whole binding validation.
        if str(option.get("subtype") or "base") != "base":
            return False
        has_any_non_base_pool = class_has_non_base_pool(class_editor_pools, item_class) or class_has_non_base_pool(class_normal_pools, item_class, normal=True)
        has_any_base_pool = class_has_base_pool(class_editor_pools, item_class) or class_has_base_pool(class_normal_pools, item_class, normal=True)
        return has_any_non_base_pool and not has_any_base_pool

    for item_class in required_classes:
        class_subtypes = subtypes_by_class.get(item_class, [])
        class_bases = base_by_class.get(item_class, [])
        class_uniques = unique_by_class.get(item_class, [])
        has_subtypes = bool(class_subtypes)

        subtype_map: dict[str, str] = {}
        base_options: list[dict[str, Any]] = []
        if has_subtypes:
            for subtype in class_subtypes:
                subtype_key = str(subtype.get("subtype") or "") or "base"
                for base in _as_list(subtype.get("baseItems")):
                    if not isinstance(base, dict):
                        continue
                    name = str(base.get("name") or "").strip()
                    if not name:
                        continue
                    subtype_map.setdefault(name, subtype_key)
                    base_options.append({
                        "kind": "base",
                        "name": name,
                        "baseName": name,
                        "subtype": subtype_key,
                    })
        else:
            for base in class_bases:
                name = str(base.get("name") or "").strip()
                if not name:
                    continue
                subtype_key = _infer_item_editor_subtype(base, item_class)
                subtype_map.setdefault(name, subtype_key)
                base_options.append({
                    "kind": "base",
                    "name": name,
                    "baseName": name,
                    "subtype": subtype_key,
                })

        unique_options: list[dict[str, Any]] = []
        for unique in class_uniques:
            name = str(unique.get("name") or "").strip()
            if not name:
                continue
            base_name = str(unique.get("baseType") or name)
            subtype_key = subtype_map.get(base_name)
            if subtype_key is None:
                subtype_key = str(class_subtypes[0].get("subtype") or "base") if class_subtypes else "base"
            unique_options.append({
                "kind": "unique",
                "name": name,
                "baseName": base_name,
                "subtype": subtype_key,
            })

        options = base_options + unique_options
        class_editor_pools = editor_by_class.get(item_class, [])
        class_normal_pools = normal_by_class.get(item_class, [])
        missing_editor: list[dict[str, str]] = []
        missing_normal: list[dict[str, str]] = []
        untyped_special: list[dict[str, str]] = []
        resolved_subtypes = sorted({str(option["subtype"]) for option in options})

        for option in options:
            subtype_key = str(option["subtype"] or "base")
            has_editor = any(pool_matches(pool, item_class, subtype_key, has_subtypes) for pool in class_editor_pools)
            has_normal = any(pool_matches(pool, item_class, subtype_key, has_subtypes, normal=True) for pool in class_normal_pools)
            option_summary = {key: str(option[key]) for key in ("kind", "name", "baseName", "subtype")}
            total_options += 1

            if has_editor:
                options_with_editor += 1
            if has_normal:
                options_with_normal += 1

            if has_editor and has_normal:
                bindable_options_total += 1
                continue

            if is_untyped_special_option(option, item_class, class_editor_pools, class_normal_pools):
                untyped_special.append(option_summary)
                continue

            bindable_options_total += 1
            if not has_editor:
                missing_editor.append(option_summary)
            if not has_normal:
                missing_normal.append(option_summary)

        untyped_special_total += len(untyped_special)
        missing_editor_total += len(missing_editor)
        missing_normal_total += len(missing_normal)
        audit = audit_by_class.get(item_class) or {}
        expected_options_from_audit = int(audit.get("baseItemCount") or 0) + int(audit.get("uniqueItemCount") or 0)
        has_expected_options = bool(options) or expected_options_from_audit > 0
        if not options and expected_options_from_audit > 0:
            row_status = "missing_visible_options"
            missing_visible_classes += 1
        elif not options:
            row_status = "not_visible"
        elif missing_editor or missing_normal:
            row_status = "missing_binding"
        else:
            row_status = "ok"
        by_class[item_class] = {
            "itemClass": item_class,
            "status": row_status,
            "expectedItemOptionsFromAudit": expected_options_from_audit,
            "hasExpectedItemOptions": has_expected_options,
            "baseOptions": len(base_options),
            "uniqueOptions": len(unique_options),
            "totalItemOptions": len(options),
            "bindableItemOptions": len(options) - len(untyped_special),
            "resolvedSubtypes": resolved_subtypes,
            "editorPools": sum(1 for pool in class_editor_pools if _pool_has_mods(pool)),
            "normalExplicitPools": sum(1 for pool in class_normal_pools if _normal_pool_has_affixes(pool)),
            "optionsWithEditorPools": len(options) - len(missing_editor) - len(untyped_special),
            "optionsWithNormalExplicitPools": len(options) - len(missing_normal) - len(untyped_special),
            "untypedSpecialItemOptions": len(untyped_special),
            "untypedSpecialOptions": untyped_special[:20],
            "missingEditorPoolOptions": missing_editor[:20],
            "missingNormalExplicitPoolOptions": missing_normal[:20],
        }

    excluded: dict[str, dict[str, Any]] = {}
    for item_class in EXCLUDED_ITEM_EDITOR_CLASSES:
        visible_base = len(base_by_class.get(item_class, []))
        visible_unique = len(unique_by_class.get(item_class, []))
        visible_editor_pools = sum(1 for pool in editor_by_class.get(item_class, []) if _pool_has_mods(pool))
        visible_normal_pools = sum(1 for pool in normal_by_class.get(item_class, []) if _normal_pool_has_affixes(pool))
        excluded[item_class] = {
            "itemClass": item_class,
            "status": "ok" if visible_base == visible_unique == visible_editor_pools == visible_normal_pools == 0 else "excluded_class_visible",
            "baseOptions": visible_base,
            "uniqueOptions": visible_unique,
            "editorPools": visible_editor_pools,
            "normalExplicitPools": visible_normal_pools,
        }

    excluded_visible = [row for row in excluded.values() if row["status"] != "ok"]
    status = "ok" if missing_editor_total == 0 and missing_normal_total == 0 and missing_visible_classes == 0 and not excluded_visible else "error"
    return {
        "status": status,
        "summary": {
            "requiredClasses": len(required_classes),
            "requiredClassesOk": sum(1 for row in by_class.values() if row["status"] == "ok"),
            "itemOptions": total_options,
            "bindableItemOptions": bindable_options_total,
            "optionsWithEditorPools": options_with_editor,
            "optionsWithNormalExplicitPools": options_with_normal,
            "untypedSpecialItemOptions": untyped_special_total,
            "missingEditorPoolOptions": missing_editor_total,
            "missingNormalExplicitPoolOptions": missing_normal_total,
            "missingVisibleItemClasses": missing_visible_classes,
            "excludedClassesVisible": len(excluded_visible),
        },
        "byClass": by_class,
        "excludedClasses": excluded,
    }



def _unique_editor_binding_health(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate that every visible unique item resolves to a base item and pools.

    This mirrors the Simple Item Editor's unique item path: unique.baseType is
    resolved to a visible base item in the same class, then the selected base's
    subtype is used to find editor and normal explicit modifier pools.
    """
    base_items = _base_items(payload)
    unique_items = _unique_items(payload)
    item_subtypes = [subtype for subtype in _as_list(payload.get("itemSubtypes")) if isinstance(subtype, dict)]
    editor_pools = [pool for pool in _as_list(payload.get("editorModifierPools")) if isinstance(pool, dict)]
    normal_pools = [pool for pool in _as_list(payload.get("normalExplicitPools")) if isinstance(pool, dict)]

    subtypes_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for subtype in item_subtypes:
        subtypes_by_class[str(subtype.get("itemClass") or "Unknown")].append(subtype)

    base_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for base in base_items:
        base_by_class[str(base.get("itemClass") or "Unknown")].append(base)

    unique_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unique in unique_items:
        unique_by_class[str(unique.get("itemClass") or "Unknown")].append(unique)

    editor_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pool in editor_pools:
        editor_by_class[str(pool.get("itemClass") or "Unknown")].append(pool)

    normal_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pool in normal_pools:
        normal_by_class[str(pool.get("itemClass") or "Unknown")].append(pool)

    def pool_matches(pool: dict[str, Any], item_class: str, subtype_key: str, has_subtypes: bool, *, normal: bool = False) -> bool:
        if str(pool.get("itemClass") or "") != item_class:
            return False
        if normal and not _normal_pool_has_affixes(pool):
            return False
        if not normal and not _pool_has_mods(pool):
            return False
        pool_subtype = str(pool.get("subtype") or "")
        if has_subtypes:
            return pool_subtype == subtype_key
        return pool_subtype in {subtype_key, "base", ""}

    def class_has_base_pool(pools: list[dict[str, Any]], item_class: str, *, normal: bool = False) -> bool:
        return any(pool_matches(pool, item_class, "base", False, normal=normal) for pool in pools)

    def class_has_non_base_pool(pools: list[dict[str, Any]], item_class: str, *, normal: bool = False) -> bool:
        for pool in pools:
            if str(pool.get("itemClass") or "") != item_class:
                continue
            if normal and not _normal_pool_has_affixes(pool):
                continue
            if not normal and not _pool_has_mods(pool):
                continue
            if str(pool.get("subtype") or "base") not in {"base", ""}:
                return True
        return False

    def is_untyped_special_option(
        option: dict[str, str],
        item_class: str,
        class_editor_pools: list[dict[str, Any]],
        class_normal_pools: list[dict[str, Any]],
    ) -> bool:
        if str(option.get("subtype") or "base") != "base":
            return False
        has_any_non_base_pool = class_has_non_base_pool(class_editor_pools, item_class) or class_has_non_base_pool(class_normal_pools, item_class, normal=True)
        has_any_base_pool = class_has_base_pool(class_editor_pools, item_class) or class_has_base_pool(class_normal_pools, item_class, normal=True)
        return has_any_non_base_pool and not has_any_base_pool

    visible_classes = sorted(item_class for item_class in unique_by_class if item_class not in EXCLUDED_ITEM_EDITOR_CLASSES)
    by_class: dict[str, dict[str, Any]] = {}
    total_unique_options = 0
    bindable_unique_options = 0
    options_with_base_items = 0
    options_with_editor = 0
    options_with_normal = 0
    untyped_special_total = 0
    missing_base_total = 0
    missing_editor_total = 0
    missing_normal_total = 0

    for item_class in visible_classes:
        class_subtypes = subtypes_by_class.get(item_class, [])
        class_bases = base_by_class.get(item_class, [])
        class_uniques = unique_by_class.get(item_class, [])
        has_subtypes = bool(class_subtypes)
        class_editor_pools = editor_by_class.get(item_class, [])
        class_normal_pools = normal_by_class.get(item_class, [])

        subtype_map: dict[str, str] = {}
        for subtype in class_subtypes:
            subtype_key = str(subtype.get("subtype") or "") or "base"
            for base in _as_list(subtype.get("baseItems")):
                if not isinstance(base, dict):
                    continue
                name = str(base.get("name") or "").strip()
                if name:
                    subtype_map.setdefault(name, subtype_key)
        for base in class_bases:
            name = str(base.get("name") or "").strip()
            if name:
                subtype_map.setdefault(name, _infer_item_editor_subtype(base, item_class))

        missing_base: list[dict[str, str]] = []
        missing_editor: list[dict[str, str]] = []
        missing_normal: list[dict[str, str]] = []
        untyped_special: list[dict[str, str]] = []
        resolved_subtypes: set[str] = set()

        for unique in sorted(class_uniques, key=lambda item: str(item.get("name") or "")):
            name = str(unique.get("name") or "").strip()
            if not name:
                continue
            base_name = str(unique.get("baseType") or "").strip()
            base_exists = bool(base_name and base_name in subtype_map)
            subtype_key = subtype_map.get(base_name)
            if subtype_key is None:
                subtype_key = str(class_subtypes[0].get("subtype") or "base") if class_subtypes else "base"
            resolved_subtypes.add(subtype_key)
            option_summary = {
                "kind": "unique",
                "name": name,
                "baseName": base_name or "<missing>",
                "subtype": subtype_key,
            }
            total_unique_options += 1
            if base_exists:
                options_with_base_items += 1

            has_editor = any(pool_matches(pool, item_class, subtype_key, has_subtypes) for pool in class_editor_pools)
            has_normal = any(pool_matches(pool, item_class, subtype_key, has_subtypes, normal=True) for pool in class_normal_pools)
            if has_editor:
                options_with_editor += 1
            if has_normal:
                options_with_normal += 1

            if not base_exists:
                bindable_unique_options += 1
                missing_base.append(option_summary)
                if not has_editor:
                    missing_editor.append(option_summary)
                if not has_normal:
                    missing_normal.append(option_summary)
                continue

            if has_editor and has_normal:
                bindable_unique_options += 1
                continue

            if is_untyped_special_option(option_summary, item_class, class_editor_pools, class_normal_pools):
                untyped_special.append(option_summary)
                continue

            bindable_unique_options += 1
            if not has_editor:
                missing_editor.append(option_summary)
            if not has_normal:
                missing_normal.append(option_summary)

        missing_base_total += len(missing_base)
        missing_editor_total += len(missing_editor)
        missing_normal_total += len(missing_normal)
        untyped_special_total += len(untyped_special)

        if missing_base:
            row_status = "missing_base_item"
        elif missing_editor or missing_normal:
            row_status = "missing_binding"
        else:
            row_status = "ok"
        by_class[item_class] = {
            "itemClass": item_class,
            "status": row_status,
            "uniqueOptions": len([unique for unique in class_uniques if str(unique.get("name") or "").strip()]),
            "bindableUniqueOptions": len([unique for unique in class_uniques if str(unique.get("name") or "").strip()]) - len(untyped_special),
            "optionsWithBaseItems": len([unique for unique in class_uniques if str(unique.get("baseType") or "").strip() in subtype_map]),
            "resolvedSubtypes": sorted(resolved_subtypes),
            "editorPools": sum(1 for pool in class_editor_pools if _pool_has_mods(pool)),
            "normalExplicitPools": sum(1 for pool in class_normal_pools if _normal_pool_has_affixes(pool)),
            "optionsWithEditorPools": len([unique for unique in class_uniques if str(unique.get("name") or "").strip()]) - len(missing_editor) - len(untyped_special),
            "optionsWithNormalExplicitPools": len([unique for unique in class_uniques if str(unique.get("name") or "").strip()]) - len(missing_normal) - len(untyped_special),
            "untypedSpecialUniqueOptions": len(untyped_special),
            "untypedSpecialOptions": untyped_special[:20],
            "missingBaseItemOptions": missing_base[:20],
            "missingEditorPoolOptions": missing_editor[:20],
            "missingNormalExplicitPoolOptions": missing_normal[:20],
        }

    excluded: dict[str, dict[str, Any]] = {}
    for item_class in EXCLUDED_ITEM_EDITOR_CLASSES:
        visible_unique = len(unique_by_class.get(item_class, []))
        visible_editor_pools = sum(1 for pool in editor_by_class.get(item_class, []) if _pool_has_mods(pool))
        visible_normal_pools = sum(1 for pool in normal_by_class.get(item_class, []) if _normal_pool_has_affixes(pool))
        excluded[item_class] = {
            "itemClass": item_class,
            "status": "ok" if visible_unique == visible_editor_pools == visible_normal_pools == 0 else "excluded_class_visible",
            "uniqueOptions": visible_unique,
            "editorPools": visible_editor_pools,
            "normalExplicitPools": visible_normal_pools,
        }

    excluded_visible = [row for row in excluded.values() if row["status"] != "ok"]
    status = "ok" if missing_base_total == 0 and missing_editor_total == 0 and missing_normal_total == 0 and not excluded_visible else "error"
    return {
        "status": status,
        "summary": {
            "uniqueClasses": len(visible_classes),
            "uniqueClassesOk": sum(1 for row in by_class.values() if row["status"] == "ok"),
            "uniqueOptions": total_unique_options,
            "bindableUniqueOptions": bindable_unique_options,
            "optionsWithBaseItems": options_with_base_items,
            "optionsWithEditorPools": options_with_editor,
            "optionsWithNormalExplicitPools": options_with_normal,
            "untypedSpecialUniqueOptions": untyped_special_total,
            "missingBaseItemOptions": missing_base_total,
            "missingEditorPoolOptions": missing_editor_total,
            "missingNormalExplicitPoolOptions": missing_normal_total,
            "excludedClassesVisible": len(excluded_visible),
        },
        "byClass": by_class,
        "excludedClasses": excluded,
    }

def _modifier_coverage_health(payload: dict[str, Any], modifier_pool_health: dict[str, Any]) -> dict[str, Any]:
    base_counts = _count_by_class(_base_items(payload))
    unique_counts = _count_by_class(_unique_items(payload))
    subtype_counts = _count_by_class([subtype for subtype in _as_list(payload.get("itemSubtypes")) if isinstance(subtype, dict)])
    editor_by_class = (modifier_pool_health.get("editor") or {}).get("byClass") or {}
    normal_by_class = (modifier_pool_health.get("normalExplicit") or {}).get("byClass") or {}
    audit_by_class = _modifier_audit_by_class(payload)

    observed_classes = {
        *base_counts,
        *unique_counts,
        *subtype_counts,
        *editor_by_class,
        *normal_by_class,
        *audit_by_class,
        *REQUIRED_MODIFIER_CLASSES,
        *EXPERIMENTAL_MODIFIER_CLASSES,
    }

    by_class: dict[str, dict[str, Any]] = {}
    for item_class in sorted(observed_classes):
        support = modifier_support_for_class(item_class)
        audit = dict(audit_by_class.get(item_class) or {})
        actual_editor = dict(editor_by_class.get(item_class) or {"pools": 0, "mods": 0})
        actual_normal = dict(normal_by_class.get(item_class) or {"pools": 0, "prefixes": 0, "suffixes": 0})

        audit_editor = {
            "pools": int(audit.get("editorModifierPoolCount") or 0),
            "mods": int(audit.get("editorModifierCount") or 0),
        }
        audit_normal = {
            "pools": int(audit.get("normalExplicitPoolCount") or 0),
            "prefixes": int(audit.get("normalPrefixCount") or 0),
            "suffixes": int(audit.get("normalSuffixCount") or 0),
        }

        # Required classes are judged only from production pools. Experimental
        # classes may be marked ready by audit-only parse counts, without adding
        # those pools to editorModifierPools/normalExplicitPools yet.
        editor_for_coverage = actual_editor
        normal_for_coverage = actual_normal
        coverage_count_source = "payload"
        if support.support_state == "experimental" and int(actual_editor.get("pools") or 0) == 0 and int(actual_normal.get("pools") or 0) == 0:
            editor_for_coverage = audit_editor
            normal_for_coverage = audit_normal
            coverage_count_source = "modifierAudit"

        has_editor = int(editor_for_coverage.get("pools") or 0) > 0 and int(editor_for_coverage.get("mods") or 0) > 0
        has_normal = int(normal_for_coverage.get("pools") or 0) > 0 and (int(normal_for_coverage.get("prefixes") or 0) + int(normal_for_coverage.get("suffixes") or 0)) > 0

        missing_required: list[str] = []
        if support.require_editor_pools and not has_editor:
            missing_required.append("editorModifierPools")
        if support.require_normal_explicit_pools and not has_normal:
            missing_required.append("normalExplicitPools")

        if missing_required:
            coverage_status = "missing_required_pools"
        elif support.support_state == "experimental" and has_editor and has_normal:
            coverage_status = "experimental_ready"
        elif support.support_state == "experimental":
            coverage_status = "experimental_pending"
        elif support.support_state == "unsupported" and (has_editor or has_normal):
            coverage_status = "unexpected_supported"
        elif support.support_state == "unsupported":
            coverage_status = "not_required"
        else:
            coverage_status = "ok"

        base_total = int(base_counts.get(item_class, 0))
        unique_total = int(unique_counts.get(item_class, 0))
        if audit:
            # Class-page audits are the only base/unique coverage source for
            # weapon classes until weapon base/unique catalogue ingestion is
            # promoted separately. Keep these counts visible for both required
            # supported weapons and experimental weapon-adjacent classes.
            base_total = base_total or int(audit.get("baseItemCount") or 0)
            unique_total = unique_total or int(audit.get("uniqueItemCount") or 0)

        by_class[item_class] = {
            "itemClass": item_class,
            "supportState": support.support_state,
            "coverageStatus": coverage_status,
            "status": coverage_status,
            "note": support.note,
            "requirements": {
                "editorModifierPools": support.require_editor_pools,
                "normalExplicitPools": support.require_normal_explicit_pools,
            },
            "missingRequired": missing_required,
            "baseItems": {
                "total": base_total,
                "coveredByEditorPools": base_total if has_editor else 0,
                "coveredByNormalExplicitPools": base_total if has_normal else 0,
            },
            "uniqueItems": {
                "total": unique_total,
                "coveredByEditorPools": unique_total if has_editor else 0,
                "coveredByNormalExplicitPools": unique_total if has_normal else 0,
            },
            "itemSubtypes": {"total": int(subtype_counts.get(item_class, 0))},
            "editor": editor_for_coverage,
            "normalExplicit": normal_for_coverage,
            "actualEditor": actual_editor,
            "actualNormalExplicit": actual_normal,
            "coverageCountSource": coverage_count_source,
            "sourceUrl": audit.get("sourceUrl") or "",
            "sourceUrls": list(audit.get("sourceUrls") or ([audit.get("sourceUrl")] if audit.get("sourceUrl") else [])),
            "snapshotStatus": {
                "classPage": audit.get("classSnapshotStatus") or "unknown",
                "classPagePath": audit.get("classSnapshotPath"),
                "modifiersCalc": audit.get("modifierSnapshotStatus") or "unknown",
                "modifiersCalcPath": audit.get("modifierSnapshotPath"),
                "modifiersCalcPaths": audit.get("modifierSnapshotPaths") or ([] if not audit.get("modifierSnapshotPath") else [audit.get("modifierSnapshotPath")]),
                "modifiersCalcPresent": audit.get("modifierSnapshotPresent"),
                "modifiersCalcExpected": audit.get("modifierSnapshotExpected"),
                "modifiersCalcMissingSlugs": audit.get("modifierSnapshotMissingSlugs") or [],
            } if audit else {},
            "audit": audit,
            # Compatibility aliases for scripts/show_health_report.py and any
            # older ad-hoc readers that expect flat count names.
            "editorModifierPoolCount": int(editor_for_coverage.get("pools") or 0),
            "editorModifierCount": int(editor_for_coverage.get("mods") or 0),
            "normalExplicitPoolCount": int(normal_for_coverage.get("pools") or 0),
            "normalPrefixCount": int(normal_for_coverage.get("prefixes") or 0),
            "normalSuffixCount": int(normal_for_coverage.get("suffixes") or 0),
        }

    required = [entry for entry in by_class.values() if entry["supportState"] == "required"]
    experimental = [entry for entry in by_class.values() if entry["supportState"] == "experimental"]
    return {
        "supportConfig": {
            item_class: {
                "supportState": config.support_state,
                "requireEditorModifierPools": config.require_editor_pools,
                "requireNormalExplicitPools": config.require_normal_explicit_pools,
                "note": config.note,
            }
            for item_class, config in sorted(MODIFIER_CLASS_SUPPORT.items())
        },
        "summary": {
            "requiredClasses": len(required),
            "requiredClassesOk": sum(1 for entry in required if entry["coverageStatus"] == "ok"),
            "experimentalClasses": len(experimental),
            "experimentalClassesReady": sum(1 for entry in experimental if entry["coverageStatus"] == "experimental_ready"),
            "classesWithEditorPools": sum(1 for entry in by_class.values() if int(entry["editor"].get("pools") or 0) > 0),
            "classesWithNormalExplicitPools": sum(1 for entry in by_class.values() if int(entry["normalExplicit"].get("pools") or 0) > 0),
        },
        "byClass": by_class,
    }


def _build_warnings(report: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []

    for item_class, class_report in (report.get("uniqueItems", {}).get("byClass") or {}).items():
        total = int(class_report.get("total") or 0)
        if total <= 0:
            warnings.append({
                "severity": "error",
                "code": "UNIQUE_CLASS_EMPTY",
                "message": f"No unique items were imported for {item_class}.",
                "itemClass": item_class,
            })
            continue
        for field, code in [
            ("icon", "UNIQUE_MISSING_ICON"),
            ("flavourText", "UNIQUE_MISSING_FLAVOUR_TEXT"),
            ("explicitMods", "UNIQUE_MISSING_EXPLICIT_MODS"),
            ("sourceUrl", "UNIQUE_MISSING_SOURCE_URL"),
        ]:
            coverage = class_report.get(field) or {}
            missing = int(coverage.get("missing") or 0)
            if missing:
                sample = ", ".join((coverage.get("missingNames") or [])[:5])
                suffix = f" Sample: {sample}." if sample else ""
                warnings.append({
                    "severity": "warning",
                    "code": code,
                    "message": f"{item_class}: {missing}/{total} unique items are missing {field}.{suffix}",
                    "itemClass": item_class,
                    "missing": missing,
                    "total": total,
                })

    for item_class, class_report in (report.get("baseItems", {}).get("byClass") or {}).items():
        total = int(class_report.get("total") or 0)
        if total <= 0:
            continue
        for field, code in [("icon", "BASE_ITEM_MISSING_ICON"), ("sourceUrl", "BASE_ITEM_MISSING_SOURCE_URL")]:
            coverage = class_report.get(field) or {}
            missing = int(coverage.get("missing") or 0)
            if missing:
                sample = ", ".join((coverage.get("missingNames") or [])[:5])
                suffix = f" Sample: {sample}." if sample else ""
                warnings.append({
                    "severity": "warning",
                    "code": code,
                    "message": f"{item_class}: {missing}/{total} base items are missing {field}.{suffix}",
                    "itemClass": item_class,
                    "missing": missing,
                    "total": total,
                })

    base_duplicate_names = report.get("baseItems", {}).get("duplicateNames") or []
    if base_duplicate_names:
        warnings.append({
            "severity": "warning",
            "code": "DUPLICATE_BASE_ITEM_NAMES",
            "message": f"Found {len(base_duplicate_names)} duplicate base item names.",
            "duplicates": base_duplicate_names[:20],
        })

    duplicate_names = report.get("uniqueItems", {}).get("duplicateNames") or []
    if duplicate_names:
        warnings.append({
            "severity": "warning",
            "code": "DUPLICATE_UNIQUE_NAMES",
            "message": f"Found {len(duplicate_names)} duplicate unique item names.",
            "duplicates": duplicate_names[:20],
        })

    subtype_health = report.get("itemSubtypes") or {}
    for field, code, label in [
        ("missingBaseItems", "SUBTYPE_MISSING_BASE_ITEMS", "base items"),
        ("missingPlannerPrimaryModGroups", "SUBTYPE_MISSING_PLANNER_PRIMARY_MOD_GROUP", "planner-primary mod groups"),
    ]:
        missing = subtype_health.get(field) or []
        if missing:
            warnings.append({
                "severity": "warning",
                "code": code,
                "message": f"{len(missing)} item subtypes are missing {label}.",
                "items": missing[:20],
            })

    modifier_health = report.get("modifierPools") or {}
    if int((modifier_health.get("editor") or {}).get("poolCount") or 0) == 0:
        warnings.append({
            "severity": "error",
            "code": "EDITOR_MODIFIER_POOLS_EMPTY",
            "message": "No editor modifier pools were imported.",
        })
    if int((modifier_health.get("normalExplicit") or {}).get("poolCount") or 0) == 0:
        warnings.append({
            "severity": "error",
            "code": "NORMAL_EXPLICIT_POOLS_EMPTY",
            "message": "No normal explicit pools were imported.",
        })

    weapon_unique = report.get("weaponUniqueProduction") or {}
    weapon_unique_summary = weapon_unique.get("summary") or {}
    if str(weapon_unique.get("status") or "ok") != "ok":
        warnings.append({
            "severity": "error",
            "code": "WEAPON_UNIQUE_PRODUCTION_INCOMPLETE",
            "message": "Weapon/Talisman unique production health found count mismatches or missing required detail fields.",
            "countMismatches": weapon_unique_summary.get("countMismatches", 0),
            "missingIcon": weapon_unique_summary.get("missingIcon", 0),
            "missingFlavourText": weapon_unique_summary.get("missingFlavourText", 0),
            "missingExplicitMods": weapon_unique_summary.get("missingExplicitMods", 0),
            "missingBaseType": weapon_unique_summary.get("missingBaseType", 0),
            "missingSourceUrl": weapon_unique_summary.get("missingSourceUrl", 0),
        })

    unique_binding = report.get("uniqueEditorBinding") or {}
    unique_binding_summary = unique_binding.get("summary") or {}
    if (
        int(unique_binding_summary.get("missingBaseItemOptions") or 0) > 0
        or int(unique_binding_summary.get("missingEditorPoolOptions") or 0) > 0
        or int(unique_binding_summary.get("missingNormalExplicitPoolOptions") or 0) > 0
    ):
        warnings.append({
            "severity": "error",
            "code": "UNIQUE_EDITOR_BINDING_MISSING",
            "message": (
                "Unique item editor binding validation found unique options without matching "
                "base items and/or modifier pools."
            ),
            "missingBaseItemOptions": unique_binding_summary.get("missingBaseItemOptions", 0),
            "missingEditorPoolOptions": unique_binding_summary.get("missingEditorPoolOptions", 0),
            "missingNormalExplicitPoolOptions": unique_binding_summary.get("missingNormalExplicitPoolOptions", 0),
        })

    for item_class, row in (unique_binding.get("excludedClasses") or {}).items():
        if row.get("status") == "ok":
            continue
        warnings.append({
            "severity": "error",
            "code": "UNIQUE_EDITOR_EXCLUDED_CLASS_VISIBLE",
            "message": f"{item_class}: excluded item class has visible unique items or modifier pools.",
            "itemClass": item_class,
            "uniqueOptions": row.get("uniqueOptions", 0),
            "editorPools": row.get("editorPools", 0),
            "normalExplicitPools": row.get("normalExplicitPools", 0),
        })

    for item_class, coverage in (report.get("modifierCoverage", {}).get("byClass") or {}).items():
        if coverage.get("supportState") != "required":
            continue
        missing_required = coverage.get("missingRequired") or []
        if missing_required:
            warnings.append({
                "severity": "error",
                "code": "REQUIRED_MODIFIER_CLASS_MISSING_POOLS",
                "message": f"{item_class}: required modifier support is missing {', '.join(missing_required)}.",
                "itemClass": item_class,
                "missingRequired": missing_required,
            })

    binding = report.get("itemEditorBinding") or {}
    binding_summary = binding.get("summary") or {}
    if (
        int(binding_summary.get("missingEditorPoolOptions") or 0) > 0
        or int(binding_summary.get("missingNormalExplicitPoolOptions") or 0) > 0
        or int(binding_summary.get("missingVisibleItemClasses") or 0) > 0
    ):
        warnings.append({
            "severity": "error",
            "code": "ITEM_EDITOR_BINDING_MISSING_POOLS",
            "message": (
                "Simple Item Editor binding validation found item options without matching "
                "editor and/or normal explicit modifier pools."
            ),
            "missingEditorPoolOptions": binding_summary.get("missingEditorPoolOptions", 0),
            "missingNormalExplicitPoolOptions": binding_summary.get("missingNormalExplicitPoolOptions", 0),
            "missingVisibleItemClasses": binding_summary.get("missingVisibleItemClasses", 0),
        })

    for item_class, row in (binding.get("excludedClasses") or {}).items():
        if row.get("status") == "ok":
            continue
        warnings.append({
            "severity": "error",
            "code": "ITEM_EDITOR_EXCLUDED_CLASS_VISIBLE",
            "message": f"{item_class}: excluded item class is visible in item editor data or modifier pools.",
            "itemClass": item_class,
            "baseOptions": row.get("baseOptions", 0),
            "uniqueOptions": row.get("uniqueOptions", 0),
            "editorPools": row.get("editorPools", 0),
            "normalExplicitPools": row.get("normalExplicitPools", 0),
        })

    return warnings


def build_payload_health_report(payload: dict[str, Any]) -> dict[str, Any]:
    modifier_pool_health = _modifier_pool_health(payload)
    modifier_audits = _modifier_audit_by_class(payload)
    report: dict[str, Any] = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "schemaVersion": payload.get("schemaVersion"),
        "parserVersion": payload.get("parserVersion"),
        "uniqueItems": _unique_health(payload),
        "weaponUniqueProduction": _weapon_unique_production_health(payload),
        "baseItems": _base_item_health(payload),
        "itemSubtypes": _subtype_health(payload),
        "modifierPools": modifier_pool_health,
        "modifierAudits": {
            "total": len(modifier_audits),
            "byClass": modifier_audits,
        },
        "modifierCoverage": _modifier_coverage_health(payload, modifier_pool_health),
        "itemEditorBinding": _item_editor_binding_health(payload),
        "uniqueEditorBinding": _unique_editor_binding_health(payload),
    }
    warnings = _build_warnings(report)
    report["warnings"] = warnings
    report["status"] = (
        "error"
        if any(w.get("severity") == "error" for w in warnings)
        else ("warning" if any(w.get("severity") == "warning" for w in warnings) else "ok")
    )
    return report


def print_payload_health_report(report: dict[str, Any]) -> None:
    status = str(report.get("status") or "unknown").upper()
    print(f"Payload health: {status}")

    unique_by_class = report.get("uniqueItems", {}).get("byClass") or {}
    if unique_by_class:
        print("Unique items:")
        for item_class, class_report in unique_by_class.items():
            total = int(class_report.get("total") or 0)
            icon = class_report.get("icon") or {}
            flavour = class_report.get("flavourText") or {}
            explicit = class_report.get("explicitMods") or {}
            print(
                f"- {item_class}: "
                f"{int(icon.get('withValue') or 0)}/{total} icon, "
                f"{int(flavour.get('withValue') or 0)}/{total} flavourText, "
                f"{int(explicit.get('withValue') or 0)}/{total} explicitMods"
            )

    weapon_unique = report.get("weaponUniqueProduction") or {}
    if weapon_unique:
        summary = weapon_unique.get("summary") or {}
        print(
            "Weapon unique production: "
            f"{str(weapon_unique.get('status') or 'unknown').upper()}, "
            f"{int(summary.get('importedUniqueItems') or 0)}/{int(summary.get('expectedUniqueItems') or 0)} imported, "
            f"{int(summary.get('weaponUniqueClassesOk') or 0)}/{int(summary.get('weaponUniqueClasses') or 0)} classes OK"
        )
        for item_class, row in sorted((weapon_unique.get("byClass") or {}).items()):
            total = int(row.get("total") or 0)
            expected = int(row.get("expectedTotal") or 0)
            icon = row.get("icon") or {}
            flavour = row.get("flavourText") or {}
            explicit = row.get("explicitMods") or {}
            print(
                f"- {item_class} [{row.get('status')}]: "
                f"{total}/{expected} uniques, "
                f"{int(icon.get('withValue') or 0)}/{total} icon, "
                f"{int(flavour.get('withValue') or 0)}/{total} flavourText, "
                f"{int(explicit.get('withValue') or 0)}/{total} explicitMods"
            )

    base_by_class = report.get("baseItems", {}).get("byClass") or {}
    if base_by_class:
        print("Base items:")
        for item_class, class_report in base_by_class.items():
            total = int(class_report.get("total") or 0)
            icon = class_report.get("icon") or {}
            source_url = class_report.get("sourceUrl") or {}
            print(
                f"- {item_class}: "
                f"{int(icon.get('withValue') or 0)}/{total} icon, "
                f"{int(source_url.get('withValue') or 0)}/{total} sourceUrl"
            )

    modifier = report.get("modifierPools") or {}
    editor = modifier.get("editor") or {}
    normal = modifier.get("normalExplicit") or {}
    print(
        "Modifier pools: "
        f"{int(editor.get('poolCount') or 0)} editor pools / {int(editor.get('modCount') or 0)} editor mods; "
        f"{int(normal.get('poolCount') or 0)} normal pools / "
        f"{int(normal.get('prefixCount') or 0)} prefixes / {int(normal.get('suffixCount') or 0)} suffixes"
    )

    coverage_by_class = (report.get("modifierCoverage") or {}).get("byClass") or {}
    if coverage_by_class:
        print("Modifier coverage:")
        priority = {"required": 0, "experimental": 1, "unsupported": 2}
        sorted_entries = sorted(
            coverage_by_class.items(),
            key=lambda item: (priority.get(str(item[1].get("supportState")), 9), item[0]),
        )
        visible_entries = [
            (item_class, coverage)
            for item_class, coverage in sorted_entries
            if str(coverage.get("supportState")) != "unsupported"
            or int((coverage.get("editor") or {}).get("pools") or 0) > 0
            or int((coverage.get("normalExplicit") or {}).get("pools") or 0) > 0
        ]
        for item_class, coverage in visible_entries:
            state = str(coverage.get("supportState") or "unknown")
            status_text = str(coverage.get("coverageStatus") or "unknown")
            editor_stats = coverage.get("editor") or {}
            normal_stats = coverage.get("normalExplicit") or {}
            base_total = int(((coverage.get("baseItems") or {}).get("total")) or 0)
            unique_total = int(((coverage.get("uniqueItems") or {}).get("total")) or 0)
            line = (
                f"- {item_class} [{state}/{status_text}]: "
                f"{base_total} base, {unique_total} unique, "
                f"{int(editor_stats.get('pools') or 0)} editor pools, "
                f"{int(normal_stats.get('pools') or 0)} normal pools / "
                f"{int(normal_stats.get('prefixes') or 0)} prefixes / "
                f"{int(normal_stats.get('suffixes') or 0)} suffixes"
            )
            snapshot = coverage.get("snapshotStatus") or {}
            source_urls = [str(url) for url in (coverage.get("sourceUrls") or []) if str(url).strip()]
            source_url = str(coverage.get("sourceUrl") or "")
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
                    f"; source={source_text}; "
                    f"snapshots class={snapshot.get('classPage', 'unknown')}, "
                    f"modifiers={modifiers_text}"
                )
            print(line)
        hidden_count = len(sorted_entries) - len(visible_entries)
        if hidden_count > 0:
            print(f"- ... {hidden_count} unsupported/not-required modifier coverage rows hidden")

    binding = report.get("itemEditorBinding") or {}
    if binding:
        summary = binding.get("summary") or {}
        print(
            "Item editor binding: "
            f"{str(binding.get('status') or 'unknown').upper()}, "
            f"{int(summary.get('optionsWithEditorPools') or 0)}/{int(summary.get('itemOptions') or 0)} options with editor pools, "
            f"{int(summary.get('optionsWithNormalExplicitPools') or 0)}/{int(summary.get('itemOptions') or 0)} options with normal pools"
        )
        for item_class, row in sorted((binding.get("byClass") or {}).items()):
            if row.get("status") not in {"ok", "missing_binding", "missing_visible_options"}:
                continue
            print(
                f"- {item_class} [{row.get('status')}]: "
                f"{int(row.get('totalItemOptions') or 0)} item options, "
                f"{int(row.get('editorPools') or 0)} editor pools, "
                f"{int(row.get('normalExplicitPools') or 0)} normal pools"
            )
        for item_class, row in sorted((binding.get("excludedClasses") or {}).items()):
            print(
                f"- excluded {item_class} [{row.get('status')}]: "
                f"{int(row.get('baseOptions') or 0)} base, "
                f"{int(row.get('uniqueOptions') or 0)} unique, "
                f"{int(row.get('editorPools') or 0)} editor pools"
            )

    unique_binding = report.get("uniqueEditorBinding") or {}
    if unique_binding:
        summary = unique_binding.get("summary") or {}
        bindable = int(summary.get("bindableUniqueOptions") or summary.get("uniqueOptions") or 0)
        print(
            "Unique editor binding: "
            f"{str(unique_binding.get('status') or 'unknown').upper()}, "
            f"{int(summary.get('optionsWithBaseItems') or 0)}/{int(summary.get('uniqueOptions') or 0)} base-matched, "
            f"{int(summary.get('optionsWithEditorPools') or 0)}/{bindable} bindable editor-bound, "
            f"{int(summary.get('optionsWithNormalExplicitPools') or 0)}/{bindable} bindable normal-bound"
            + (f", {int(summary.get('untypedSpecialUniqueOptions') or 0)} untyped special" if int(summary.get('untypedSpecialUniqueOptions') or 0) else "")
        )
        for item_class, row in sorted((unique_binding.get("byClass") or {}).items()):
            if row.get("status") not in {"ok", "missing_base_item", "missing_binding"}:
                continue
            print(
                f"- unique {item_class} [{row.get('status')}]: "
                f"{int(row.get('uniqueOptions') or 0)} unique options, "
                f"{int(row.get('optionsWithBaseItems') or 0)} base-matched, "
                f"{int(row.get('editorPools') or 0)} editor pools, "
                f"{int(row.get('normalExplicitPools') or 0)} normal pools"
            )
        for item_class, row in sorted((unique_binding.get("excludedClasses") or {}).items()):
            print(
                f"- excluded unique {item_class} [{row.get('status')}]: "
                f"{int(row.get('uniqueOptions') or 0)} unique, "
                f"{int(row.get('editorPools') or 0)} editor pools"
            )

    warnings = report.get("warnings") or []
    if warnings:
        print("Warnings:")
        for warning in warnings[:20]:
            print(f"- [{warning.get('severity', 'warning')}] {warning.get('code')}: {warning.get('message')}")
        if len(warnings) > 20:
            print(f"- ... {len(warnings) - 20} more warnings")
