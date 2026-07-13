"""Parse display placeholders without depending on a locale."""

from __future__ import annotations

import re


PLACEHOLDER = re.compile(r"\[([+-]?)(\d+)(?:\.(\d+))?([%％])?\]")


def placeholder_indices(template: str) -> list[int]:
    return [int(match.group(2)) for match in PLACEHOLDER.finditer(template)]


def title_template(template: str) -> str:
    unique_indices = list(dict.fromkeys(placeholder_indices(template)))
    names = {
        index: "n" if len(unique_indices) == 1 else f"n{position + 1}"
        for position, index in enumerate(unique_indices)
    }

    def replace(match: re.Match[str]) -> str:
        sign, raw_index, _precision, suffix = match.groups()
        return f"[{sign}{names[int(raw_index)]}{suffix or ''}]"

    return PLACEHOLDER.sub(replace, template)
