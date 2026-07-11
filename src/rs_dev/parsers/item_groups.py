"""Parser for the item-group dictionary in simpleGameText.dat."""

from __future__ import annotations

from pathlib import Path

from .binary import read_cp949_string, u32


def parse_item_groups(
    path: Path, *, expected_count: int | None = None
) -> dict[int, str]:
    data = path.read_bytes()
    count = u32(data, 0x78F)
    if expected_count is not None and count != expected_count:
        raise ValueError(
            f"expected {expected_count} item groups at 0x78f, found {count}"
        )

    cursor = 0x793
    groups: dict[int, str] = {}
    for expected_id in range(count):
        group_id = u32(data, cursor)
        if group_id != expected_id:
            raise ValueError(
                f"item group sequence mismatch at {cursor:#x}: "
                f"expected {expected_id}, found {group_id}"
            )
        name, cursor = read_cp949_string(data, cursor + 4)
        groups[group_id] = name
    return groups
