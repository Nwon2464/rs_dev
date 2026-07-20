"""Build the five general converter views and merge them losslessly."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rs_dev.models.general_open_option import GeneralOpenOptionRow
from rs_dev.open_options.common.csv_io import write_csv
from rs_dev.open_options.converters.specs import CONVERTER_SPECS
from rs_dev.open_options.general.export_converters import (
    FIELDNAMES,
    export_converter_rows,
    load_converter_rows,
)
from rs_dev.open_options.general.merge import merge_general_rows
from rs_dev.open_options.general.migration import (
    build_legacy_general_baseline,
    write_baseline,
)
from rs_dev.open_options.general.transform import transform_general_blocks
from rs_dev.open_options.general.validation import (
    audit_association_probability_axes,
    compare_with_baseline,
    validate_converter_rows,
    write_validation_report,
)
from rs_dev.parsers import parse_item_groups, parse_item_option_open


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = ROOT / "after"
DEFAULT_INTERMEDIATE = ROOT / "data/intermediate/open_options/general"
DEFAULT_OUTPUT = ROOT / "data/processed/open_options/general/open_option_rows.csv"
DEFAULT_LEGACY = ROOT / "data/processed/equipment_converter_type_options.csv"
DEFAULT_BASELINE = ROOT / "data/reports/open_options/general/migration_baseline.json"
DEFAULT_REPORT = ROOT / "data/reports/open_options/general/converter_validation.json"


def _load_or_create_baseline(legacy_path: Path, baseline_path: Path) -> dict[str, Any]:
    if baseline_path.is_file():
        return json.loads(baseline_path.read_text(encoding="utf-8"))
    if not legacy_path.is_file():
        raise FileNotFoundError("legacy general-open CSV is required to create migration baseline")
    baseline = build_legacy_general_baseline(legacy_path)
    write_baseline(baseline_path, baseline)
    return baseline


def build_general_open_options(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    intermediate_dir: Path = DEFAULT_INTERMEDIATE,
    output_path: Path = DEFAULT_OUTPUT,
    legacy_path: Path = DEFAULT_LEGACY,
    baseline_path: Path = DEFAULT_BASELINE,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    item_option_path = data_dir / "item_option_open.dat"
    group_path = data_dir / "simpleGameText.dat"
    missing = [str(path) for path in (item_option_path, group_path) if not path.is_file()]
    if missing:
        raise FileNotFoundError("required source file(s) missing: " + ", ".join(missing))

    baseline = _load_or_create_baseline(legacy_path, baseline_path)
    blocks = parse_item_option_open(item_option_path)
    group_names = parse_item_groups(group_path, expected_count=84)
    exported_rows: list[list[GeneralOpenOptionRow]] = []
    converter_reports: dict[str, Any] = {}
    for spec in CONVERTER_SPECS:
        rows = transform_general_blocks(blocks, group_names, spec)
        converter_reports[spec.converter_type] = validate_converter_rows(rows, spec)
        path = export_converter_rows(intermediate_dir, spec, rows)
        exported_rows.append(load_converter_rows(path))

    merged = merge_general_rows(exported_rows)
    comparison = compare_with_baseline(merged, baseline)
    if not comparison["matches"]:
        raise ValueError(f"general migration baseline mismatch: {comparison['mismatches']}")
    write_csv(output_path, FIELDNAMES, (row.model_dump() for row in merged))

    association_spec = next(
        spec for spec in CONVERTER_SPECS if spec.converter_type == "association"
    )
    report = {
        "schema_version": 1,
        "converter_validation": converter_reports,
        "association_probability_axes": audit_association_probability_axes(
            blocks, association_spec
        ),
        "migration_comparison": comparison,
        "output": str(output_path),
    }
    if not report["association_probability_axes"]["float_a_float_b_equal"]:
        raise ValueError("association float_a and float_b differ in current source data")
    write_validation_report(report_path, report)
    return report
