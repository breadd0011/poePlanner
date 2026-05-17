from pathlib import Path

from poe2db_scraper.base_item_parser import parse_base_items_from_class_page
from poe2db_scraper.models import validate_ui_payload
from poe2db_scraper.schema import GLOVES_URL, HELMETS_URL


def test_parse_base_items_from_class_page_dom_includes_icon_and_source_url(project_root: Path):
    html = (project_root / "data" / "snapshots" / "poe2db" / "2026-05-06" / "pages" / "gloves.html").read_text(encoding="utf-8")
    items = parse_base_items_from_class_page(GLOVES_URL, html, item_class="Gloves")

    assert items
    assert not any("DNT" in item["name"] for item in items)
    stocky = next(item for item in items if item["name"] == "Stocky Mitts")
    assert stocky["sourceUrl"].endswith("/Stocky_Mitts")
    assert stocky["icon"].startswith("Art/2DItems/Armours/Gloves/")
    assert stocky["defences"] == {"armour": 15}


def test_parse_base_items_includes_implicit_only_real_catalogue_item(project_root: Path):
    html = (project_root / "data" / "snapshots" / "poe2db" / "2026-05-06" / "pages" / "gloves.html").read_text(encoding="utf-8")
    items = parse_base_items_from_class_page(GLOVES_URL, html, item_class="Gloves")

    golden = next(item for item in items if item["name"] == "Golden Bracers")
    assert golden["requirements"]["level"] == 12
    assert golden["implicitMods"]
    assert golden["implicitMods"][0]["text"] == "+(20—30) to maximum Life"


def test_generated_payload_has_top_level_base_items(project_root: Path):
    import json

    payload = json.loads((project_root / "out" / "poe2db_poc_ui.json").read_text(encoding="utf-8"))
    validate_ui_payload(payload)

    assert payload["baseItems"]
    assert payload["parserSanity"]["importedBaseItems"] == len(payload["baseItems"])
    assert payload["parserSanity"]["baseItemsByClass"]["Helmets"] >= 100
    helmet = next(item for item in payload["baseItems"] if item["name"] == "Rusted Greathelm")
    assert helmet["itemClass"] == "Helmets"
    assert helmet["sourceUrl"].endswith("/Rusted_Greathelm")
    assert helmet["icon"]
