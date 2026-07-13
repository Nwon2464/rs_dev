"""Build the Korean option-template catalog from capa.dat."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rs_dev.open_options.templates.normalize import normalize_template


def build_korean_catalog(capa: Mapping[int, Mapping[str, Any]]) -> dict[int, str]:
    catalog: dict[int, str] = {}
    for option_id, option in capa.items():
        template = normalize_template(
            str(option.get("short_text") or option.get("description") or "")
        )
        if template:
            catalog[option_id] = template
    return catalog
