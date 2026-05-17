from pathlib import Path

from poe2db_scraper.class_parser import parse_class_page
from poe2db_scraper.schema import GLOVES_URL


def test_gloves_class_summary_counts(fixtures_dir: Path):
    html = (fixtures_dir / "Gloves.html").read_text(encoding="utf-8")
    parsed = parse_class_page(GLOVES_URL, html)
    assert parsed["kind"] == "item_class"
    assert parsed["summary"]["uniqueCount"] == 35
    assert parsed["summary"]["itemCount"] == 91
    assert parsed["knownSubtypeSlugs"] == [
        "Gloves_str",
        "Gloves_dex",
        "Gloves_int",
        "Gloves_str_dex",
        "Gloves_str_int",
        "Gloves_dex_int",
    ]
