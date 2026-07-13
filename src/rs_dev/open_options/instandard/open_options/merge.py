"""Merge four non-standard converter views."""

from __future__ import annotations

from rs_dev.models.instandard_open_option import InstandardOpenOptionRow
from rs_dev.open_options.common.validation import duplicate_row_keys


def merge_instandard_open_rows(
    converter_rows: list[list[InstandardOpenOptionRow]],
) -> list[InstandardOpenOptionRow]:
    rows = [row for group in converter_rows for row in group]
    duplicates = duplicate_row_keys(
        (row.model_dump() for row in rows),
        ("converter_type", "item_group_id", "source_block_index", "source_file_offset"),
    )
    if duplicates:
        raise ValueError(f"duplicate non-standard open rows: {duplicates[:5]}")
    return sorted(
        rows,
        key=lambda row: (
            row.item_group_id,
            ("normal", "improved", "fake", "burning").index(row.converter_type),
            row.open_slot,
            row.candidate_index,
        ),
    )
