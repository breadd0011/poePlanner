from __future__ import annotations

import argparse
import json
from pathlib import Path

from poe2db_poc.importers import build_poc_payload


def main() -> None:
    parser = argparse.ArgumentParser(description='PoE2DB POC scraper v4')
    parser.add_argument('--force-refresh', action='store_true', help='Ignore cache and re-download pages')
    parser.add_argument('--debug', action='store_true', help='Also write debug output with raw lines/object data')
    args = parser.parse_args()

    out_dir = Path('out')
    out_dir.mkdir(exist_ok=True)

    payload = build_poc_payload(force_refresh=args.force_refresh, debug=args.debug)

    ui_payload = {k: v for k, v in payload.items() if k != '_debug'}
    ui_path = out_dir / 'poe2db_poc_ui.json'
    ui_path.write_text(json.dumps(ui_payload, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'Wrote {ui_path}')

    if args.debug:
        debug_path = out_dir / 'poe2db_poc_debug.json'
        debug_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Wrote {debug_path}')


if __name__ == '__main__':
    main()
