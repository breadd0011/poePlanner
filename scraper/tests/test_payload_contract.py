from __future__ import annotations

from poe2db_scraper.augment_parser import parse_augment_page
from poe2db_scraper.class_parser import parse_class_page
from poe2db_scraper.item_parser import parse_item_page
from poe2db_scraper.models import validate_ui_payload
from poe2db_scraper.schema import (
    GLOVES_DEX_INT_URL,
    GLOVES_DEX_URL,
    GLOVES_INT_URL,
    GLOVES_STR_DEX_URL,
    GLOVES_STR_INT_URL,
    GLOVES_STR_URL,
    GLOVES_URL,
    PARSER_VERSION,
    SCHEMA_VERSION,
    GLOVE_SUBTYPE_URLS,
)
from poe2db_scraper.subtype_parser import parse_subtype_page


def test_payload_contract_validates_fixture_payload(treefingers_html, crude_claw_html, desert_rune_html, fixtures_dir, urls) -> None:
    subtype_url_to_fixture = {
        GLOVES_STR_URL: "Gloves_str.html",
        GLOVES_DEX_URL: "Gloves_dex.html",
        GLOVES_INT_URL: "Gloves_int.html",
        GLOVES_STR_DEX_URL: "Gloves_str_dex.html",
        GLOVES_STR_INT_URL: "Gloves_str_int.html",
        GLOVES_DEX_INT_URL: "Gloves_dex_int.html",
    }
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "parserVersion": PARSER_VERSION,
        "generatedAt": "2026-05-01T00:00:00+00:00",
        "source": "poe2db",
        "sourceUrls": [urls["tree"], urls["claw"], urls["rune"], GLOVES_URL, *GLOVE_SUBTYPE_URLS],
        "items": [
            parse_item_page(urls["tree"], treefingers_html),
            parse_item_page(urls["claw"], crude_claw_html),
        ],
        "augment": parse_augment_page(urls["rune"], desert_rune_html),
        "itemClasses": [parse_class_page(GLOVES_URL, (fixtures_dir / "Gloves.html").read_text(encoding="utf-8"))],
        "itemSubtypes": [
            parse_subtype_page(url, (fixtures_dir / subtype_url_to_fixture[url]).read_text(encoding="utf-8"))
            for url in GLOVE_SUBTYPE_URLS
        ],
    }

    validate_ui_payload(payload)


def test_parser_sanity_accepts_weapon_unique_summary_fields() -> None:
    from poe2db_scraper.models import ParserSanityReport

    report = ParserSanityReport.model_validate({
        "weaponUniqueItemsByClass": {"Bows": 10, "Talismans": 4},
        "importedWeaponUniqueItems": 14,
        "importedWeaponUniqueItemClasses": 2,
    })

    assert report.weaponUniqueItemsByClass == {"Bows": 10, "Talismans": 4}
    assert report.importedWeaponUniqueItems == 14
    assert report.importedWeaponUniqueItemClasses == 2
