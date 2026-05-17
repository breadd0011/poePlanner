from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .fetcher import FetchedPage, fetch_html
from urllib.parse import urlparse
from .modifier_coverage_config import (
    CLASS_LEVEL_PRODUCTION_MODIFIER_ITEM_CLASSES,
    EXPERIMENTAL_MODIFIER_CLASSES,
    modifier_support_for_class,
)
from .normal_affix_parser import parse_editor_modifier_pools_from_html
from .schema import (
    BOOTS_URL,
    BOOT_SUBTYPE_URLS,
    GLOVES_URL,
    GLOVE_SUBTYPE_URLS,
    HELMETS_URL,
    HELMET_SUBTYPE_URLS,
    SHIELD_MODIFIER_SUBTYPE_URLS,
    BODY_ARMOUR_MODIFIER_SUBTYPE_URLS,
    OPTIONAL_UNIQUE_ITEM_CLASSES,
    UNIQUE_ITEM_CLASS_URLS,
    WEAPON_UNIQUE_ITEM_CLASSES,
    WEAPON_UNIQUE_ITEM_CLASS_URLS,
    BuildPaths,
)
from .unique_gloves_parser import extract_unique_armour_candidates, stable_slug
from .text import slug_from_url


@dataclass(frozen=True)
class CategorySnapshotConfig:
    item_class: str
    class_url: str
    subtype_urls: list[str]


CATEGORY_SNAPSHOTS: dict[str, CategorySnapshotConfig] = {
    "Gloves": CategorySnapshotConfig("Gloves", GLOVES_URL, list(GLOVE_SUBTYPE_URLS)),
    "Boots": CategorySnapshotConfig("Boots", BOOTS_URL, list(BOOT_SUBTYPE_URLS)),
    "Helmets": CategorySnapshotConfig("Helmets", HELMETS_URL, list(HELMET_SUBTYPE_URLS)),
    **{
        item_class: CategorySnapshotConfig(
            item_class,
            UNIQUE_ITEM_CLASS_URLS[item_class],
            list(BODY_ARMOUR_MODIFIER_SUBTYPE_URLS) if item_class == "Body Armours" else (list(SHIELD_MODIFIER_SUBTYPE_URLS) if item_class == "Shields" else []),
        )
        for item_class in OPTIONAL_UNIQUE_ITEM_CLASSES
    },
    **{
        item_class: CategorySnapshotConfig(item_class, WEAPON_UNIQUE_ITEM_CLASS_URLS[item_class], [])
        for item_class in WEAPON_UNIQUE_ITEM_CLASSES
    },
}


def normalize_categories(raw_categories: list[str] | None) -> list[str]:
    if not raw_categories:
        return list(CATEGORY_SNAPSHOTS)
    normalized: list[str] = []
    aliases = {
        "helmet": "Helmets",
        "helmets": "Helmets",
        "glove": "Gloves",
        "gloves": "Gloves",
        "boot": "Boots",
        "boots": "Boots",
        "body armour": "Body Armours",
        "body armours": "Body Armours",
        "body armor": "Body Armours",
        "body armors": "Body Armours",
        "focus": "Foci",
        "focuses": "Foci",
        "foci": "Foci",
        "life flask": "Life Flasks",
        "life flasks": "Life Flasks",
        "mana flask": "Mana Flasks",
        "mana flasks": "Mana Flasks",
        "charm": "Charms",
        "charms": "Charms",
        "flask": "Flasks",
        "flasks": "Flasks",
        "utility": "Utility",
        "utility items": "Utility",
        "weapon": "Weapons",
        "weapons": "Weapons",
    }
    for raw in raw_categories:
        for part in str(raw).split(","):
            value = part.strip().strip('"').strip("'")
            if not value:
                continue
            canonical = aliases.get(value.lower()) or next((name for name in CATEGORY_SNAPSHOTS if name.lower() == value.lower()), None)
            if canonical == "Weapons":
                for weapon_class in WEAPON_UNIQUE_ITEM_CLASSES:
                    if weapon_class not in normalized:
                        normalized.append(weapon_class)
                continue
            if canonical == "Flasks":
                for flask_class in ("Life Flasks", "Mana Flasks"):
                    if flask_class not in normalized:
                        normalized.append(flask_class)
                continue
            if canonical == "Utility":
                for utility_class in ("Life Flasks", "Mana Flasks", "Charms"):
                    if utility_class not in normalized:
                        normalized.append(utility_class)
                continue
            if canonical is None:
                allowed = ", ".join(sorted([*CATEGORY_SNAPSHOTS, "Flasks", "Utility", "Weapons"]))
                raise ValueError(f"Unsupported category '{value}'. Supported categories: {allowed}")
            if canonical not in normalized:
                normalized.append(canonical)
    return normalized


def _poe2db_url_with_slug(original_url: str, slug: str) -> str:
    parsed = urlparse(original_url)
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return original_url.rstrip("/") + "/" + slug
    parts[-1] = slug
    return f"{parsed.scheme}://{parsed.netloc}/" + "/".join(parts)


def _unique_url_fallbacks(unique: dict[str, str] | str | Any) -> list[str]:
    if isinstance(unique, str):
        source_url = unique
        name = slug_from_url(unique).replace("_", " ")
    elif isinstance(unique, dict):
        source_url = unique.get("sourceUrl") or ""
        name = unique.get("name") or slug_from_url(source_url).replace("_", " ")
    else:
        source_url = getattr(unique, "sourceUrl", "") or ""
        name = getattr(unique, "name", "") or slug_from_url(source_url).replace("_", " ")

    def page_slug_preserve_hyphen(value: str) -> str:
        import re
        out = str(value).strip().replace("'", "")
        out = re.sub(r"\s+", "_", out)
        out = re.sub(r"[^A-Za-z0-9_-]+", "_", out)
        return re.sub(r"_+", "_", out).strip("_")

    def page_slug_underscore(value: str) -> str:
        import re
        return re.sub(r"[^A-Za-z0-9]+", "_", str(value).replace("'", "")).strip("_")

    candidates = [source_url]
    for slug in (page_slug_preserve_hyphen(name), page_slug_underscore(name)):
        if source_url and slug:
            candidates.append(_poe2db_url_with_slug(source_url, slug))

    deduped: list[str] = []
    for url in candidates:
        if url and url not in deduped:
            deduped.append(url)
    return deduped


def _snapshot_record(paths: BuildPaths, fetched: FetchedPage, *, snapshot_date: str, folder: str) -> dict[str, Any]:
    snapshot_dir = paths.snapshot_dir_for_date(snapshot_date) / folder
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    slug = stable_slug(slug_from_url(fetched.url)) or "unknown"
    path = snapshot_dir / f"{slug}.html"
    path.write_text(fetched.html, encoding="utf-8")
    return {
        "sourceUrl": fetched.url,
        "snapshotPath": str(path.relative_to(paths.project_root)),
        "cachePath": str(fetched.cache_path.relative_to(paths.project_root)),
        "fromCache": fetched.from_cache,
        "statusCode": fetched.status_code,
        "warnings": list(fetched.warnings),
    }


def update_category_snapshots(
    paths: BuildPaths,
    *,
    categories: list[str] | None = None,
    force_refresh: bool = True,
    include_unique_details: bool = True,
    verbose: bool = False,
) -> dict[str, Any]:
    """Fetch and persist the raw PoE2DB HTML needed by the planner.

    This is meant for the occasional wiki/update workflow: run it when PoE2DB
    changes, commit/review the HTML + generated JSON diff, then ship the planner
    data. Normal builds can use the checked-in snapshots and cache.
    """
    selected = normalize_categories(categories)
    snapshot_date = datetime.now(timezone.utc).date().isoformat()
    paths.modifiers_calc_full_html_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "snapshotDate": snapshot_date,
        "categories": {},
    }

    for index, category_name in enumerate(selected, start=1):
        config = CATEGORY_SNAPSHOTS[category_name]
        if verbose:
            print(f"[{index}/{len(selected)}] Refreshing {category_name} class page...")
        category_report: dict[str, Any] = {"classPage": None, "subtypes": [], "uniques": []}
        class_page = fetch_html(config.class_url, cache_dir=paths.cache_dir, force_refresh=force_refresh)
        category_report["classPage"] = _snapshot_record(paths, class_page, snapshot_date=snapshot_date, folder="classes")

        if config.item_class in (*CLASS_LEVEL_PRODUCTION_MODIFIER_ITEM_CLASSES, *EXPERIMENTAL_MODIFIER_CLASSES):
            support = modifier_support_for_class(config.item_class)
            is_required_class_level = support.support_state == "required" and support.require_editor_pools and support.require_normal_explicit_pools
            slug = stable_slug(config.item_class)
            full_html_path = paths.modifiers_calc_full_html_path(slug)
            full_html_path.parent.mkdir(parents=True, exist_ok=True)
            full_html_path.write_text(class_page.html, encoding="utf-8")
            pools = parse_editor_modifier_pools_from_html(
                class_page.html,
                source_url=f"{config.class_url}#ModifiersCalc",
                item_class=config.item_class,
                subtype="base",
                slug=slug,
                validation_source="snapshot_update_class_level_validation" if is_required_class_level else "snapshot_update_experimental_modifier_audit",
                confidence="high" if is_required_class_level else "medium",
            )
            has_prefix = any(pool.get("sourceGroup") == "Base Prefix" and pool.get("mods") for pool in pools)
            has_suffix = any(pool.get("sourceGroup") == "Base Suffix" and pool.get("mods") for pool in pools)
            if is_required_class_level:
                if len(pools) != 11:
                    raise RuntimeError(f"Expected 11 class-level ModifiersCalc groups for {config.item_class}, parsed {len(pools)}")
                if not has_prefix:
                    raise RuntimeError(f"{config.item_class} class snapshot did not produce a non-empty Base Prefix pool")
                if not has_suffix:
                    raise RuntimeError(f"{config.item_class} class snapshot did not produce a non-empty Base Suffix pool")
            category_report["classModifiers"] = {
                "supportState": support.support_state,
                "modifiersCalcFullPath": str(full_html_path.relative_to(paths.project_root)),
                "parsedEditorPoolCount": len(pools),
                "parsedModifierCount": sum(len(pool.get("mods") or []) for pool in pools),
                "basePrefixPoolPresent": has_prefix,
                "baseSuffixPoolPresent": has_suffix,
                "rawSources": sorted({str(pool.get("rawSource") or "unknown") for pool in pools}),
            }

        for subtype_url in config.subtype_urls:
            fetched = fetch_html(subtype_url, cache_dir=paths.cache_dir, force_refresh=force_refresh)
            slug = slug_from_url(subtype_url)
            if not slug:
                raise RuntimeError(f"Could not derive subtype slug from {subtype_url}")
            full_html_path = paths.modifiers_calc_full_html_path(slug)
            full_html_path.parent.mkdir(parents=True, exist_ok=True)
            full_html_path.write_text(fetched.html, encoding="utf-8")

            subtype_key = slug.replace(f"{config.item_class}_", "")
            pools = parse_editor_modifier_pools_from_html(
                fetched.html,
                source_url=f"{subtype_url}#ModifiersCalc",
                item_class=config.item_class,
                subtype=subtype_key,
                slug=slug,
                validation_source="snapshot_update_validation",
                confidence="high",
            )
            if len(pools) != 11:
                raise RuntimeError(f"Expected 11 ModifiersCalc groups for {slug}, parsed {len(pools)}")
            if not any(pool.get("sourceGroup") == "Base Prefix" and pool.get("mods") for pool in pools):
                raise RuntimeError(f"{slug} snapshot did not produce a non-empty Base Prefix pool")
            if not any(pool.get("sourceGroup") == "Base Suffix" and pool.get("mods") for pool in pools):
                raise RuntimeError(f"{slug} snapshot did not produce a non-empty Base Suffix pool")

            snapshot = _snapshot_record(paths, fetched, snapshot_date=snapshot_date, folder="subtypes")
            snapshot.update({
                "modifiersCalcFullPath": str(full_html_path.relative_to(paths.project_root)),
                "parsedEditorPoolCount": len(pools),
                "parsedModifierCount": sum(len(pool.get("mods") or []) for pool in pools),
                "rawSources": sorted({str(pool.get("rawSource") or "unknown") for pool in pools}),
            })
            category_report["subtypes"].append(snapshot)
        unique_candidates = extract_unique_armour_candidates(config.class_url, class_page.html, item_class=config.item_class)
        category_report["discoveredUniqueUrls"] = len(unique_candidates)
        if not include_unique_details:
            category_report["uniqueDetailsSkipped"] = True
            report["categories"][category_name] = category_report
            continue
        for unique_index, unique_entry in enumerate(unique_candidates, start=1):
            if verbose and (unique_index == 1 or unique_index % 10 == 0 or unique_index == len(unique_candidates)):
                print(f"    [{unique_index}/{len(unique_candidates)}] Refreshing {category_name} unique detail snapshots...")
            last_error: Exception | None = None
            fetched_unique: FetchedPage | None = None
            attempted_urls = _unique_url_fallbacks(unique_entry)
            for unique_url in attempted_urls:
                try:
                    fetched_unique = fetch_html(unique_url, cache_dir=paths.cache_dir, force_refresh=force_refresh)
                    break
                except RuntimeError as exc:
                    last_error = exc
                    continue

            if fetched_unique is None:
                category_report["uniques"].append({"sourceUrl": attempted_urls[0] if attempted_urls else "", "attemptedUrls": attempted_urls, "statusCode": None, "warnings": [f"Skipped unique detail snapshot after failed fetches: {last_error}"], "skipped": True})
                continue

            snapshot = _snapshot_record(paths, fetched_unique, snapshot_date=snapshot_date, folder=f"unique_{config.item_class.lower()}")
            if attempted_urls and fetched_unique.url != attempted_urls[0]:
                snapshot.setdefault("warnings", []).append(f"Fetched unique detail from fallback URL {fetched_unique.url}; original URL was {attempted_urls[0]}")
                snapshot["attemptedUrls"] = attempted_urls
            category_report["uniques"].append(snapshot)

        report["categories"][category_name] = category_report
    return report
