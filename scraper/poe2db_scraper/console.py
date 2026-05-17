from __future__ import annotations

import os
import sys
from typing import TextIO

_COLOR_MODE = "auto"

_STYLE_CODES: dict[str, str] = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "heading": "\033[1;36m",
    "ok": "\033[32m",
    "review": "\033[33m",
    "action": "\033[1;33m",
    "error": "\033[31m",
    "warning": "\033[33m",
    "info": "\033[36m",
    "path": "\033[2m",
    "count": "\033[1m",
}

_STATUS_STYLES = {
    "ok": "ok",
    "pass": "ok",
    "passed": "ok",
    "healthy": "ok",
    "success": "ok",
    "warning": "warning",
    "warnings": "warning",
    "review": "review",
    "incomplete": "warning",
    "missing": "warning",
    "failed": "error",
    "failure": "error",
    "fail": "error",
    "error": "error",
    "errors": "error",
}


def _enable_windows_virtual_terminal() -> None:
    """Best-effort ANSI support for older Windows consoles.

    Modern Windows Terminal and PowerShell generally support ANSI already. This
    helper is intentionally silent: color should never break a scrape/build.
    """
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        return


def configure_color(mode: str = "auto") -> None:
    global _COLOR_MODE
    normalized = (mode or "auto").strip().lower()
    if normalized not in {"auto", "always", "never"}:
        normalized = "auto"
    _COLOR_MODE = normalized
    if normalized != "never":
        _enable_windows_virtual_terminal()


def color_enabled(stream: TextIO | None = None) -> bool:
    if _COLOR_MODE == "never":
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if _COLOR_MODE == "always":
        return True

    target = stream or sys.stdout
    if os.environ.get("TERM") == "dumb":
        return False
    isatty = getattr(target, "isatty", None)
    return bool(isatty and isatty())


def paint(text: object, style: str, *, stream: TextIO | None = None) -> str:
    rendered = str(text)
    code = _STYLE_CODES.get(style)
    if not code or not color_enabled(stream):
        return rendered
    return f"{code}{rendered}{_STYLE_CODES['reset']}"


def heading(text: object) -> str:
    return paint(text, "heading")


def status(text: object) -> str:
    rendered = str(text)
    style = _STATUS_STYLES.get(rendered.strip().lower())
    return paint(rendered, style or "bold")


def label(text: object, severity: str | None = None) -> str:
    normalized = (severity or str(text)).strip().lower()
    style = _STATUS_STYLES.get(normalized)
    return paint(text, style or "bold")
