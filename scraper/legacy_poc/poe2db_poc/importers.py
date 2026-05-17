from __future__ import annotations

from typing import Any

from .fetcher import fetch_html, lines_from_html
from .parsing import (
    classify_tooltip_sections,
    extract_trade_json_if_present,
    parse_mod_blocks,
    parse_object_data,
    safe_item_name,
    slice_tooltip_lines,
    strip_markup,
    title_from_url,
)


ITEM_CLASS_FROM_URL_FALLBACK = {
    'Treefingers': 'Gloves',
    'Crude_Claw': 'Claws',
}


def infer_rarity(trade_json: dict[str, Any] | None, lines: list[str], mods: list[dict[str, Any]]) -> str | None:
    if trade_json and trade_json.get('rarity'):
        return str(trade_json['rarity'])
    if any((m.get('generationType') or '').startswith('Unique') or 'Unique' in (m.get('generationType') or '') for m in mods):
        return 'Unique'
    return None


def parse_item_page(source_url: str, *, force_refresh: bool = False) -> dict[str, Any]:
    html = fetch_html(source_url, force_refresh=force_refresh)
    lines = lines_from_html(html)
    object_data = parse_object_data(lines)
    trade_json = extract_trade_json_if_present(html)

    name = safe_item_name(lines, source_url, trade_json)
    base_type = object_data.get('baseType')
    if not base_type and trade_json:
        base_type = trade_json.get('baseType') or trade_json.get('typeLine')
    if not base_type:
        base_type = name

    item_class = object_data.get('itemClass')
    if not item_class:
        slug = source_url.rstrip('/').split('/')[-1]
        item_class = ITEM_CLASS_FROM_URL_FALLBACK.get(slug)
    if not item_class and trade_json:
        props = trade_json.get('properties') or []
        if props and isinstance(props[0], dict):
            item_class = strip_markup(props[0].get('name'))

    tooltip_lines = slice_tooltip_lines(lines, name)
    tooltip_sections = classify_tooltip_sections(
        tooltip_lines,
        name=name,
        base_type=base_type,
        item_class=item_class,
    )
    mods = parse_mod_blocks(lines)

    # Optional enrichment: if trade JSON is present, use it for rolled display values only when
    # the HTML/text-first parser found too little. It is not required for base item pages.
    if trade_json and not any(section['kind'] == 'explicit' for section in tooltip_sections):
        explicit_mods = [strip_markup(x) for x in trade_json.get('explicitMods', []) if strip_markup(x)]
        if explicit_mods:
            tooltip_sections.append({'kind': 'explicit', 'lines': explicit_mods})

    frame_type = trade_json.get('frameType') if trade_json else None
    rarity = infer_rarity(trade_json, lines, mods)

    return {
        'sourceUrl': source_url,
        'kind': 'item',
        'name': name,
        'baseType': base_type,
        'itemClass': item_class,
        'rarity': rarity,
        'icon': object_data.get('icon') or (trade_json.get('icon') if trade_json else None),
        'frameType': frame_type,
        'tooltipSections': tooltip_sections,
        'mods': mods,
    }


def parse_augment_page(source_url: str, *, force_refresh: bool = False) -> dict[str, Any]:
    html = fetch_html(source_url, force_refresh=force_refresh)
    lines = lines_from_html(html)
    object_data = parse_object_data(lines)

    name = safe_item_name(lines, source_url, None)
    item_class = object_data.get('itemClass') or 'Augment'

    # The useful Desert Rune tooltip starts at the plain item name line and ends at image/Forge Recipe.
    tooltip_lines = slice_tooltip_lines(lines, name)

    sections: list[dict[str, Any]] = [{'kind': 'title', 'lines': [name, item_class]}]
    property_lines: list[str] = []
    requirement_lines: list[str] = []
    description_lines: list[str] = []
    bonded = False

    for line in tooltip_lines[1:]:
        clean = strip_markup(line) or ''
        if not clean or clean == item_class:
            continue
        if clean.startswith('Stack Size:'):
            property_lines.append(clean)
            continue
        if clean.startswith('Requires:'):
            requirement_lines.append(clean)
            continue
        if clean == 'Bonded:':
            bonded = True
            continue

        effect_prefixes = {
            'Martial Weapon:': 'martial_weapon',
            'Wand or Staff:': 'wand_or_staff',
            'Armour:': 'armour',
        }
        matched_effect = False
        for prefix, condition in effect_prefixes.items():
            if clean.startswith(prefix):
                effect_text = clean[len(prefix):].strip()
                sections.append({
                    'kind': 'augment_effect',
                    'condition': condition,
                    'bonded': bonded,
                    'lines': [effect_text],
                })
                matched_effect = True
                break
        if matched_effect:
            continue

        # Long non-effect text is descriptive text.
        if 'Place into an empty' in clean or 'Shift click' in clean or description_lines:
            description_lines.append(clean)

    if property_lines:
        sections.insert(1, {'kind': 'property', 'lines': property_lines})
    if requirement_lines:
        insert_at = 2 if property_lines else 1
        sections.insert(insert_at, {'kind': 'requirement', 'lines': requirement_lines})
    if description_lines:
        sections.append({'kind': 'description', 'lines': description_lines})

    return {
        'sourceUrl': source_url,
        'kind': 'augment',
        'name': name,
        'itemClass': item_class,
        'baseType': object_data.get('baseType') or name,
        'icon': object_data.get('icon'),
        'tooltipSections': sections,
    }


def build_poc_payload(*, force_refresh: bool = False, debug: bool = False) -> dict[str, Any]:
    urls = {
        'treefingers': 'https://poe2db.tw/us/Treefingers',
        'crudeClaw': 'https://poe2db.tw/us/Crude_Claw',
        'desertRune': 'https://poe2db.tw/us/Desert_Rune',
    }

    payload: dict[str, Any] = {
        'schemaVersion': 'poc-0.4',
        'items': [
            parse_item_page(urls['treefingers'], force_refresh=force_refresh),
            parse_item_page(urls['crudeClaw'], force_refresh=force_refresh),
        ],
        'augment': parse_augment_page(urls['desertRune'], force_refresh=force_refresh),
    }

    # Compatibility alias: first item as item, because the earlier POC had singular item.
    payload['item'] = payload['items'][0]

    if debug:
        debug_pages: dict[str, Any] = {}
        for key, url in urls.items():
            html = fetch_html(url, force_refresh=False)
            lines = lines_from_html(html)
            debug_pages[key] = {
                'url': url,
                'titleFromUrl': title_from_url(url),
                'objectData': parse_object_data(lines),
                'first80Lines': lines[:80],
                'hasTradeJson': extract_trade_json_if_present(html) is not None,
            }
        payload['_debug'] = debug_pages

    return payload
