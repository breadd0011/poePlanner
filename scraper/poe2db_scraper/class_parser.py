from __future__ import annotations

import re
from typing import Any

from .text import clean_display_text, get_page_lines_from_html, slug_from_url


def _visible(line: str) -> str:
    line = re.sub(r"【\d+†Image:[^】]+】", "", line)
    line = re.sub(r"【\d+†([^】†]+)】", r"\1", line)
    line = re.sub(r"【\d+†([^】]+)†[^】]+】", r"\1", line)
    return clean_display_text(line)


def _count_from_heading(lines: list[str], label: str) -> int | None:
    for line in lines:
        if m := re.search(rf"{re.escape(label)}\s*/(\d+)", line):
            return int(m.group(1))
    return None


def parse_class_page(source_url: str, html: str) -> dict[str, Any]:
    lines = [_visible(line) for line in get_page_lines_from_html(html)]
    slug = slug_from_url(source_url)
    item_class = slug.replace("_", " ")
    unique_count = _count_from_heading(lines, f"{item_class} Unique")
    item_count = _count_from_heading(lines, f"{item_class} Item")

    # Class page is a catalogue overview, not a full unique parser.
    unique_names: list[str] = []
    in_unique = False
    for line in lines:
        if line.startswith(f"##### {item_class} Unique"):
            in_unique = True
            continue
        if in_unique and line.startswith("##### "):
            break
        if in_unique and line and not line.startswith("Reset") and not any(marker in line for marker in ["%", "Adds ", "Gain ", "Cannot ", "Image:"]):
            if len(unique_names) < 12 and re.search(r"[A-Za-z]", line):
                unique_names.append(line)

    return {
        "id": f"poe2db:{slug}",
        "slug": slug,
        "source": "poe2db",
        "sourceUrl": source_url,
        "kind": "item_class",
        "itemClass": item_class,
        "summary": {
            "uniqueCount": unique_count,
            "itemCount": item_count,
        },
        "knownSubtypeSlugs": [f"{item_class}_str", f"{item_class}_dex", f"{item_class}_int", f"{item_class}_str_dex", f"{item_class}_str_int", f"{item_class}_dex_int"],
        "sampleUniqueLabels": unique_names,
        "parseStatus": "ok",
        "warnings": [],
    }
