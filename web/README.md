# Web

Vite/React planner UI. It is intentionally frontend-only and reads generated scraper data from `public/data/`.

## Layout

- `src/` - React application and feature code.
- `src/features/equipment-planner/` - current planner/editor feature.
- `public/data/` - generated JSON payload copied from the scraper.
- `public/image/` - local image assets used by the UI.
- `scripts/` - frontend-only regression/audit scripts.

## Usage

```bat
cd web
npm install
npm run dev
npm run build
```

Regenerate `public/data/poe2db_poc_ui.json` from the repository root with:

```bat
scraper\scripts\generate_payload.bat
```
