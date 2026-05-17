from __future__ import annotations

import io

from poe2db_scraper.console import color_enabled, configure_color, heading, paint, status


def test_color_auto_does_not_emit_ansi_for_non_tty_stream():
    configure_color("auto")
    stream = io.StringIO()

    assert color_enabled(stream) is False
    assert paint("OK", "ok", stream=stream) == "OK"


def test_color_always_wraps_status_text():
    configure_color("always")
    try:
        rendered = status("OK")
        assert "\x1b[" in rendered
        assert rendered.endswith("\x1b[0m")
    finally:
        configure_color("auto")


def test_heading_respects_never_mode():
    configure_color("never")
    try:
        assert heading("Payload") == "Payload"
    finally:
        configure_color("auto")
