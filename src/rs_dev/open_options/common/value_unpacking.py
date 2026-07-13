"""Decode the two unsigned 16-bit option values stored in one integer."""

from __future__ import annotations


def unpack_packed_value(packed_value: int) -> tuple[int, int]:
    if not 0 <= packed_value <= 0xFFFFFFFF:
        raise ValueError("packed option value must fit in 32 bits")
    return packed_value & 0xFFFF, packed_value >> 16
