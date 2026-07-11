"""Strict parser for the contiguous option dictionary in capa.dat."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from .binary import read_cp949_string, u32


def _parse_record_at(
    data: bytes, offset: int, expected_id: int
) -> dict[str, Any] | None:
    if offset + 32 > len(data) or u32(data, offset) != expected_id:
        return None

    strings: list[str] = []
    cursor = offset + 32
    try:
        for index in range(3):
            text, cursor = read_cp949_string(data, cursor, allow_empty=index > 0)
            strings.append(text)
    except (UnicodeDecodeError, ValueError):
        return None

    help_text = ""
    try:
        help_text, _ = read_cp949_string(data, cursor, allow_empty=True)
    except (UnicodeDecodeError, ValueError):
        pass

    return {
        "option_id": expected_id,
        "name": strings[0],
        "description": strings[1],
        "short_text": strings[2],
        "help_text": help_text,
        "record_offset": offset,
    }


def parse_capa(path: Path) -> dict[int, dict[str, Any]]:
    """Parse capa.dat in physical, contiguous option-ID order."""
    data = path.read_bytes()
    record_count = u32(data, 0x10)
    cursor = 0x25D
    records: dict[int, dict[str, Any]] = {}

    for expected_id in range(record_count):
        needle = struct.pack("<I", expected_id)
        candidate = cursor if expected_id == 0 else data.find(needle, cursor + 33)
        record = None
        while candidate >= 0:
            record = _parse_record_at(data, candidate, expected_id)
            if record is not None:
                cursor = candidate
                break
            candidate = data.find(needle, candidate + 1)
        if record is None:
            raise ValueError(
                f"capa.dat sequential parse stopped at option_id={expected_id}"
            )
        records[expected_id] = record

    if list(records) != list(range(record_count)):
        raise ValueError("capa.dat option IDs are not contiguous from zero")
    return records
