# Windows scraper helper scripts

All scripts are Windows CMD friendly and can be run from the repository root, the `scraper` folder, or the `scraper/scripts` folder.
They set `PYTHONPATH=.` automatically where needed.

## Recommended normal workflows

### Regenerate from existing snapshots/cache

```bat
scraper\scripts\generate_payload.bat
scraper\scripts\show_health_report.bat
```

This now prints socket-compatible augment coverage after the payload is written. If the UI shows stale or incomplete augment coverage, use the force-refresh helper below.

To preview the smaller future frontend contract, run:

```bat
python scraper\run_poc.py --slim-ui-payload --debug
```

That writes `out/poe2db_poc_ui.json` without legacy unique arrays or inline diagnostics; diagnostics still go to `out/poe2db_poc_diagnostics.json`.

### Force-refresh socket augment data

```bat
scraper\scripts\refresh_socket_augments.bat
```

Use this after augment parser changes, when the Developer data panel shows incomplete socket augment coverage, or when picker/socket tooltips look stale. It runs the payload builder with `--force-refresh --debug --write-schema`, writes the same payload files as `generate_payload.bat`, and prints CLI coverage/guardrail summaries for rune, Soul Core, and other socket-compatible augment data.

The old helper remains as an alias:

```bat
scraper\scripts\refresh_rune_augments.bat
```

### Refresh non-weapon uniques and flavour text

```bat
scraper\scripts\refresh_non_weapon_uniques.bat
scraper\scripts\show_health_report.bat
```

Use this for the usual unique item workflow. It covers:

```text
Gloves, Boots, Helmets, Body Armours, Shields, Foci, Quivers, Rings, Amulets, Belts,
Life Flasks, Mana Flasks, Charms
```

### Refresh all currently supported modifier pools

```bat
scraper\scripts\refresh_all_supported_modifiers.bat
scraper\scripts\show_health_report.bat
```

This covers the modifier classes currently expected by the health report:

```text
Gloves, Boots, Helmets, Body Armours, Rings, Amulets, Belts, Shields, Foci, Quivers,
Life Flasks, Mana Flasks, Charms,
Bows, Crossbows, Wands, Sceptres, Daggers, Claws, Quarterstaves, Staves,
One Hand Swords, Two Hand Swords, One Hand Axes, Two Hand Axes,
One Hand Maces, Two Hand Maces, Spears, Flails, Talismans
```

Talismans are treated as supported weapon modifiers. Traps are intentionally out of scope. The refresh uses `--skip-unique-details`, so it avoids slow unique detail hydration.

### Run focused scraper tests

```bat
scraper\scripts\run_scraper_tests.bat
```

## Base item catalogue refresh

### Non-weapon base items

```bat
scraper\scripts\refresh_non_weapon_base_items.bat
```

### Weapon base items only

```bat
scraper\scripts\refresh_weapon_base_items.bat
```

### All supported base items

```bat
scraper\scripts\refresh_all_base_items.bat
```

Base item refreshes use `--skip-unique-details`, so they should be much faster than unique detail refreshes.

## Unique refresh helpers

### Helmet-only refresh

```bat
scraper\scripts\refresh_helmets.bat
```

Useful when Helmet flavour text or detail cache is missing.

### Non-weapon uniques

```bat
scraper\scripts\refresh_non_weapon_uniques.bat
```

This is the renamed replacement for the old `refresh_all_snapshots.bat` name.


### Flasks and charms

```bat
scraper\scripts\refresh_flasks_charms.bat
```

Covers Life Flasks, Mana Flasks, and Charms. Use this focused helper when the equipment panel utility slots need fresh base/unique/modifier data without refreshing weapons.

### Weapon uniques only

```bat
scraper\scripts\refresh_weapon_uniques.bat
scraper\scripts\generate_payload.bat
scraper\scripts\show_health_report.bat
```

Weapon uniques are production inputs for `uniqueItems`, including Talismans. This can take a while because the `Weapons` alias expands to many PoE2DB weapon classes and hydrates unique detail pages for flavour text. Traps are intentionally out of scope.

### Full unique refresh

```bat
scraper\scripts\refresh_all_uniques.bat
```

This is the heavy crawl: non-weapon uniques, flask/charm uniques, plus weapon uniques. Use it when you want to fully refresh every production unique detail snapshot; otherwise prefer a narrower helper.

## Modifier refresh helpers

### Accessories

```bat
scraper\scripts\refresh_accessory_modifiers.bat
```

Covers:

```text
Rings, Amulets, Belts
```

### Offhands

```bat
scraper\scripts\refresh_offhand_modifiers.bat
```

Covers:

```text
Shields, Foci, Quivers
```

### Body Armours

```bat
scraper\scripts\refresh_body_armour_modifiers.bat
```

Covers the Body Armour defence-profile modifier pages:

```text
str, dex, int, str_dex, str_int, dex_int
```

### Weapon modifier snapshots

```bat
scraper\scripts\refresh_weapon_modifiers.bat
scraper\scripts\show_health_report.bat
```

This refreshes the concrete PoE2DB weapon class pages via the `Weapons` alias and writes class-page ModifiersCalc HTML. The supported weapon classes, including Talismans, are production-required and wired into the planner pools. Traps are intentionally out of scope.

### All supported modifiers

```bat
scraper\scripts\refresh_all_supported_modifiers.bat
```

Use this when you want one modifier refresh command for everything currently required by the health report, including Life Flasks, Mana Flasks, and Charms.

## Deprecated aliases

`refresh_all_snapshots.bat` is kept as a backward-compatible alias for `refresh_non_weapon_uniques.bat`.
Use the clearer name going forward.
