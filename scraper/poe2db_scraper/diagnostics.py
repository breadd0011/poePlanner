from __future__ import annotations

from typing import Any, Literal

Severity = Literal["info", "warning", "error"]


def diagnostic(
    *,
    code: str,
    message: str,
    severity: Severity = "info",
    action_required: bool = False,
    **context: Any,
) -> dict[str, Any]:
    """Create the canonical diagnostic/warning shape used across reports."""
    result: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
        "actionRequired": action_required,
    }
    for key, value in context.items():
        if value is not None:
            result[key] = value
    return result


def info(*, code: str, message: str, action_required: bool = False, **context: Any) -> dict[str, Any]:
    return diagnostic(code=code, message=message, severity="info", action_required=action_required, **context)


def warning(*, code: str, message: str, action_required: bool = False, **context: Any) -> dict[str, Any]:
    return diagnostic(code=code, message=message, severity="warning", action_required=action_required, **context)


def error(*, code: str, message: str, action_required: bool = True, **context: Any) -> dict[str, Any]:
    return diagnostic(code=code, message=message, severity="error", action_required=action_required, **context)


def normalise_diagnostic(value: Any, *, default_code: str = "diagnostic") -> dict[str, Any]:
    """Coerce legacy string or partial dict warnings into the canonical shape."""
    if isinstance(value, dict):
        severity = str(value.get("severity") or "warning")
        if severity not in {"info", "warning", "error"}:
            severity = "warning"
        code = str(value.get("code") or default_code)
        message = str(value.get("message") or code)
        action_required = bool(value.get("actionRequired") or severity == "error")
        context = {k: v for k, v in value.items() if k not in {"severity", "code", "message", "actionRequired"}}
        return diagnostic(
            code=code,
            message=message,
            severity=severity,  # type: ignore[arg-type]
            action_required=action_required,
            **context,
        )
    return warning(code=default_code, message=str(value))


def normalise_diagnostics(values: list[Any] | tuple[Any, ...] | None, *, default_code: str = "diagnostic") -> list[dict[str, Any]]:
    return [normalise_diagnostic(value, default_code=default_code) for value in (values or [])]
