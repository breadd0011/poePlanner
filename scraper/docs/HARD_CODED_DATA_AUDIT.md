# Hardcoded data audit - PoE2DB planner/scraper

## Summary

Goal: reduce game-data drift by keeping PoE2DB-owned data parsed from PoE2DB, and keeping only planner-owned normalization/configuration in source code.

This pass focuses on the risky areas called out in the cleanup discussion:

- base item lists
- modifier text mappings
- slot/category mappings
- affix groups
- UI display labels

## Changes made in this pass

### 1. Centralized supported armour class/subtype config

Added `scraper/poe2db_scraper/armour_config.py`.

This replaces duplicated hand-written subtype metadata with generated config for the currently supported armour classes:

- Gloves
- Boots
- Helmets

Important distinction: this file does **not** define game item rows. It only defines which PoE2DB pages the current planner scope loads and how PoE2DB armour subtype slugs are structured.

The following are now derived from one place:

- class URLs
- subtype URLs
- subtype labels
- attribute profiles
- defence profiles
- subtype metadata map

Updated files:

- `scraper/poe2db_scraper/schema.py`
- `scraper/poe2db_scraper/subtype_parser.py`
- `scraper/poe2db_scraper/builder.py`

### 2. Removed frontend hardcoded item-class list as the source of truth

`SimpleItemEditor` no longer uses:

```ts
const ITEM_CLASSES = ["Gloves", "Boots", "Helmets"] as const;
```

Instead, available item classes are derived from the payload's `itemSubtypes`.

This means if the scraper emits a new supported item class later, the editor selector can see it without needing a separate UI list update.

### 3. Removed hardcoded default base item names

Removed this frontend default preference:

- Gloves -> `Moulded Mitts`
- Boots -> `Laced Boots`
- Helmets -> `Rusted Greathelm`

The editor now picks the first available base item from parsed payload data.

This prevents UI defaults from silently breaking when PoE2DB changes rows, naming, or when the planner scope expands.

### 4. Generic selected unique state naming

Renamed the internal frontend state from `uniqueGloveId` to `selectedUniqueId`.

This was not a data bug, but it was a maintainability smell after Boots/Helmets were added.

### 5. Minor duplicate cleanup

Removed a duplicate `setPickerSourcesState(["normal"])` call in `resetModifierSelection`.

## Audit findings by category

### Base item lists

Current status: mostly good.

Base item rows are parsed from PoE2DB subtype/class pages. Remaining risk is the fallback path:

- `_fill_missing_base_items` may use class-page rows or a previous generated payload when a subtype page does not expose base items.

Recommendation:

- Keep the class-page fallback.
- Add a diagnostic counter per subtype showing whether base items came from subtype page, class page, or previous snapshot.
- Avoid previous-payload fallback in CI/release builds unless explicitly requested.

### Modifier text mappings

Current status: mixed.

Good:

- Normal/editor modifier pools mostly come from PoE2DB `ModifiersCalc` HTML.
- Tag extraction and editable range extraction are parser logic, not game-data lists.

Still hardcoded / risky:

- `STATIC_VAAL_CORRUPTED_TEXTS` in `mod_pool_parser.py`
- fallback corrupted defence modifiers in `fallback_primary_corrupted_pool`
- tag token expansions in `normal_affix_parser.py`

Recommendation:

- Treat `STATIC_VAAL_CORRUPTED_TEXTS` as the next cleanup target.
- Prefer parsing the static Vaal section from PoE2DB HTML; keep a fixture-based test for shape, not exact text.
- Keep tag token maps only if they are explicitly documented as parser normalization for poor/noisy HTML extraction.

### Slot/category mappings

Current status: improved.

Supported armour class/subtype configuration is now centralized in `armour_config.py` instead of being duplicated across schema, builder, subtype parser and UI.

Remaining risk:

- `uniqueGloves`, `uniqueBoots`, `uniqueHelmets` are still separate payload fields and separate frontend props.

Recommendation:

- In a later schema version, add a generic payload shape such as:

```json
"uniqueItemsByClass": {
  "Gloves": [],
  "Boots": [],
  "Helmets": []
}
```

Then keep old fields temporarily for backwards compatibility.

### Affix groups

Current status: acceptable but needs documentation.

The source mechanics and group labels are still represented in code:

- `normal`
- `corrupted`
- `essence`
- `perfect_essence`
- `desecrated`
- `augment`
- `bonded`

These are partly planner concepts and partly PoE2DB UI group names.

Recommendation:

- Create one shared backend enum/config for source mechanics.
- Emit display labels in the payload, or emit raw PoE2DB group names and let the UI only style/order them.
- Add a parser sanity report for unknown/new PoE2DB group headings.

### UI display labels

Current status: partly hardcoded but mostly acceptable.

Hardcoded UI labels like `Normal`, `Corrupted`, `Add Explicit Mod`, `STR/DEX` are not direct game-data rows; they are UI presentation. However, subtype labels can already come from the payload and should be preferred where available.

Recommendation:

- Prefer `ItemSubtype.label` for subtype display.
- Keep button/action labels in UI code.
- Move source mechanic labels to payload or a shared planner config if they need to match PoE2DB wording exactly.

## Recommended next cleanup ticket

**Replace static Vaal/corrupted fallback texts with PoE2DB-parsed corrupted enchantment sections.**

Acceptance criteria:

1. `STATIC_VAAL_CORRUPTED_TEXTS` is removed or only used in tests/fixtures.
2. `parse_static_vaal_corrupted_reference` parses visible rows from PoE2DB HTML.
3. Fallback corrupted defence mods are derived from the actual parsed dropdown/static section, not synthesized text.
4. CI/payload contract fails if corrupted pools are empty for a supported subtype.

## Validation performed

```bash
PYTHONPATH=scraper python scraper/run_poc.py --debug --write-schema
```

Result: succeeded.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=scraper pytest -q \
  scraper/tests/test_unique_flavour_text.py \
  scraper/tests/test_unique_boot_flavour_text.py \
  scraper/tests/test_url_normalization.py \
  scraper/tests/test_payload_contract.py \
  scraper/tests/test_treefingers.py \
  scraper/tests/test_helmet_base_items.py \
  scraper/tests/test_helmet_category_config.py
```

Result: `14 passed`.

Frontend build note:

```bash
cd web && npm run build
```

Could not be validated in this container because `node_modules` is missing, so TypeScript cannot resolve `react` / `react-dom`. This is the same dependency-install limitation as before, not a scraper/runtime validation failure.

## Cleanup pass 2 update

### Completed in this pass

- Removed `STATIC_VAAL_CORRUPTED_TEXTS` from runtime scraper logic.
- Removed `fallback_primary_corrupted_pool` subtype-synthesized game-stat fallback.
- Added `parse_modifiers_calc_corrupted_modsview_json`, so planner-primary corrupted pools can come from PoE2DB's embedded `ModsView` JSON when the rendered dropdown is not present.
- Updated `parse_static_vaal_corrupted_reference` to parse the visible `#VaalOrbCorruptedEnchantment` section from PoE2DB HTML/plain-text fixtures.
- Moved normal-affix plain-text tag fallback config into `mod_tag_config.py` and documented it as parser-normalization support, not game data.
- Added payload-level `modifierSourceMechanics` metadata for source order/labels.
- Added generic flat `uniqueItems` payload field, while keeping `uniqueGloves`, `uniqueBoots`, and `uniqueHelmets` as backwards-compatible legacy fields.
- Updated the UI to consume `uniqueItems` and `modifierSourceMechanics` instead of component-local source labels/order and per-class unique props.

### Still intentionally left

- `uniqueGloves`, `uniqueBoots`, `uniqueHelmets` are still emitted for backwards compatibility. New UI path uses `uniqueItems`.
- Source mechanic metadata is still a backend planner contract, not scraped verbatim from PoE2DB. This is intentional because some labels are UX concepts such as `Augment-compatible`.
- `TAG_COMPONENTS` / `COMPOUND_TAG_TOKENS` still exist as plain-text snapshot fallback config in `mod_tag_config.py`; live/full DOM parsing uses PoE2DB badge data.

### Validation performed in cleanup pass 2

```bash
PYTHONPATH=scraper python scraper/run_poc.py --debug --write-schema
```

Result: succeeded.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=scraper pytest -q \
  scraper/tests/test_gloves_subtypes.py \
  scraper/tests/test_normal_affix_parser.py \
  scraper/tests/test_boots_modifier_pools.py \
  scraper/tests/test_payload_contract.py \
  scraper/tests/test_unique_boot_flavour_text.py \
  scraper/tests/test_unique_flavour_text.py \
  scraper/tests/test_treefingers.py \
  scraper/tests/test_url_normalization.py
```

Result: `23 passed`.

```bash
cd web && npm ci --ignore-scripts --prefer-offline
cd web && npx tsc -b
```

Result: succeeded. Full `npm run build` still timed out during the Vite bundling step in this container after TypeScript completed; no TypeScript errors remained.

## Cleanup pass 3 update: unique flavour text hydration

### Problem

Cleanup pass 2 made normal builds rely on class-page catalogue rows for unique armour items. That fixed stale/misclassified unique item problems, but the PoE2DB class catalogue rows do not render unique item flavour text. As a result, `flavourText` stayed empty in the UI payload even though the unique detail pages still contain it.

### Completed in this pass

- Added unique-detail flavour hydration while keeping catalogue rows as the source of truth for:
  - unique membership
  - base type
  - icon
  - visible implicit/explicit mods
- Detail pages are now used for fields that the catalogue does not render, especially `flavourText`.
- Normal builds are offline-friendly and deterministic:
  - use `.cache/poe2db` detail pages if present
  - otherwise use checked-in `scraper/data/snapshots/poe2db/<date>/unique_<class>/*.html` snapshots if present
  - do not live-fetch missing detail pages unless `--force-refresh` or `--update-snapshots` is used
- Added merge guard: if the detail page item name does not match the catalogue item name, hydration is skipped and a diagnostic is emitted.
- Added regression test to ensure detail-page flavour text is merged without letting detail-page mods override catalogue mods.
- Seeded checked-in scraped unique glove detail snapshots from the existing PoE2DB snapshot set so the local payload restores glove flavour text without hardcoded strings.

### Current payload status from available scraped/cached HTML

- `uniqueGloves`: 35 / 35 with `flavourText`
- `uniqueBoots`: 23 / 23 with `flavourText`
- `uniqueHelmets`: 0 / 50 with `flavourText` in this local package because no helmet detail snapshots/cache were available in the uploaded project or older snapshot bundle. Running `python scraper/run_poc.py --update-snapshots --categories Helmets` in an environment with PoE2DB network access will populate the helmet detail snapshots and hydrate them the same way.

### Validation performed in cleanup pass 3

```bash
PYTHONPATH=scraper python scraper/run_poc.py --debug --write-schema
```

Result: succeeded in this workspace and regenerated `out/poe2db_poc_ui.json`, `web/public/data/poe2db_poc_ui.json`, and `web/src/data/poe2db_poc_ui.json`.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=scraper pytest -q \
  scraper/tests/test_unique_detail_flavour_hydration.py \
  scraper/tests/test_unique_flavour_text.py \
  scraper/tests/test_unique_boot_flavour_text.py \
  scraper/tests/test_payload_contract.py
```

Result: `6 passed`.

```bash
PYTHONPATH=scraper python -m py_compile \
  scraper/poe2db_scraper/builder.py \
  scraper/poe2db_scraper/models.py
```

Result: succeeded.

Frontend TypeScript was not revalidated in this container because `web/node_modules` is not present in the uploaded package.

## Pass 4 - generic base item pipeline

Status: implemented.

Changes:

- Added top-level `baseItems` as the primary generic base-item catalogue.
- Base items are parsed from the PoE2DB class-page `Item` tab, not from hardcoded UI defaults.
- Parsed fields include `itemClass`, `name`, `sourceUrl`, `icon`, `requirements`, `defences`, generic `properties`, raw `propertyLines`, and `implicitMods`.
- The planner UI now receives `baseItems` and can list non-armour classes once their class pages have been refreshed.
- Existing `itemSubtypes[].baseItems` remains for modifier-pool compatibility with Gloves/Boots/Helmets.
- Added Windows helpers:
  - `scripts\refresh_non_weapon_base_items.bat`
  - `scripts\refresh_all_base_items.bat`

Notes:

- `refresh_all_base_items.bat` refreshes class/subtype pages and skips unique detail pages. It is intended to be faster and less opaque than `refresh_all_uniques.bat`.
- Weapon classes are still represented as concrete PoE2DB class pages via the `Weapons` alias expansion.
- Modifier pools are still only fully wired for the armour subtype pipeline. Non-armour base items can appear in the picker, but explicit/enchant/socket pools need their own follow-up pipeline.
