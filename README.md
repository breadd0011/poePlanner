# PoE2 Planner Monorepo

This repository is split into two independent projects:

- `scraper/` - Python PoE2DB scraper and payload generator.
- `web/` - Vite/React planner UI.

The only intentional coupling is the generated payload. The scraper writes its own build artifacts to `scraper/out/`, then copies the web-facing JSON files into `web/public/data/` so the static frontend can load them from `/data/...`.

## Common Commands

From the repository root:

```bat
scraper\scripts\generate_payload.bat
scraper\scripts\show_health_report.bat
scraper\scripts\run_scraper_tests.bat
```

```bat
cd web
npm install
npm run dev
npm run build
```

Do not commit local archives such as `image.rar` or `latestVer.zip`; they are ignored as local artifacts.
