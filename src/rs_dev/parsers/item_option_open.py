"""Pure structural parser for item_option_open.dat."""

from __future__ import annotations

import struct
from pathlib import Path

from rs_dev.models.open_option_raw import OpenOptionBlock

from .binary import u32


ROWS_PER_BLOCK = 124
ROWS_PER_SLOT = 31
ROW_SIZE = 24
EXPECTED_BLOCK_COUNT = 176


def parse_item_option_open(path: Path) -> list[OpenOptionBlock]:
    data = path.read_bytes()
    blocks: list[OpenOptionBlock] = []
    cursor = 0
    block_index = 0
    while cursor < len(data):
        header_size = 32 if block_index == 0 else 8
        if cursor + header_size > len(data):
            raise ValueError(f"truncated block header at {cursor:#x}")
        section_type = u32(data, cursor + (24 if block_index == 0 else 0))
        section_group = u32(data, cursor + (28 if block_index == 0 else 4))
        rows_offset = cursor + header_size
        rows_end = rows_offset + ROWS_PER_BLOCK * ROW_SIZE
        if rows_end + 4 > len(data):
            raise ValueError(f"truncated row table in block {block_index}")

        group_count = u32(data, rows_end)
        groups_end = rows_end + 4 + group_count * 4
        if group_count > 84 or groups_end > len(data):
            raise ValueError(f"invalid group list in block {block_index}")
        group_ids = tuple(
            u32(data, rows_end + 4 + index * 4) for index in range(group_count)
        )

        rows = []
        for row_index in range(ROWS_PER_BLOCK):
            offset = rows_offset + row_index * ROW_SIZE
            raw_row = data[offset : offset + ROW_SIZE]
            if raw_row == bytes(ROW_SIZE):
                continue
            candidate_index, option_id, packed_value, float_a, float_b, tier = (
                struct.unpack("<IIIffI", raw_row)
            )
            rows.append(
                {
                    "row_index": row_index,
                    "source_file_offset": offset,
                    "candidate_index": candidate_index,
                    "option_id": option_id,
                    "packed_value": packed_value,
                    "float_a": float_a,
                    "float_b": float_b,
                    "tier": tier,
                }
            )

        blocks.append(
            OpenOptionBlock.model_validate(
                {
                    "block_index": block_index,
                    "section_type": section_type,
                    "section_group": section_group,
                    "group_ids": group_ids,
                    "rows": rows,
                }
            )
        )
        cursor = groups_end
        block_index += 1

    if cursor != len(data) or len(blocks) != EXPECTED_BLOCK_COUNT:
        raise ValueError(
            "item_option_open.dat boundary mismatch: "
            f"cursor={cursor}, size={len(data)}, blocks={len(blocks)}"
        )
    return blocks
