from poe2db_scraper.schema import HELMETS_URL, HELMET_SUBTYPE_URLS
from poe2db_scraper.snapshot_updater import normalize_categories, CATEGORY_SNAPSHOTS
from poe2db_scraper.subtype_parser import SUBTYPE_META


def test_helmet_snapshot_category_is_supported_by_singular_and_plural_names():
    assert normalize_categories(["Helmet"]) == ["Helmets"]
    assert normalize_categories(["Helmets"]) == ["Helmets"]
    config = CATEGORY_SNAPSHOTS["Helmets"]
    assert config.class_url == HELMETS_URL
    assert config.subtype_urls == list(HELMET_SUBTYPE_URLS)
    assert len(config.subtype_urls) == 6


def test_helmet_subtype_metadata_profiles_are_configured():
    assert SUBTYPE_META["Helmets_str"]["defenceProfile"] == ["armour"]
    assert SUBTYPE_META["Helmets_dex"]["defenceProfile"] == ["evasion"]
    assert SUBTYPE_META["Helmets_int"]["defenceProfile"] == ["energy_shield"]
    assert SUBTYPE_META["Helmets_str_dex"]["attributeProfile"] == ["str", "dex"]
    assert SUBTYPE_META["Helmets_str_int"]["attributeProfile"] == ["str", "int"]
    assert SUBTYPE_META["Helmets_dex_int"]["attributeProfile"] == ["dex", "int"]
