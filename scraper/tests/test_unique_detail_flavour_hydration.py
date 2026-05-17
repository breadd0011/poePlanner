from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from poe2db_scraper.builder import _merge_unique_detail_fields, _snapshot_detail_path_for_unique
from poe2db_scraper.schema import BuildPaths
from poe2db_scraper.unique_gloves_parser import UniqueGloveCandidate, parse_unique_glove_page, stable_slug


def test_unique_detail_page_flavour_is_merged_without_overriding_catalogue_mods(treefingers_html: str, urls: dict[str, str]) -> None:
    catalogue = {
        "id": f"unique_gloves_{stable_slug('Treefingers')}",
        "name": "Treefingers",
        "baseType": "Riveted Mitts",
        "sourceUrl": urls["tree"],
        "explicitMods": [{"id": "catalogue_explicit_001", "text": "CATALOGUE MOD SHOULD STAY"}],
        "flavourText": [],
        "requirements": {},
        "defences": {},
        "tooltipSections": [{"kind": "explicit", "lines": ["CATALOGUE MOD SHOULD STAY"]}],
        "diagnostics": [],
        "warnings": [],
    }
    detail = parse_unique_glove_page(urls["tree"], treefingers_html, expected_base_type="Riveted Mitts", fallback=deepcopy(catalogue))

    merged = _merge_unique_detail_fields(catalogue, detail)

    assert merged["explicitMods"] == catalogue["explicitMods"]
    assert merged["flavourText"] == ["The largest beings on Wraeclast", "are not flesh and blood."]
    assert {section["kind"] for section in merged["tooltipSections"]} == {"explicit", "flavour"}
    assert any(diagnostic["code"] == "UNIQUE_FLAVOUR_TEXT_FROM_DETAIL_PAGE" for diagnostic in merged["diagnostics"])


def test_unique_detail_snapshot_lookup_uses_checked_in_scraped_html(project_root: Path) -> None:
    paths = BuildPaths(project_root=project_root)
    candidate = UniqueGloveCandidate(
        name="Treefingers",
        baseType="Riveted Mitts",
        sourceUrl="https://poe2db.tw/us/Treefingers",
        label="Treefingers Riveted Mitts",
    )

    snapshot_path = _snapshot_detail_path_for_unique(candidate, paths, item_class="Gloves")

    assert snapshot_path is not None
    assert snapshot_path.name == "treefingers.html"


def test_unique_detail_hydration_reads_dom_flavour_when_trade_json_omits_it() -> None:
    from poe2db_scraper.builder import _unique_detail_hydration_from_html

    html = '''
    <html><body>
      <div class="newItemPopup uniquePopup">
        <div class="Stats">
          <div class="FlavourText">"Those who dance are considered insane<br/>by those who cannot hear the music."<br/>- Atziri, Queen of the Vaal</div>
        </div>
      </div>
    </body></html>
    '''
    detail = _unique_detail_hydration_from_html(
        "https://poe2db.tw/us/Atziris_Step",
        html,
        item_class="Boots",
        expected_base_type="Cinched Boots",
        fallback={"name": "Atziri's Step", "baseType": "Cinched Boots"},
    )

    assert detail["flavourText"] == [
        '"Those who dance are considered insane',
        'by those who cannot hear the music."',
        "- Atziri, Queen of the Vaal",
    ]
    assert any(diagnostic["code"] == "UNIQUE_DETAIL_LIGHTWEIGHT_HYDRATION" for diagnostic in detail["diagnostics"])


def test_unique_detail_hydration_marks_coming_soon_flavour_as_unpublished_placeholder() -> None:
    from poe2db_scraper.builder import _unique_detail_hydration_from_html

    html = '''
    <html><body>
      <div class="newItemPopup uniquePopup">
        <div class="Stats">
          <div class="FlavourText">Coming soon</div>
        </div>
      </div>
    </body></html>
    '''
    detail = _unique_detail_hydration_from_html(
        "https://poe2db.tw/us/Tabula_Rasa",
        html,
        item_class="Body Armours",
        expected_base_type="Garment",
        fallback={"name": "Tabula Rasa", "baseType": "Garment"},
    )

    assert detail["flavourText"] == []
    assert any(diagnostic["code"] == "UNIQUE_FLAVOUR_TEXT_NOT_PUBLISHED" for diagnostic in detail["diagnostics"])
