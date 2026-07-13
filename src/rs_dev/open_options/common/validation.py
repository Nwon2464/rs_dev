"""Cross-row checks that are independent of converter semantics."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def duplicate_row_keys(
    rows: Iterable[Mapping[str, Any]], fields: tuple[str, ...]
) -> list[tuple[Any, ...]]:
    seen: set[tuple[Any, ...]] = set()
    duplicates: set[tuple[Any, ...]] = set()
    for row in rows:
        key = tuple(row[field] for field in fields)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return sorted(duplicates, key=str)
