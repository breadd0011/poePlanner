from __future__ import annotations

import html as html_lib
import json
import re
from typing import Any
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup, Tag


def clean_poe_markup(text: str | None) -> str | None:
    """Normalize PoE link markup and whitespace without doing UI-specific edits."""
    if text is None:
        return None

    text = html_lib.unescape(str(text))
    text = text.replace("\r", "")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\[([^|\]]+)\|([^\]]+)\]", r"\2", text)
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    text = text.replace("–", "—")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_display_text(text: str | None) -> str:
    """Normalize text as it should appear in a frontend tooltip."""
    clean = clean_poe_markup(text) or ""
    clean = re.sub(r"\s+([:;,])", r"\1", clean)
    clean = re.sub(r"\s+%", "%", clean)
    clean = re.sub(r"\(\s*([+-]?\d+)\s*—\s*([+-]?\d+)\s*\)", r"(\1—\2)", clean)
    clean = re.sub(r"\+\s*\(", "+(", clean)
    clean = re.sub(r"Requires:\s+", "Requires: ", clean)
    clean = re.sub(r"Stack Size:\s+", "Stack Size: ", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def clean_stat_text(text: str | None) -> str:
    """Normalize internal stat rows. Keep spaces around numeric em-dash ranges."""
    clean = clean_poe_markup(text) or ""
    clean = re.sub(r"\s+([:;,])", r"\1", clean)
    clean = re.sub(r"\s+%", "%", clean)
    clean = re.sub(r"(?<!\()\b(-?\d+)\s*—\s*(-?\d+)\b", r"\1 — \2", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def node_text(node: Tag | None, *, display: bool = True) -> str:
    if node is None:
        return ""
    text = node.get_text(" ", strip=True)
    return clean_display_text(text) if display else (clean_poe_markup(text) or "")


def node_lines(node: Tag | None) -> list[str]:
    if node is None:
        return []
    html = str(node).replace("<br/>", "\n").replace("<br>", "\n").replace("<br />", "\n")
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    return [clean_display_text(line) for line in text.splitlines() if clean_display_text(line)]


def get_page_lines_from_html(html: str) -> list[str]:
    """Return cleaned page text lines for debug and fallback parsing.

    This intentionally uses get_text("\n", strip=True) instead of stripped_strings.
    PoE2DB inline links may still split visual lines into chunks; structured tooltip
    parsing fixes that separately.
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.select("script, style"):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    lines: list[str] = []
    for raw in text.splitlines():
        line = clean_display_text(raw)
        if line:
            lines.append(line)
    return lines


def value_after_label(lines: list[str], label: str) -> str | None:
    for i, line in enumerate(lines):
        line = clean_display_text(line)
        prefix = label + " "
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            if value:
                return clean_poe_markup(value)

        if line == label and i + 1 < len(lines):
            value = clean_display_text(lines[i + 1])
            if value:
                return clean_poe_markup(value)
    return None


def slug_from_url(url: str) -> str:
    return unquote(urlparse(url).path.rstrip("/").split("/")[-1]).strip()


def title_from_url(url: str) -> str:
    return slug_from_url(url).replace("_", " ").strip()


def slice_tooltip_lines(lines: list[str], item_name: str) -> list[str]:
    start = None

    for i, line in enumerate(lines):
        if clean_display_text(line) == item_name:
            start = i
            break

    if start is None:
        return []

    end = len(lines)
    for i in range(start + 1, len(lines)):
        line = clean_display_text(lines[i])
        if line.startswith("##### "):
            end = i
            break
        if "Show Full Descriptions" in line:
            end = i
            break
        if line == "Edit":
            end = i
            break
        # In raw BeautifulSoup text the card header is not prefixed with #####.
        if line.endswith(" Attr /5") or re.search(r" /\d+$", line):
            if line != item_name:
                end = i
                break

    return [clean_display_text(x) for x in lines[start:end] if clean_display_text(x)]


def extract_trade_json_if_present(html_text: str) -> dict[str, Any] | None:
    markers = ['"realm": "poe2"', '"realm":"poe2"']
    start_marker = -1
    for marker in markers:
        start_marker = html_text.find(marker)
        if start_marker != -1:
            break
    if start_marker == -1:
        return None

    start = html_text.rfind("{", 0, start_marker)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(html_text)):
        ch = html_text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                raw = html_lib.unescape(html_text[start : i + 1])
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return None
    return None


def to_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    raw = str(value).strip()
    return int(raw) if re.fullmatch(r"-?\d+", raw) else None


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def without_empty(lines: list[str]) -> list[str]:
    return [line for line in lines if line.strip()]
