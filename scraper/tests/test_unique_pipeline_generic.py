from poe2db_scraper.models import UniqueItem
from poe2db_scraper.snapshot_updater import normalize_categories
from poe2db_scraper.unique_gloves_parser import extract_unique_catalogue_items


def test_generic_unique_catalogue_parser_supports_amulets():
    html = '''
    <div id="AmuletsUnique">
      <div class="d-flex">
        <a class="uniqueitem" href="/us/Igniferis">
          <img src="https://cdn.poe2db.tw/image/Art/2DItems/Amulets/Uniques/Igniferis.webp" />
        </a>
        <div>
          <a class="uniqueitem" href="/us/Igniferis">
            <span class="uniqueName">Igniferis</span>
            <span class="uniqueTypeLine">Crimson Amulet</span>
          </a>
          <div class="explicitMod">+(10—20)% to Fire Resistance</div>
        </div>
      </div>
    </div>
    '''
    items = extract_unique_catalogue_items("https://poe2db.tw/us/Amulets", html, item_class="Amulets")

    assert len(items) == 1
    item = items[0]
    assert item["id"] == "unique_amulets_igniferis"
    assert item["kind"] == "unique_item"
    assert item["itemClass"] == "Amulets"
    assert item["baseType"] == "Crimson Amulet"
    assert item["sourceUrl"] == "https://poe2db.tw/us/Igniferis"
    assert item["explicitMods"][0]["text"] == "+(10—20)% to Fire Resistance"


def test_unique_item_model_accepts_generic_classes():
    item = UniqueItem.model_validate({
        "id": "unique_amulets_igniferis",
        "slug": "Igniferis",
        "source": "poe2db",
        "sourceUrl": "https://poe2db.tw/us/Igniferis",
        "kind": "unique_item",
        "name": "Igniferis",
        "baseType": "Crimson Amulet",
        "itemClass": "Amulets",
        "rarity": "Unique",
    })

    assert item.kind == "unique_item"
    assert item.itemClass == "Amulets"


def test_focus_alias_normalizes_to_foci():
    assert normalize_categories(["Focuses"]) == ["Foci"]


def test_weapons_alias_expands_to_concrete_weapon_classes():
    categories = normalize_categories(["Weapons"])

    assert "Claws" in categories
    assert "Bows" in categories
    assert "Talismans" in categories
    assert "Traps" not in categories
    assert "Weapons" not in categories
    assert len(categories) > 5


def test_generic_unique_catalogue_parser_supports_weapon_classes():
    html = '''
    <div id="BowsUnique">
      <div class="d-flex">
        <a class="uniqueitem" href="/us/Deaths_Harp">
          <img src="https://cdn.poe2db.tw/image/Art/2DItems/Weapons/TwoHandWeapons/Bows/Uniques/DeathsHarp.webp" />
        </a>
        <div>
          <a class="uniqueitem" href="/us/Deaths_Harp">
            <span class="uniqueName">Death's Harp</span>
            <span class="uniqueTypeLine">Dualstring Bow</span>
          </a>
          <div class="explicitMod">Bow Attacks fire an additional Arrow</div>
        </div>
      </div>
    </div>
    '''

    items = extract_unique_catalogue_items("https://poe2db.tw/us/Bows", html, item_class="Bows")

    assert len(items) == 1
    item = items[0]
    assert item["id"] == "unique_bows_deaths_harp"
    assert item["kind"] == "unique_item"
    assert item["itemClass"] == "Bows"
    assert item["baseType"] == "Dualstring Bow"
    assert item["sourceUrl"] == "https://poe2db.tw/us/Deaths_Harp"
    assert item["icon"] == "Art/2DItems/Weapons/TwoHandWeapons/Bows/Uniques/DeathsHarp"
    assert item["explicitMods"][0]["text"] == "Bow Attacks fire an additional Arrow"
