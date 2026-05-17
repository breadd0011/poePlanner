from __future__ import annotations

import html as html_lib
import json
import re
from typing import Any
from urllib.parse import unquote, urlparse

NAV_JUNK = {
    'Update cookie preferences',
    'PoE2 DB',
    'Item',
    'Gem',
    'Skill Gems',
    'Support Gems',
    'Spirit Gems',
    'Lineage Supports',
    'Modifiers',
    'Desecrated Modifiers',
    'Keywords',
    'Crafting',
    'Quest',
    'Ascendancy Classes',
    'Passive Skill Tree',
    'Act',
    'Waystones',
    'Economy',
    'Patreon',
    'US English',
    'Edit',
}

PROPERTY_PREFIXES = (
    'Physical Damage:',
    'Critical Hit Chance:',
    'Attacks per Second:',
    'Weapon Range:',
    'Armour:',
    'Evasion Rating:',
    'Energy Shield:',
    'Block chance:',
    'Stack Size:',
)


def strip_markup(text: str | None) -> str | None:
    if text is None:
        return None

    text = html_lib.unescape(str(text))
    text = text.replace('\r', '')
    # PoE trade markup: [Strength|Str] -> Str, [Armour] -> Armour
    text = re.sub(r'\[([^|\]]+)\|([^\]]+)\]', r'\2', text)
    text = re.sub(r'\[([^\]]+)\]', r'\1', text)
    # Normalize whitespace but preserve em dash ranges.
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def title_from_url(url: str) -> str:
    slug = unquote(urlparse(url).path.rstrip('/').split('/')[-1])
    return slug.replace('_', ' ').strip()


def slug_from_url(url: str) -> str:
    return unquote(urlparse(url).path.rstrip('/').split('/')[-1]).strip()


def is_junk_line(line: str) -> bool:
    clean = line.strip()
    if not clean:
        return True
    if clean in NAV_JUNK:
        return True
    if clean.startswith('Image:'):
        return True
    if clean.startswith('Copyright'):
        return True
    if len(clean) > 200:
        return True
    return False


def value_after_label(lines: list[str], label: str) -> str | None:
    for i, line in enumerate(lines):
        clean = strip_markup(line) or ''
        prefix = label + ' '

        # Case: "BaseType Crude Claw"
        if clean.startswith(prefix):
            value = clean[len(prefix):].strip()
            if value:
                return value

        # Case: "BaseType" then next line contains the value.
        if clean == label and i + 1 < len(lines):
            value = strip_markup(lines[i + 1])
            if value:
                return value

    return None


def parse_object_data(lines: list[str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    label_map = {
        'DropLevel': 'dropLevel',
        'BaseType': 'baseType',
        'Class': 'itemClass',
        'Flags': 'flags',
        'Type': 'type',
        'Tags': 'tagsRaw',
        'Icon': 'icon',
        'Acronym': 'acronym',
        'Release Version': 'releaseVersion',
        'Currency Exchange': 'currencyExchange',
        'NoteCode': 'noteCode',
    }

    for label, key in label_map.items():
        value = value_after_label(lines, label)
        if value is not None:
            data[key] = value

    if 'tagsRaw' in data:
        data['tags'] = [x.strip() for x in str(data['tagsRaw']).split(',') if x.strip()]

    # Collect simple dotted object values too: Weapon.minimum_damage 5, Sockets.socket_info 1:5:100
    object_prefixes = (
        'Base.',
        'Mods.',
        'AttributeRequirements.',
        'Weapon.',
        'Quality.',
        'Sockets.',
    )
    for line in lines:
        clean = strip_markup(line) or ''
        if any(clean.startswith(prefix) for prefix in object_prefixes):
            if ' ' in clean:
                key, value = clean.split(' ', 1)
                data[key] = value.strip()

    return data


def safe_item_name(lines: list[str], source_url: str, trade_json: dict[str, Any] | None = None) -> str:
    if trade_json and trade_json.get('name'):
        return strip_markup(trade_json.get('name')) or title_from_url(source_url)

    url_title = title_from_url(source_url)

    # Exact title match from URL, good for Treefingers and Crude Claw.
    for line in lines:
        clean = strip_markup(line) or ''
        if clean.lower() == url_title.lower():
            return clean

    # For base items, object BaseType is often the item name.
    base_type = value_after_label(lines, 'BaseType')
    if base_type:
        return base_type

    # First plausible content line before the first ##### block.
    for line in lines:
        clean = strip_markup(line) or ''
        if clean.startswith('##### '):
            break
        if is_junk_line(clean):
            continue
        if clean.startswith('* '):
            continue
        if '/' in clean and len(clean) < 30:
            continue
        return clean

    return url_title


def extract_trade_json_if_present(html_text: str) -> dict[str, Any] | None:
    # Optional enrichment only. Do not rely on this for base item pages.
    markers = ['"realm": "poe2"', '"realm":"poe2"']
    start_marker = -1
    for marker in markers:
        start_marker = html_text.find(marker)
        if start_marker != -1:
            break
    if start_marker == -1:
        return None

    start = html_text.rfind('{', 0, start_marker)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(html_text)):
        ch = html_text[i]
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                raw = html_text[start:i + 1]
                raw = html_lib.unescape(raw)
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return None
    return None


def slice_tooltip_lines(lines: list[str], name: str) -> list[str]:
    start = None
    for i, line in enumerate(lines):
        clean = strip_markup(line) or ''
        if clean.lower() == name.lower():
            start = i
            break

    if start is None:
        return []

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith('##### '):
            end = i
            break

    return [strip_markup(x) or '' for x in lines[start:end] if strip_markup(x)]


def normalize_requirement_line(line: str) -> list[str]:
    if not line.startswith('Requires:'):
        return []
    raw = line.replace('Requires:', '').strip()
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    return [f'Requires: {p}' for p in parts]


def classify_tooltip_sections(tooltip_lines: list[str], *, name: str, base_type: str | None, item_class: str | None) -> list[dict[str, Any]]:
    if not tooltip_lines:
        title_lines = [name]
        if base_type and base_type != name:
            title_lines.append(base_type)
        return [{'kind': 'title', 'lines': title_lines}]

    sections: list[dict[str, Any]] = []

    idx = 0
    title_lines = []
    if idx < len(tooltip_lines):
        title_lines.append(tooltip_lines[idx])
        idx += 1
    if idx < len(tooltip_lines) and base_type and tooltip_lines[idx] == base_type and base_type != name:
        title_lines.append(tooltip_lines[idx])
        idx += 1
    elif base_type and base_type != name and base_type not in title_lines:
        # Unique pages often have name then type line; base item pages usually do not.
        pass

    if title_lines:
        sections.append({'kind': 'title', 'lines': title_lines})

    property_lines = []
    requirement_lines = []
    mod_lines = []
    flavour_lines = []

    # If the next line is an item class, keep it as property.
    while idx < len(tooltip_lines):
        line = tooltip_lines[idx]
        idx += 1

        if not line or line.startswith('Image'):
            continue

        reqs = normalize_requirement_line(line)
        if reqs:
            requirement_lines.extend(reqs)
            continue

        if item_class and line == item_class:
            property_lines.append(line)
            continue

        if line.startswith(PROPERTY_PREFIXES):
            property_lines.append(line)
            continue

        # Rune/augment labels are handled elsewhere.
        if line in {'Augment'} or line.startswith('Stack Size:'):
            property_lines.append(line)
            continue

        # Crude Claw has only properties; Treefingers has explicit mods after requirements/properties.
        looks_like_mod = (
            '%' in line or
            line.startswith('+') or
            line.startswith('Adds ') or
            'reduced ' in line or
            'increased ' in line or
            "Giant's Blood" in line
        )
        if looks_like_mod:
            mod_lines.append(line)
            continue

        # Remaining short lines after mods are likely flavour.
        if mod_lines or flavour_lines:
            flavour_lines.append(line)
        else:
            property_lines.append(line)

    if property_lines:
        sections.append({'kind': 'property', 'lines': property_lines})
    if requirement_lines:
        sections.append({'kind': 'requirement', 'lines': requirement_lines})
    if mod_lines:
        sections.append({'kind': 'explicit', 'lines': mod_lines})
    if flavour_lines:
        sections.append({'kind': 'flavour', 'lines': flavour_lines})

    return sections


def parse_internal_stat_line(line: str) -> dict[str, Any]:
    clean = strip_markup(line) or line
    scope = None
    if clean.endswith(' Global'):
        scope = 'Global'
        clean = clean[:-7]
    elif clean.endswith(' Local'):
        scope = 'Local'
        clean = clean[:-6]

    m = re.match(r'(.+?)\s+(-?\d+)\s+—\s+(-?\d+)$', clean)
    if m:
        return {
            'id': m.group(1).strip(),
            'min': int(m.group(2)),
            'max': int(m.group(3)),
            'scope': scope,
            'raw': line,
        }

    return {'id': clean, 'min': None, 'max': None, 'scope': scope, 'raw': line}


def parse_mod_blocks(lines: list[str]) -> list[dict[str, Any]]:
    mods: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in lines:
        clean = strip_markup(line) or ''
        if clean.startswith('##### '):
            title = clean.removeprefix('##### ').strip()
            # Skip known non-mod blocks.
            if any(x in title for x in ['Attr /', 'Version history', 'Forge Recipe', 'Recipe /', 'Sites', 'News', 'About Site']):
                if current and current.get('family'):
                    mods.append(current)
                current = None
                continue
            if current and current.get('family'):
                mods.append(current)
            current = {
                'text': title,
                'family': None,
                'domains': None,
                'generationType': None,
                'requiredLevel': None,
                'stats': [],
                'craftTags': [],
            }
            continue

        if not current:
            continue

        if clean.startswith('Family '):
            current['family'] = clean.removeprefix('Family ').strip()
        elif clean.startswith('Domains '):
            current['domains'] = clean.removeprefix('Domains ').strip()
        elif clean.startswith('GenerationType '):
            current['generationType'] = clean.removeprefix('GenerationType ').strip()
        elif clean.startswith('Req. level '):
            raw = clean.removeprefix('Req. level ').strip()
            current['requiredLevel'] = int(raw) if raw.isdigit() else raw
        elif clean.startswith('* '):
            current['stats'].append(parse_internal_stat_line(clean.removeprefix('* ').strip()))
        elif clean.startswith('Craft Tags '):
            current['craftTags'] = clean.removeprefix('Craft Tags ').strip().split()

    if current and current.get('family'):
        mods.append(current)

    return mods
