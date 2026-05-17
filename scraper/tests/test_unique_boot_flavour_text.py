from pathlib import Path

from poe2db_scraper.fetcher import cache_path_for_url
from poe2db_scraper.schema import BOOTS_URL
from poe2db_scraper.unique_gloves_parser import extract_unique_catalogue_items


def test_boot_uniques_are_imported_from_poe2db_catalogue(project_root: Path) -> None:
    html = cache_path_for_url(BOOTS_URL, project_root / ".cache" / "poe2db").read_text(encoding="utf-8")
    unique_boots = extract_unique_catalogue_items(BOOTS_URL, html, item_class="Boots")
    assert len(unique_boots) == 23
    knight = next(item for item in unique_boots if item["name"] == "The Knight-errant")
    assert knight["baseType"] == "Mail Sabatons"
    assert knight["sourceUrl"].endswith("/The_Knight-errant")
    assert "The_Knight_errant" not in knight["sourceUrl"]
    assert knight["explicitMods"]
