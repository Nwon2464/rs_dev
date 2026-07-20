from __future__ import annotations

import csv
import json
from pathlib import Path

from rs_dev.open_options.catalogs.pipeline import (
    DEFAULT_DATA_DIR as CATALOG_DATA_DIR,
    DEFAULT_LLT as CATALOG_LLT,
)
from rs_dev.open_options.general.pipeline import DEFAULT_DATA_DIR as GENERAL_DATA_DIR
from rs_dev.open_options.instandard.pipeline import (
    DEFAULT_DATA_DIR as INSTANDARD_DATA_DIR,
)
from rs_dev.open_options.locales.pipeline import (
    DEFAULT_DATA_DIR as LOCALE_DATA_DIR,
    DEFAULT_LLT as LOCALE_LLT,
)


ROOT = Path(__file__).resolve().parents[1]


def test_all_web_data_builders_default_to_after_snapshot() -> None:
    after = ROOT / "after"
    assert {
        GENERAL_DATA_DIR,
        INSTANDARD_DATA_DIR,
        LOCALE_DATA_DIR,
        CATALOG_DATA_DIR,
    } == {after}
    assert {LOCALE_LLT, CATALOG_LLT} == {after / "language/japanese.llt"}


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


def test_catalog_audits_are_rebuilt_under_reports() -> None:
    report_root = ROOT / "data/reports/open_options/catalogs/ja"
    for name in (
        "equipment_groups_audit.json",
        "open_equipment_buckets_audit.json",
        "open_metadata_audit.json",
    ):
        payload = json.loads((report_root / name).read_text(encoding="utf-8"))
        assert payload["summary"]["production_export_eligible"] is True

    assert not (ROOT / "data/processed/i18n/ja").exists()


def test_option_tag_audit_has_complete_evidence() -> None:
    payload = json.loads(
        (
            ROOT
            / "data/reports/open_options/catalogs/option_tags_audit.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["summary"]["option_count"] == 132
    assert payload["summary"]["untagged_count"] == 0
    assert payload["summary"]["untagged_option_ids"] == []
    for option in payload["options"].values():
        assert option["canonical_tags"]
        assert set(option["canonical_tags"]) == set(option["evidence"])
        assert all(option["evidence"][tag] for tag in option["canonical_tags"])
