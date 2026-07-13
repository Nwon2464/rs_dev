"""Merge already validated converter rows without changing their values."""

from __future__ import annotations

from rs_dev.models.general_open_option import GeneralOpenOptionRow
from rs_dev.open_options.common.validation import duplicate_row_keys


IDENTITY_FIELDS = (
    "converter_type",
    "source_block_index",
    "open_slot",
    "candidate_index",
    "option_id",
)


def merge_general_rows(
    converter_rows: list[list[GeneralOpenOptionRow]],
) -> list[GeneralOpenOptionRow]:
    merged = [row for rows in converter_rows for row in rows]
    duplicates = duplicate_row_keys(
        (row.model_dump() for row in merged), IDENTITY_FIELDS
    )
    if duplicates:
        raise ValueError(f"duplicate general open-option rows: {duplicates[:5]}")
    return merged
