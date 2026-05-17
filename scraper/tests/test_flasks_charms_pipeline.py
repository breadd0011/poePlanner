from __future__ import annotations

from poe2db_scraper.base_item_parser import parse_base_items_from_class_page
from poe2db_scraper.modifier_coverage_config import (
    CLASS_LEVEL_PRODUCTION_MODIFIER_ITEM_CLASSES,
    REQUIRED_MODIFIER_CLASSES,
    UTILITY_MODIFIER_ITEM_CLASSES,
)
from poe2db_scraper.schema import OPTIONAL_BASE_ITEM_CLASSES, OPTIONAL_UNIQUE_ITEM_CLASSES, UNIQUE_ITEM_CLASS_URLS
from poe2db_scraper.snapshot_updater import CATEGORY_SNAPSHOTS, normalize_categories
from poe2db_scraper.unique_gloves_parser import extract_unique_catalogue_items


def test_utility_item_classes_are_registered_for_payload_refresh() -> None:
    for item_class in ("Life Flasks", "Mana Flasks", "Charms"):
        assert item_class in UNIQUE_ITEM_CLASS_URLS
        assert item_class in OPTIONAL_BASE_ITEM_CLASSES
        assert item_class in OPTIONAL_UNIQUE_ITEM_CLASSES
        assert item_class in CATEGORY_SNAPSHOTS


def test_utility_modifier_classes_are_required_class_level_pools() -> None:
    assert UTILITY_MODIFIER_ITEM_CLASSES == ("Life Flasks", "Mana Flasks", "Charms")
    for item_class in UTILITY_MODIFIER_ITEM_CLASSES:
        assert item_class in CLASS_LEVEL_PRODUCTION_MODIFIER_ITEM_CLASSES
        assert item_class in REQUIRED_MODIFIER_CLASSES


def test_flask_and_utility_aliases_expand_to_concrete_classes() -> None:
    assert normalize_categories(["Flasks"]) == ["Life Flasks", "Mana Flasks"]
    assert normalize_categories(["Utility"]) == ["Life Flasks", "Mana Flasks", "Charms"]
    assert normalize_categories(["life flask", "mana flask", "charm"]) == ["Life Flasks", "Mana Flasks", "Charms"]


def test_generic_base_item_parser_supports_life_flask_rows() -> None:
    html = '''
    <div id="LifeFlasksItem">
      <div class="d-flex">
        <a class="whiteitem" href="/us/Lesser_Life_Flask">
          <img src="https://cdn.poe2db.tw/image/Art/2DItems/Flasks/FlaskLife01.webp" />
        </a>
        <div>
          <a class="whiteitem" href="/us/Lesser_Life_Flask">Lesser Life Flask</a>
          <div class="property">Recovers 50 Life over 3 Second</div>
          <div class="property">Consumes 10 of 60 Charges on use</div>
          <div class="property">Currently has 60 Charges</div>
        </div>
      </div>
    </div>
    '''

    items = parse_base_items_from_class_page("https://poe2db.tw/us/Life_Flasks", html, item_class="Life Flasks")

    assert len(items) == 1
    item = items[0]
    assert item["itemClass"] == "Life Flasks"
    assert item["name"] == "Lesser Life Flask"
    assert item["sourceUrl"] == "https://poe2db.tw/us/Lesser_Life_Flask"
    assert item["icon"] == "Art/2DItems/Flasks/FlaskLife01"
    assert "Recovers 50 Life over 3 Second" in item["propertyLines"]


def test_generic_unique_catalogue_parser_supports_charms() -> None:
    html = '''
    <div id="CharmsUnique">
      <div class="d-flex">
        <a class="uniqueitem" href="/us/Breath_of_the_Mountains">
          <img src="https://cdn.poe2db.tw/image/Art/2DItems/Charms/SapphireUniqueCharm.webp" />
        </a>
        <div>
          <a class="uniqueitem" href="/us/Breath_of_the_Mountains">
            <span class="uniqueName">Breath of the Mountains</span>
            <span class="uniqueTypeLine">Sapphire Charm</span>
          </a>
          <div class="explicitMod">Grants a Power Charge on use</div>
          <div class="flavourText">To scrape the sky</div>
        </div>
      </div>
    </div>
    '''

    items = extract_unique_catalogue_items("https://poe2db.tw/us/Charms", html, item_class="Charms")

    assert len(items) == 1
    item = items[0]
    assert item["id"] == "unique_charms_breath_of_the_mountains"
    assert item["itemClass"] == "Charms"
    assert item["baseType"] == "Sapphire Charm"
    assert item["sourceUrl"] == "https://poe2db.tw/us/Breath_of_the_Mountains"
    assert item["explicitMods"][0]["text"] == "Grants a Power Charge on use"
