from __future__ import annotations

import json
from pathlib import Path

import pytest

from rs_dev import instandard_open_options as collector


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def exported_rows() -> tuple[list[dict], dict[str, object]]:
    data_dir = collector.DEFAULT_DATA_DIR
    required = (
        data_dir / "item_option_open.dat",
        data_dir / "simpleGameText.dat",
        data_dir / "capa.dat",
    )
    if not all(path.is_file() for path in required):
        pytest.skip("local Red Stone DAT files are unavailable")
    return collector.collect_rows(data_dir=data_dir)


def test_all_instandard_groups_and_raw_signatures_are_covered(
    exported_rows: tuple[list[dict], dict[str, object]],
) -> None:
    rows, summary = exported_rows
    dataset = json.loads(
        collector.DEFAULT_INSTANDARD_JSON.read_text(encoding="utf-8")
    )
    expected_ids = {row["item_group_id"] for row in dataset["equipment"]}

    assert summary == {
        "equipment_group_count": 34,
        "bucket_signature_count": 10,
        "source_block_count": 30,
        "row_count": 12199,
        "invalid_probability_slot_count": 1,
    }
    assert {row["item_group_id"] for row in rows} == expected_ids
    assert len({row["bucket_group_ids"] for row in rows}) == 10
    assert {row["section_type"] for row in rows} == {11}
    assert {row["section_group"] for row in rows} == {0, 1, 3}
    assert any(row["option_id"] == 0 for row in rows)


def test_weapon_burning_screen_result_is_reproduced(
    exported_rows: tuple[list[dict], dict[str, object]],
) -> None:
    rows, _summary = exported_rows
    cannon = [
        row
        for row in rows
        if row["item_group_id"] == 82 and row["converter_type"] == "불타는"
    ]
    expected = (
        (1, 15, 736, 300),
        (2, 13, 623, 25),
        (3, 1, 623, 20),
        (4, 17, 464, 20),
    )
    for slot, candidate, option_id, value_0 in expected:
        match = next(
            row
            for row in cannon
            if row["open_slot"] == slot
            and row["candidate_index"] == candidate
        )
        assert (match["option_id"], match["value_0_low16"]) == (
            option_id,
            value_0,
        )
        assert match["mapping_status"] == "screen_confirmed"


def test_crown_burning_slot4_is_the_only_probability_anomaly(
    exported_rows: tuple[list[dict], dict[str, object]],
) -> None:
    rows, _summary = exported_rows
    invalid = {
        (
            row["item_group_id"],
            row["converter_type"],
            row["open_slot"],
            row["source_block_index"],
            row["slot_probability_sum"],
        )
        for row in rows
        if row["probability_sum_valid"] == "false"
    }
    assert invalid == {(1, "불타는", 4, 73, "88.8899989")}
    anomaly_rows = [
        row
        for row in rows
        if row["item_group_id"] == 1
        and row["converter_type"] == "불타는"
        and row["open_slot"] == 4
    ]
    assert len(anomaly_rows) == 24
    assert sum(float(row["probability"]) for row in anomaly_rows) == pytest.approx(
        88.8899989
    )
