# Scraper

Python project for collecting PoE2DB source pages and generating planner payloads.

## Layout

- `poe2db_scraper/` - scraper, parser, builder, contract, and health-report code.
- `poe2db_scraper/build_policy.py` - build mode/fallback/write-side-effect policy.
- `poe2db_scraper/augment_classification.py` - shared Augment catalogue/socket classification rules.
- `poe2db_scraper/payload_contract.py` - runtime-vs-diagnostics payload boundaries and slim runtime payload options.
- `poe2db_scraper/fetcher.py` - session-backed HTTP/cache client with retry policy and batch-fetch helper.
- `tests/` - scraper and payload regression tests.
- `data/` - checked-in source snapshots and parser fixtures.
- `.cache/` - local fetch cache, ignored by Git.
- `out/` - generated payload/debug/schema/diagnostics output, ignored by Git.
- `scripts/` - Windows helper scripts for common refresh and test workflows.
- `docs/` - scraper pipeline notes and audits.
- `legacy_poc/` - old prototype kept out of the repo root.

## Usage

From the repository root:

```bat
scraper\scripts\generate_payload.bat
scraper\scripts\show_health_report.bat
scraper\scripts\run_scraper_tests.bat
```

From inside `scraper/`:

```bat
python run_poc.py --debug --write-schema
python run_poc.py --slim-ui-payload
python run_poc.py --build-mode strict --force-refresh
python -m pytest tests
```

`run_poc.py` writes generated files to `scraper/out/`. Copying payload/report files to `../web/public/data/` is explicit via `--copy-web` (the `generate_payload.bat` helper passes it).

Generated outputs:

- `out/poe2db_poc_ui.json` - UI payload. By default it is backward-compatible; `--slim-ui-payload` omits legacy unique arrays and inline diagnostics.
- `out/poe2db_payload_health_report.json` - health report extracted from the payload.
- `out/poe2db_poc_diagnostics.json` - scraper/CI diagnostics split out from the runtime contract.
- `out/poe2db_poc_debug.json` - optional verbose debug output with `--debug`.
- `out/poe2db_poc_schema.json` - optional full Pydantic-derived JSON schema with `--write-schema`.

Build modes and write flags:

- `--build-mode dev` is the default local workflow and still allows cache-oriented fallbacks such as previous generated modifier pool reuse.
- `--build-mode strict` disables previous generated output reuse and stale-cache fallback so release/CI runs fail instead of silently carrying stale data.
- Dated `data/snapshots/...` writes during the payload build require `--write-snapshots`.
- Fetched `data/modifiers_calc_full/...` fixture writes require `--write-modifier-html-cache`.

Contract direction:

- The existing UI payload intentionally stays backward-compatible by default, including legacy unique fields and inline diagnostics.
- Use `python run_poc.py --slim-ui-payload` or `RuntimePayloadOptions.from_slim_flag(True)` when preparing a smaller future frontend payload.
- Parser warnings/diagnostics should use the canonical `{severity, code, message, actionRequired}` shape from `poe2db_scraper.diagnostics`.
- Do not reintroduce runtime dependencies on `poe2db_scraper.static_boots`; it is now an archived compatibility stub.

P2 maintenance notes:

- `poe2db_scraper.fetcher.FetchClient` is the preferred HTTP surface for new scraper flows. It wraps a reusable `requests.Session`, retry policy, stale-cache policy, and deterministic `fetch_many_html` helper.
- `poe2db_scraper.utils.ordered_unique_strings` should be used for source URL and other first-seen-order de-duplication instead of repeated `if value not in list` checks.
- Legacy top-level unique arrays (`uniqueGloves`, `uniqueBoots`, `uniqueHelmets`) are formally deprecated. Keep them only for backward compatibility until the web UI reads from `uniqueItems`.
