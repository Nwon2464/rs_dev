"""Audit locale coverage and safe rendering for emitted option rows."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from .placeholders import placeholder_indices
from .render import render_template


def audit_locale_catalogs(
    rows: Iterable[Mapping[str, Any]],
    catalogs: Mapping[str, Mapping[int, str]],
) -> dict[str, Any]:
    materialized = list(rows)
    option_ids = sorted({int(row["option_id"]) for row in materialized})
    report: dict[str, Any] = {"option_id_count": len(option_ids), "locales": {}}
    for locale, catalog in catalogs.items():
        missing = [option_id for option_id in option_ids if option_id not in catalog]
        unsupported: list[dict[str, Any]] = []
        render_failures: list[dict[str, Any]] = []
        for row in materialized:
            option_id = int(row["option_id"])
            template = catalog.get(option_id)
            if template is None:
                continue
            indices = placeholder_indices(template)
            if any(index > 1 for index in indices):
                unsupported.append({"option_id": option_id, "indices": sorted(set(indices))})
                continue
            try:
                render_template(template, [int(row["value_0"]), int(row["value_1"])])
            except ValueError as error:
                render_failures.append({"option_id": option_id, "error": str(error)})
        report["locales"][locale] = {
            "template_count": len(catalog),
            "missing_option_ids": missing,
            "unsupported_placeholders": _unique_dicts(unsupported),
            "render_failures": _unique_dicts(render_failures),
        }
    report["valid"] = all(
        not locale_report["missing_option_ids"]
        and not locale_report["unsupported_placeholders"]
        and not locale_report["render_failures"]
        for locale_report in report["locales"].values()
    )
    return report


def audit_instandard_catalog(
    catalog: Mapping[str, Any],
    catalogs: Mapping[str, Mapping[int, str]],
    bindings: Mapping[int, Mapping[int, int]],
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for locale, locale_catalog in catalogs.items():
        missing: list[int] = []
        failures: list[dict[str, Any]] = []
        for option in catalog["options"]:
            option_id = int(option["option_id"])
            template = locale_catalog.get(option_id)
            if template is None:
                missing.append(option_id)
                continue
            option_bindings = dict(bindings.get(option_id, {}))
            try:
                for tier in option["tiers"]:
                    for values in tier["rolls"]:
                        render_template(template, values, option_bindings)
            except ValueError as error:
                failures.append({"option_id": option_id, "error": str(error)})
        results[locale] = {
            "missing_option_ids": sorted(set(missing)),
            "render_failures": _unique_dicts(failures),
        }
    return {
        "locales": results,
        "valid": all(
            not result["missing_option_ids"] and not result["render_failures"]
            for result in results.values()
        ),
    }


def _unique_dicts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(
        {
            json.dumps(row, ensure_ascii=False, sort_keys=True): row
            for row in rows
        }.values()
    )
