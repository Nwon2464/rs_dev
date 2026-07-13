from __future__ import annotations

from pathlib import Path

import pytest

from rs_dev.models.general_open_option import GeneralOpenOptionRow
from rs_dev.open_options.common.value_unpacking import unpack_packed_value
from rs_dev.parsers import parse_capa, parse_item_option_open, read_cp949_string, u32


ROOT = Path(__file__).resolve().parents[1]


def test_binary_primitives_parse_u32_and_cp949() -> None:
    encoded = "장비".encode("cp949") + b"\x00"
    data = len(encoded).to_bytes(4, "little") + encoded
    assert u32(b"\x78\x56\x34\x12", 0) == 0x12345678
    assert read_cp949_string(data, 0) == ("장비", len(data))


@pytest.mark.parametrize(
    "data, message",
    [
        (b"\x01\x00", "truncated CP949 string length"),
        (b"\x02\x00\x00\x00A", "truncated CP949 string"),
        (b"\x01\x00\x00\x00A", "unterminated CP949 string"),
    ],
)
def test_cp949_parser_rejects_invalid_boundaries(data: bytes, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        read_cp949_string(data, 0)


def test_capa_parser_returns_contiguous_known_records() -> None:
    records = parse_capa(ROOT / "data/raw/capa.dat")
    assert list(records) == list(range(len(records)))
    assert records[63]["name"] == "힘상승"


def test_pure_item_option_parser_preserves_raw_axes() -> None:
    blocks = parse_item_option_open(ROOT / "data/raw/item_option_open.dat")
    assert len(blocks) == 176
    assert sum(len(block.rows) for block in blocks) == 7749
    assert {block.section_type for block in blocks} >= {7, 8, 9, 11}
    row = blocks[0].rows[0]
    assert row.float_a == 7
    assert row.float_b == 7
    assert unpack_packed_value(row.packed_value) == (120, 0)


def test_general_row_schema_contains_no_display_fields() -> None:
    fields = set(GeneralOpenOptionRow.model_fields)
    assert {"option_name", "option_display", "grade_name"}.isdisjoint(fields)
    assert fields == {
        "converter_type", "equipment_bucket", "group_ids", "group_names",
        "grade_code", "section_group", "open_slot", "candidate_index",
        "option_id", "value_0", "value_1", "probability",
        "probability_source", "tier", "source_block_index", "source_file_offset",
    }
