from pathlib import Path

from poe2db_scraper.fetcher import cache_path_for_url
from poe2db_scraper.schema import BOOTS_URL
from poe2db_scraper.unique_gloves_parser import extract_unique_catalogue_items, normalize_poe2db_item_url


def test_locale_navigation_links_are_not_unique_item_urls():
    source = "https://poe2db.tw/us/Gloves"
    assert normalize_poe2db_item_url(source, "tw/Gloves") is None
    assert normalize_poe2db_item_url(source, "/tw/Gloves") is None
    assert normalize_poe2db_item_url(source, "https://poe2db.tw/tw/Gloves") is None


def test_item_links_are_canonicalized_to_us_urls():
    source = "https://poe2db.tw/us/Gloves"
    assert normalize_poe2db_item_url(source, "Treefingers") == "https://poe2db.tw/us/Treefingers"
    assert normalize_poe2db_item_url(source, "/us/Treefingers") == "https://poe2db.tw/us/Treefingers"


def test_unique_boot_catalogue_preserves_poe2db_hyphen_slug(project_root: Path):
    html = cache_path_for_url(BOOTS_URL, project_root / ".cache" / "poe2db").read_text(encoding="utf-8")
    unique_boots = extract_unique_catalogue_items(BOOTS_URL, html, item_class="Boots")
    knight = next(item for item in unique_boots if item["name"] == "The Knight-errant")
    assert knight["sourceUrl"].endswith("/The_Knight-errant")
    assert "The_Knight_errant" not in knight["sourceUrl"]
