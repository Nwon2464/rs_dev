from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_general_migration_baseline_and_association_audit() -> None:
    report = json.loads((ROOT / "data/reports/open_options/general/converter_validation.json").read_text(encoding="utf-8"))
    assert report["migration_comparison"]["matches"] is True
    assert report["migration_comparison"]["current"]["row_count"] == 8008
    assert report["converter_validation"]["association"]["row_count"] == 735
    assert report["association_probability_axes"] == {
        "checked_row_count": 735,
        "float_a_float_b_equal": True,
        "mismatches": [],
    }


def test_final_general_schema_and_converter_counts() -> None:
    path = ROOT / "data/processed/open_options/general/open_option_rows.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == [
        "converter_type", "equipment_bucket", "group_ids", "group_names",
        "grade_code", "section_group", "open_slot", "candidate_index",
        "option_id", "value_0", "value_1", "probability",
        "probability_source", "tier", "source_block_index", "source_file_offset",
    ]
    assert len(rows) == 8008
    assert {row["converter_type"] for row in rows} == {"normal", "improved", "fake", "burning", "association"}


def test_web_public_outputs_equal_processed_outputs() -> None:
    paths = [
        "general/open_option_rows.csv",
        "instandard/catalog.json",
        "instandard/open_option_rows.csv",
        "i18n/ko/base_options.json",
        "i18n/ja/base_options.json",
        "catalogs/option_tags.json",
        "catalogs/equipment_groups.json",
        "catalogs/open_equipment_buckets.json",
        "catalogs/open_metadata.json",
    ]
    for relative in paths:
        assert (ROOT / "data/processed/open_options" / relative).read_bytes() == (ROOT / "web/public/data/open_options" / relative).read_bytes()
