# Non-armour modifier pipeline plan

## Current patch scope

This patch adds a validator/reporting layer only. It does not change modifier parsing logic.

The goal is to make modifier coverage visible before adding the non-armour parser, so a future parser patch can be verified by data health instead of manual UI checking.

## Support states

Modifier support is now explicitly configured in `scraper/poe2db_scraper/modifier_coverage_config.py`.

### Required

These classes are production-required by the current planner UI and must have both editor pools and normal explicit pools:

- Gloves
- Boots
- Helmets

If any of these lose `editorModifierPools` or `normalExplicitPools`, `payloadHealth.status` becomes `error`.

### Experimental

These are the first non-armour modifier pipeline targets:

- Rings
- Amulets
- Belts

They are reported in `payloadHealth.modifierCoverage`, but they do not create warnings/errors yet if pools are missing. Once their parser is implemented and verified, move them from `experimental` to `required` in the config.

### Unsupported

All other discovered item classes remain unsupported by default. They still appear in `modifierCoverage.byClass` if base/unique items or modifier pools exist, but missing modifier pools are not treated as a problem.

## Report shape

`payloadHealth.modifierCoverage` now contains:

- `supportConfig`: configured required/experimental classes
- `summary`: required/experimental readiness counts
- `byClass`: per-item-class coverage details

Each class row contains:

- base item count
- unique item count
- item subtype count
- editor modifier pool count/mod count
- normal explicit pool count/prefix/suffix count
- support state
- coverage status
- missing required pool list

## Next parser step

After this patch is green, implement the non-armour parser in this order:

1. Rings
2. Amulets
3. Belts

For each class:

1. add/refresh PoE2DB snapshots
2. parse editor pools and normal explicit pools
3. verify `modifierCoverage.byClass[Class].coverageStatus == "experimental_ready"`
4. visually confirm in the UI
5. move the class to required only after the data is stable
