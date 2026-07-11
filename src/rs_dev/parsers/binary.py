"""Binary primitives shared by DAT parsers."""

from __future__ import annotations

import struct


def u32(data: bytes, offset: int) -> int:
    """Read one little-endian unsigned 32-bit integer."""
    return struct.unpack_from("<I", data, offset)[0]


def read_cp949_string(
    data: bytes, offset: int, *, allow_empty: bool = False
) -> tuple[str, int]:
    """Read a length-prefixed, null-terminated CP949 string."""
    if offset + 4 > len(data):
        raise ValueError(f"truncated CP949 string length at {offset:#x}")
    length = u32(data, offset)
    end = offset + 4 + length
    if end > len(data):
        raise ValueError(f"truncated CP949 string at {offset:#x}")
    if length == 0:
        if allow_empty:
            return "", end
        raise ValueError(f"empty CP949 string at {offset:#x}")
    if data[end - 1] != 0:
        raise ValueError(f"unterminated CP949 string at {offset:#x}")
    return data[offset + 4 : end - 1].decode("cp949"), end
