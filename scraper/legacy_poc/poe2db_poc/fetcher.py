from __future__ import annotations

import hashlib
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

CACHE_DIR = Path('.cache/poe2db')
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    'User-Agent': 'poe2-planner-data-poc/0.4 contact: local-dev'
}


def cache_path_for_url(url: str) -> Path:
    digest = hashlib.sha256(url.encode('utf-8')).hexdigest()
    return CACHE_DIR / f'{digest}.html'


def fetch_html(url: str, *, force_refresh: bool = False, delay_seconds: float = 0.75) -> str:
    path = cache_path_for_url(url)

    if path.exists() and not force_refresh:
        return path.read_text(encoding='utf-8')

    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    html = response.text

    path.write_text(html, encoding='utf-8')
    time.sleep(delay_seconds)
    return html


def soup_from_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, 'lxml')


def lines_from_html(html: str) -> list[str]:
    soup = soup_from_html(html)
    return [
        line.strip()
        for line in soup.get_text('\n', strip=True).splitlines()
        if line.strip()
    ]
