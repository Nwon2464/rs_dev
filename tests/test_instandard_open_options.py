from __future__ import annotations

import csv
import json
from pathlib import Path

from rs_dev.models.instandard_equipment import InstandardCatalog
from rs_dev.models.instandard_open_option import InstandardOpenOptionRow


ROOT = Path(__file__).resolve().parents[1]


def _rows() -> list[InstandardOpenOptionRow]:
    with (ROOT / "data/processed/open_options/instandard/open_option_rows.csv").open(encoding="utf-8-sig", newline="") as handle:
        return [InstandardOpenOptionRow.model_validate(row) for row in csv.DictReader(handle)]


def test_normalized_catalog_preserves_assignments_and_tiers() -> None:
    catalog = InstandardCatalog.model_validate_json(
        (ROOT / "data/processed/open_options/instandard/catalog.json").read_text(encoding="utf-8")
    )
    assert len(catalog.equipment) == 34
    assert len(catalog.options) == 80
    necklace = next(item for item in catalog.equipment if item.item_group_id == 8)
    assert necklace.option_ids[-2:] == [1045, 922]
    assert necklace.supplemental_option_ids == [1045, 922]
    tiers = [tier for option in catalog.options for tier in option.tiers]
    assert sum(len(tier.rolls) for tier in tiers if tier.enabled) == 7640
    assert sum(len(tier.rolls) for tier in tiers if not tier.enabled) == 360
    assert catalog.value_bindings == {"922": {"1": 0}, "1045": {"1": 0}}


def test_four_converter_views_match_migration_baseline() -> None:
    rows = _rows()
    assert len(rows) == 12202
    assert {row.converter_type for row in rows} == {"normal", "improved", "fake", "burning"}
    report = json.loads((ROOT / "data/reports/open_options/instandard/converter_validation.json").read_text(encoding="utf-8"))
    assert report["migration_comparison"]["matches"] is True
    assert report["probability_anomalies"] == []


def test_updated_open_option_rows_are_renderable() -> None:
    rows = _rows()
    helmet_burning = [
        row
        for row in rows
        if row.item_group_id == 1
        and row.converter_type == "burning"
        and row.open_slot == 4
    ]
    assert [
        (row.candidate_index, row.option_id, row.value_0, row.tier)
        for row in helmet_burning[-4:]
    ] == [
        (24, 723, 13, 4),
        (25, 754, 5, 2),
        (26, 754, 6, 3),
        (27, 754, 8, 4),
    ]
    assert abs(sum(float(row.probability) for row in helmet_burning) - 100) <= 0.06

    crown_fake = [
        row
        for row in rows
        if row.item_group_id == 29
        and row.converter_type == "fake"
        and row.open_slot == 4
        and row.candidate_index == 20
    ]
    assert [(row.option_id, row.value_0, row.tier) for row in crown_fake] == [
        (688, 14, 2),
    ]


def test_screen_confirmed_cannon_rows_are_preserved() -> None:
    cannon = [row for row in _rows() if row.item_group_id == 82 and row.converter_type == "burning"]
    for slot, candidate, option_id, value_0 in (
        (1, 15, 736, 300), (2, 13, 623, 25), (3, 1, 623, 20), (4, 17, 464, 20),
    ):
        assert any(row.open_slot == slot and row.candidate_index == candidate and row.option_id == option_id and row.value_0 == value_0 for row in cannon)
