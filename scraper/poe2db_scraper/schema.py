from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .armour_config import ARMOUR_ITEM_CLASSES, armour_class_url, armour_subtype_url
from .unique_gloves_parser import UNIQUE_ITEM_CLASS_URL_SLUGS, WEAPON_UNIQUE_CLASS_URL_SLUGS

SCHEMA_VERSION = "poc-0.21"
PARSER_VERSION = "poe2db-planner-poc-v29.0"
SOURCE_NAME = "poe2db"

TREEFINGERS_URL = "https://poe2db.tw/us/Treefingers"
CRUDE_CLAW_URL = "https://poe2db.tw/us/Crude_Claw"
DESERT_RUNE_URL = "https://poe2db.tw/us/Desert_Rune"
AUGMENT_INDEX_URL = "https://poe2db.tw/us/Augment"
GLOVES_URL = armour_class_url("Gloves")
GLOVES_STR_URL = armour_subtype_url("Gloves", "str")
GLOVES_DEX_URL = armour_subtype_url("Gloves", "dex")
GLOVES_INT_URL = armour_subtype_url("Gloves", "int")
GLOVES_STR_DEX_URL = armour_subtype_url("Gloves", "str_dex")
GLOVES_STR_INT_URL = armour_subtype_url("Gloves", "str_int")
GLOVES_DEX_INT_URL = armour_subtype_url("Gloves", "dex_int")
BOOTS_URL = armour_class_url("Boots")
BOOTS_STR_URL = armour_subtype_url("Boots", "str")
BOOTS_DEX_URL = armour_subtype_url("Boots", "dex")
BOOTS_INT_URL = armour_subtype_url("Boots", "int")
BOOTS_STR_DEX_URL = armour_subtype_url("Boots", "str_dex")
BOOTS_STR_INT_URL = armour_subtype_url("Boots", "str_int")
BOOTS_DEX_INT_URL = armour_subtype_url("Boots", "dex_int")
HELMETS_URL = armour_class_url("Helmets")
HELMETS_STR_URL = armour_subtype_url("Helmets", "str")
HELMETS_DEX_URL = armour_subtype_url("Helmets", "dex")
HELMETS_INT_URL = armour_subtype_url("Helmets", "int")
HELMETS_STR_DEX_URL = armour_subtype_url("Helmets", "str_dex")
HELMETS_STR_INT_URL = armour_subtype_url("Helmets", "str_int")
HELMETS_DEX_INT_URL = armour_subtype_url("Helmets", "dex_int")

SHIELDS_STR_URL = "https://poe2db.tw/us/Shields_str"
SHIELDS_STR_DEX_URL = "https://poe2db.tw/us/Shields_str_dex"
SHIELDS_STR_INT_URL = "https://poe2db.tw/us/Shields_str_int"
BODY_ARMOURS_STR_URL = "https://poe2db.tw/us/Body_Armours_str"
BODY_ARMOURS_DEX_URL = "https://poe2db.tw/us/Body_Armours_dex"
BODY_ARMOURS_INT_URL = "https://poe2db.tw/us/Body_Armours_int"
BODY_ARMOURS_STR_DEX_URL = "https://poe2db.tw/us/Body_Armours_str_dex"
BODY_ARMOURS_STR_INT_URL = "https://poe2db.tw/us/Body_Armours_str_int"
BODY_ARMOURS_DEX_INT_URL = "https://poe2db.tw/us/Body_Armours_dex_int"

ITEM_URLS = [TREEFINGERS_URL, CRUDE_CLAW_URL]
AUGMENT_URLS = [AUGMENT_INDEX_URL, DESERT_RUNE_URL]
CLASS_URLS = [GLOVES_URL, BOOTS_URL, HELMETS_URL]
UNIQUE_ITEM_CLASS_URLS = {item_class: f"https://poe2db.tw/us/{slug}" for item_class, slug in UNIQUE_ITEM_CLASS_URL_SLUGS.items()}
WEAPON_UNIQUE_ITEM_CLASS_URLS = {item_class: f"https://poe2db.tw/us/{slug}" for item_class, slug in WEAPON_UNIQUE_CLASS_URL_SLUGS.items()}
DEFAULT_UNIQUE_ITEM_CLASSES = tuple(ARMOUR_ITEM_CLASSES)
OPTIONAL_UNIQUE_ITEM_CLASSES = tuple(item_class for item_class in UNIQUE_ITEM_CLASS_URLS if item_class not in DEFAULT_UNIQUE_ITEM_CLASSES)
WEAPON_UNIQUE_ITEM_CLASSES = tuple(WEAPON_UNIQUE_ITEM_CLASS_URLS)
OPTIONAL_BASE_ITEM_CLASSES = tuple(dict.fromkeys([*OPTIONAL_UNIQUE_ITEM_CLASSES, *WEAPON_UNIQUE_ITEM_CLASSES]))
GLOVE_SUBTYPE_URLS = [
    GLOVES_STR_URL,
    GLOVES_DEX_URL,
    GLOVES_INT_URL,
    GLOVES_STR_DEX_URL,
    GLOVES_STR_INT_URL,
    GLOVES_DEX_INT_URL,
]
BOOT_SUBTYPE_URLS = [
    BOOTS_STR_URL,
    BOOTS_DEX_URL,
    BOOTS_INT_URL,
    BOOTS_STR_DEX_URL,
    BOOTS_STR_INT_URL,
    BOOTS_DEX_INT_URL,
]
HELMET_SUBTYPE_URLS = [
    HELMETS_STR_URL,
    HELMETS_DEX_URL,
    HELMETS_INT_URL,
    HELMETS_STR_DEX_URL,
    HELMETS_STR_INT_URL,
    HELMETS_DEX_INT_URL,
]

SHIELD_MODIFIER_SUBTYPE_URLS = [
    SHIELDS_STR_URL,
    SHIELDS_STR_DEX_URL,
    SHIELDS_STR_INT_URL,
]
BODY_ARMOUR_MODIFIER_SUBTYPE_URLS = [
    BODY_ARMOURS_STR_URL,
    BODY_ARMOURS_DEX_URL,
    BODY_ARMOURS_INT_URL,
    BODY_ARMOURS_STR_DEX_URL,
    BODY_ARMOURS_STR_INT_URL,
    BODY_ARMOURS_DEX_INT_URL,
]
SUBTYPE_URLS = GLOVE_SUBTYPE_URLS + BOOT_SUBTYPE_URLS + HELMET_SUBTYPE_URLS
TARGET_URLS = ITEM_URLS + AUGMENT_URLS + CLASS_URLS + SUBTYPE_URLS


@dataclass(frozen=True)
class BuildPaths:
    project_root: Path

    @property
    def repo_root(self) -> Path:
        return self.project_root.parent

    @property
    def web_root(self) -> Path:
        return self.repo_root / "web"

    @property
    def cache_dir(self) -> Path:
        return self.project_root / ".cache" / "poe2db"

    @property
    def snapshots_dir(self) -> Path:
        return self.project_root / "data" / "snapshots" / "poe2db"

    def snapshot_dir_for_date(self, snapshot_date: str) -> Path:
        return self.snapshots_dir / snapshot_date

    @property
    def out_dir(self) -> Path:
        return self.project_root / "out"

    @property
    def web_data_dir(self) -> Path:
        return self.web_root / "public" / "data"

    @property
    def ui_json_path(self) -> Path:
        return self.out_dir / "poe2db_poc_ui.json"

    @property
    def debug_json_path(self) -> Path:
        return self.out_dir / "poe2db_poc_debug.json"

    @property
    def diagnostics_json_path(self) -> Path:
        return self.out_dir / "poe2db_poc_diagnostics.json"

    @property
    def json_schema_path(self) -> Path:
        return self.out_dir / "poe2db_poc_schema.json"

    @property
    def web_ui_json_path(self) -> Path:
        return self.web_data_dir / "poe2db_poc_ui.json"

    @property
    def health_report_json_path(self) -> Path:
        return self.out_dir / "poe2db_payload_health_report.json"

    @property
    def web_health_report_json_path(self) -> Path:
        return self.web_data_dir / "poe2db_payload_health_report.json"

    @property
    def web_diagnostics_json_path(self) -> Path:
        return self.web_data_dir / "poe2db_poc_diagnostics.json"


    @property
    def normal_affix_snapshot_path(self) -> Path:
        return self.project_root / "data" / "modifiers_calc_gloves_int.txt"

    @property
    def normal_affix_prefix_html_path(self) -> Path:
        return self.project_root / "data" / "modifiers_calc_gloves_int_base_prefix.html"

    @property
    def normal_affix_suffix_html_path(self) -> Path:
        return self.project_root / "data" / "modifiers_calc_gloves_int_base_suffix.html"

    @property
    def normal_affix_str_dex_prefix_html_path(self) -> Path:
        return self.project_root / "data" / "modifiers_calc_gloves_str_dex_base_prefix.html"

    @property
    def normal_affix_str_dex_suffix_html_path(self) -> Path:
        return self.project_root / "data" / "modifiers_calc_gloves_str_dex_base_suffix.html"


    @property
    def modifiers_calc_full_html_dir(self) -> Path:
        return self.project_root / "data" / "modifiers_calc_full"

    def modifiers_calc_full_html_path(self, slug: str) -> Path:
        return self.modifiers_calc_full_html_dir / f"{slug}.html"
