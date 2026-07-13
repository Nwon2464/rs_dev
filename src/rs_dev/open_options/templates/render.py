"""Render validated option templates from a value vector."""

from __future__ import annotations

import re

from .placeholders import PLACEHOLDER, placeholder_indices


def render_template(
    template: str,
    values: list[int] | tuple[int, ...],
    bindings: dict[int, int] | None = None,
) -> str:
    bindings = bindings or {}
    required = placeholder_indices(template)
    missing = [index for index in required if bindings.get(index, index) >= len(values)]
    if missing:
        raise ValueError(f"template requires unavailable value indices: {sorted(set(missing))}")

    def replace(match: re.Match[str]) -> str:
        sign, raw_index, precision, suffix = match.groups()
        source_index = bindings.get(int(raw_index), int(raw_index))
        value = values[source_index]
        digits = int(precision or 0)
        rendered = str(value) if not digits else f"{value / 10**digits:.{digits}f}"
        signed = f"{sign}{rendered}" if sign and value >= 0 else rendered
        return f"{signed}{suffix or ''}"

    rendered = PLACEHOLDER.sub(replace, template)
    if PLACEHOLDER.search(rendered):
        raise ValueError("placeholder remains after rendering")
    return rendered
