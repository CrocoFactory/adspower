#!/usr/bin/env python3
"""Inspect the installed/importable adspower v3 public surface without making API calls."""

from __future__ import annotations

import inspect
import json
import sys
from typing import Any


def signature(obj: Any) -> str | None:
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return None


def methods(cls: type[Any], names: tuple[str, ...]) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for name in names:
        value = getattr(cls, name, None)
        if value is not None:
            result[name] = signature(value)
    return result


def aliases(cls: type[Any], pairs: tuple[tuple[str, str], ...]) -> dict[str, bool]:
    """Report public aliases by identity, not by source-text declarations."""
    result: dict[str, bool] = {}
    for alias, target in pairs:
        alias_value = getattr(cls, alias, None)
        target_value = getattr(cls, target, None)
        result[f"{alias}={target}"] = alias_value is not None and alias_value is target_value
    return result


def main() -> int:
    try:
        import adspower
    except Exception as exc:  # diagnostic script: report import failure cleanly
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"cannot import adspower: {type(exc).__name__}: {exc}",
                    "hint": "Run from the repository environment or install the target package first.",
                },
                indent=2,
            )
        )
        return 2

    report: dict[str, Any] = {
        "ok": True,
        "version": getattr(adspower, "__version__", None),
        "module": getattr(adspower, "__file__", None),
        "clients": {},
        "browser_resource": {},
        "browser_aliases": {},
        "sessions": {},
        "notes": [],
    }

    sync_client = getattr(adspower, "AdsPowerClient", None)
    async_client = getattr(adspower, "AsyncAdsPowerClient", None)

    if sync_client is not None:
        report["clients"]["AdsPowerClient"] = signature(sync_client)
    if async_client is not None:
        report["clients"]["AsyncAdsPowerClient"] = signature(async_client)

    try:
        from adspower.resources import AsyncBrowsersResource, BrowsersResource

        browser_method_names = (
            "start",
            "session",
            "stop",
            "stop_all",
            "status",
            "list_opened",
            "cloud_status",
        )
        report["browser_resource"]["BrowsersResource"] = methods(
            BrowsersResource, browser_method_names
        )
        report["browser_resource"]["AsyncBrowsersResource"] = methods(
            AsyncBrowsersResource, browser_method_names
        )
        report["browser_aliases"]["BrowsersResource"] = aliases(
            BrowsersResource, (("session", "start"),)
        )
        report["browser_aliases"]["AsyncBrowsersResource"] = aliases(
            AsyncBrowsersResource, (("session", "start"),)
        )
    except Exception as exc:
        report["browser_resource"]["error"] = f"{type(exc).__name__}: {exc}"

    for name in ("BrowserSession", "AsyncBrowserSession"):
        cls = getattr(adspower, name, None)
        if cls is None:
            continue
        report["sessions"][name] = methods(
            cls,
            ("stop", "selenium", "playwright", "__enter__", "__aenter__"),
        )

    sync_aliases = report["browser_aliases"].get("BrowsersResource", {})
    if isinstance(sync_aliases, dict):
        if sync_aliases.get("session=start"):
            report["notes"].append(
                "browsers.session(...) is a supported public alias of browsers.start(...)."
            )
        else:
            report["notes"].append(
                "browsers.session(...) is not an identity alias of browsers.start(...); inspect both signatures before choosing one."
            )

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
