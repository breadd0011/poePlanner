from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .fetcher import FetchedPage, fetch_html
from .schema import BuildPaths


@dataclass(frozen=True)
class BuildOptions:
    """Controls scraper fallback and write-side-effect policy for a payload build.

    Keep this policy outside of builder.py so the orchestration layer can stay
    focused on assembling data rather than deciding which fallbacks are allowed.
    """

    mode: str = "dev"
    allow_previous_output_fallbacks: bool = True
    reuse_generated_modifier_pools: bool = True
    allow_stale_cache_on_error: bool = True
    write_snapshots: bool = False
    write_modifier_html_cache: bool = False

    @classmethod
    def from_mode(
        cls,
        mode: str = "dev",
        *,
        allow_previous_output_fallbacks: bool | None = None,
        reuse_generated_modifier_pools: bool | None = None,
        allow_stale_cache_on_error: bool | None = None,
        write_snapshots: bool | None = None,
        write_modifier_html_cache: bool | None = None,
    ) -> "BuildOptions":
        normalized = str(mode or "dev").strip().lower()
        if normalized == "strict":
            options = cls(
                mode="strict",
                allow_previous_output_fallbacks=False,
                reuse_generated_modifier_pools=False,
                allow_stale_cache_on_error=False,
                write_snapshots=False,
                write_modifier_html_cache=False,
            )
        elif normalized == "dev":
            options = cls(mode="dev")
        else:
            raise ValueError(f"Unsupported build mode {mode!r}; expected 'dev' or 'strict'.")

        updates = {
            "allow_previous_output_fallbacks": allow_previous_output_fallbacks,
            "reuse_generated_modifier_pools": reuse_generated_modifier_pools,
            "allow_stale_cache_on_error": allow_stale_cache_on_error,
            "write_snapshots": write_snapshots,
            "write_modifier_html_cache": write_modifier_html_cache,
        }
        values = options.__dict__.copy()
        for key, value in updates.items():
            if value is not None:
                values[key] = value
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "allowPreviousOutputFallbacks": self.allow_previous_output_fallbacks,
            "reuseGeneratedModifierPools": self.reuse_generated_modifier_pools,
            "allowStaleCacheOnError": self.allow_stale_cache_on_error,
            "writeSnapshots": self.write_snapshots,
            "writeModifierHtmlCache": self.write_modifier_html_cache,
        }


def fetch_html_for_build(
    url: str,
    *,
    paths: BuildPaths,
    force_refresh: bool,
    options: BuildOptions,
) -> FetchedPage:
    """Fetch a page using the active build policy."""
    return fetch_html(
        url,
        cache_dir=paths.cache_dir,
        force_refresh=force_refresh,
        allow_stale_cache_on_error=options.allow_stale_cache_on_error,
    )
