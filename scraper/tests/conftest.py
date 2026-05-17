from __future__ import annotations

from pathlib import Path

import pytest

from poe2db_scraper.schema import CRUDE_CLAW_URL, DESERT_RUNE_URL, TREEFINGERS_URL

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def treefingers_html() -> str:
    return (FIXTURE_DIR / "Treefingers.html").read_text(encoding="utf-8")


@pytest.fixture
def crude_claw_html() -> str:
    return (FIXTURE_DIR / "Crude_Claw.html").read_text(encoding="utf-8")


@pytest.fixture
def desert_rune_html() -> str:
    return (FIXTURE_DIR / "Desert_Rune.html").read_text(encoding="utf-8")


@pytest.fixture
def urls() -> dict[str, str]:
    return {
        "tree": TREEFINGERS_URL,
        "claw": CRUDE_CLAW_URL,
        "rune": DESERT_RUNE_URL,
    }


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURE_DIR


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]
