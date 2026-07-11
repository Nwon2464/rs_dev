from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from rs_dev import instandard_options as instandard_collector
from rs_dev import open_options as open_collector
from rs_dev.models import (
    InstandardDataset,
    InstandardRenderRow,
    InstandardTierCsvRow,
    OpenOptionOutputRow,
)
from rs_dev.parsers import parse_capa, read_cp949_string, u32


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
    assert records[63]["option_id"] == 63
    assert records[63]["name"] == "힘상승"


def test_open_option_binary_parse_result_is_model_validated() -> None:
    blocks = open_collector.parse_blocks(ROOT / "data/raw/item_option_open.dat")
    assert len(blocks) == 176
    assert sum(len(block["rows"]) for block in blocks) == 7749
    assert {block["section_type"] for block in blocks} >= {7, 8, 9, 11}


def test_instandard_weapon_burning_slot4_section_type_11_is_preserved() -> None:
    path = open_collector.DEFAULT_DATA_DIR / "item_option_open.dat"
    if not path.is_file():
        pytest.skip(f"local DAT is unavailable: {path}")

    weapon_group_ids = (
        18,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        28,
        30,
        32,
        33,
        54,
        55,
        56,
        57,
        58,
        61,
        63,
        68,
        70,
        80,
        82,
    )
    matches = [
        block
        for block in open_collector.parse_blocks(path)
        if block["section_type"] == 11
        and block["section_group"] == 3
        and block["group_ids"] == weapon_group_ids
    ]
    assert len(matches) == 1

    slot4 = [
        row for row in matches[0]["rows"] if row["row_index"] // 31 + 1 == 4
    ]
    assert len(slot4) == 30
    assert [row["candidate_index"] for row in slot4] == list(range(1, 31))

    expected = (
        (460, (127, 152, 182)),
        (201, (60, 70, 80)),
        (704, (5, 6, 7)),
        (706, (7, 8, 9)),
        (724, (14, 18, 22)),
        (464, (17, 20, 23)),
        (752, (12, 14, 16)),
        (754, (6, 8, 10)),
        (755, (80, 96, 115)),
        (472, (40, 45, 50)),
    )
    for index, (option_id, values) in enumerate(expected):
        rows = slot4[index * 3 : index * 3 + 3]
        assert tuple(row["option_id"] for row in rows) == (option_id,) * 3
        assert tuple(row["packed_value"] & 0xFFFF for row in rows) == values
        assert tuple(row["packed_value"] >> 16 for row in rows) == (0, 0, 0)
        assert tuple(row["normal"] for row in rows) == pytest.approx((8, 1.5, 0.5))
        assert tuple(row["improved"] for row in rows) == (0, 0, 0)
        assert tuple(row["tier"] for row in rows) == (3, 4, 5)


def test_display_value_transformations() -> None:
    option = {
        "name": "테스트",
        "short_text": "공격력 +[0], 속도 [1.1%]",
        "description": "",
    }
    assert open_collector.option_display(option, 15, 123) == (
        2,
        "공격력 +15, 속도 12.3%",
    )
    assert (
        instandard_collector.render_option_value("저항 [0.1％]", [125, 0, 0])
        == "저항 12.5％"
    )


@pytest.mark.parametrize("option_id", [922, 1045])
def test_supplemental_display_template_reuses_primary_value(option_id: int) -> None:
    template = "최소 [0], 최대 [1], 확률 [1.1%]"
    assert instandard_collector.display_template(option_id, template) == (
        "최소 [0], 최대 [0], 확률 [0.1%]"
    )


def test_probability_validation_and_model_bounds() -> None:
    rows = [
        {"row_index": 0, "normal": 40.0, "improved": 0.0},
        {"row_index": 1, "normal": 60.0, "improved": 0.0},
    ]
    validity = open_collector.probability_validity(rows)
    assert validity[1] is True
    assert validity[2] is False

    valid = {
        "equipment_bucket": "헬멧",
        "item_group_ids": "0",
        "item_group_names": "헬멧",
        "grade_code": 7,
        "grade_name": "유니크",
        "section_group": 0,
        "open_slot": 1,
        "candidate_index": 1,
        "option_id": 63,
        "option_name": "힘상승",
        "option_value_arity": 1,
        "option_display": "힘 +1",
        "value_raw": 1,
        "value_0_low16": 1,
        "value_1_high16": 0,
        "normal_probability": "101",
        "improved_probability": "0",
        "option_tier": 1,
        "probability_sum_valid": "false",
        "source_file_name": "item_option_open.dat",
        "source_block_index": 0,
        "source_file_offset": "0x20",
        "mapping_basis": "test",
        "mapping_confidence": "test",
    }
    with pytest.raises(ValidationError, match="probability must be between 0 and 100"):
        OpenOptionOutputRow.model_validate(valid)


def test_supplemental_options_are_validated_on_necklace() -> None:
    dataset = json.loads(
        (ROOT / "data/processed/instandard_equipment.json").read_text(
            encoding="utf-8"
        )
    )
    InstandardDataset.model_validate(dataset)

    invalid = deepcopy(dataset)
    necklace = next(item for item in invalid["equipment"] if item["item_group_id"] == 8)
    necklace["supplemental_option_ids"].remove(922)
    with pytest.raises(ValidationError, match="must be 922 and 1045"):
        InstandardDataset.model_validate(invalid)


def test_output_model_field_order_matches_frozen_csv_schemas() -> None:
    expectations = {
        "data/processed/equipment_converter_type_options.csv": OpenOptionOutputRow,
        "data/processed/instandard_equipment_tiers.csv": InstandardTierCsvRow,
        "data/processed/instandard_equipment_render_rows.csv": InstandardRenderRow,
    }
    for relative_path, model in expectations.items():
        with (ROOT / relative_path).open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            header = reader.fieldnames
            rows = list(reader)
        assert header == list(model.model_fields)
        for row in rows:
            model.model_validate(row)
