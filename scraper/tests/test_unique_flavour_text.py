from pathlib import Path

from poe2db_scraper.fetcher import cache_path_for_url
from poe2db_scraper.schema import GLOVES_URL, HELMETS_URL
from poe2db_scraper.unique_gloves_parser import extract_unique_catalogue_items


def _cached_class_html(project_root: Path, source_url: str) -> str:
    return cache_path_for_url(source_url, project_root / ".cache" / "poe2db").read_text(encoding="utf-8")


def test_gloves_uniques_are_imported_from_poe2db_catalogue(project_root: Path) -> None:
    unique_gloves = extract_unique_catalogue_items(GLOVES_URL, _cached_class_html(project_root, GLOVES_URL), item_class="Gloves")
    assert len(unique_gloves) == 35
    treefingers = next(item for item in unique_gloves if item["name"] == "Treefingers")
    assert treefingers["baseType"] == "Riveted Mitts"
    assert treefingers["sourceUrl"] == "https://poe2db.tw/us/Treefingers"
    assert any("Giant's Blood" in mod["text"] for mod in treefingers["explicitMods"])


def test_helmet_uniques_are_imported_from_helmet_catalogue(project_root: Path) -> None:
    unique_helmets = extract_unique_catalogue_items(HELMETS_URL, _cached_class_html(project_root, HELMETS_URL), item_class="Helmets")
    assert len(unique_helmets) == 50
    assert all(item["kind"] == "unique_helmet" for item in unique_helmets)
    assert all(item["baseType"] for item in unique_helmets)
    assert all(item["explicitMods"] for item in unique_helmets)
    assert all(item["name"] != "Helmets" for item in unique_helmets)
