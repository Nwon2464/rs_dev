#!/usr/bin/env python3
"""Audit and conditionally export Japanese open-option metadata."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.japanese_open_metadata import (
    DEFAULT_AUDIT_OUTPUT, DEFAULT_PRODUCTION_OUTPUT,
    build_japanese_open_metadata_audit, build_production_open_metadata,
    collect_current_ui_values, collect_usage, write_json,
)
from rs_dev.parsers import parse_japanese_llt

DEFAULT_LLT = Path("/mnt/c/game/Red Stone/Data/language/japanese.llt")
DEFAULT_GENERAL_CSV = ROOT / "web/public/data/equipment_converter_type_options.csv"
DEFAULT_INSTANDARD_CSV = ROOT / "web/public/data/instandard_open_option_rows.csv"
DEFAULT_UI = ROOT / "web/src/i18n/index.ts"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llt", type=Path, default=DEFAULT_LLT)
    parser.add_argument("--general-csv", type=Path, default=DEFAULT_GENERAL_CSV)
    parser.add_argument("--instandard-csv", type=Path, default=DEFAULT_INSTANDARD_CSV)
    parser.add_argument("--current-ui", type=Path, default=DEFAULT_UI)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT_OUTPUT)
    parser.add_argument("--production-output", type=Path, default=DEFAULT_PRODUCTION_OUTPUT)
    args = parser.parse_args()
    grade_sets, converters = collect_usage(args.general_csv, args.instandard_csv)
    report = build_japanese_open_metadata_audit(
        parse_japanese_llt(args.llt), grade_sets["grades"], converters["general"],
        converters["instandard"], collect_current_ui_values(args.current_ui),
        japanese_llt_source=str(args.llt), general_csv_source=str(args.general_csv),
        instandard_csv_source=str(args.instandard_csv), current_ui_source=str(args.current_ui),
    )
    write_json(args.audit_output, report.model_dump(mode="json"))
    print(f"sections: {report.summary.section_count}")
    print(f"confirmed={report.summary.confirmed_count}, candidate={report.summary.strong_candidate_count}, ambiguous={report.summary.ambiguous_count}, missing={report.summary.missing_count}")
    print(f"audit: {args.audit_output}")
    if report.summary.production_export_eligible:
        payload = build_production_open_metadata(report)
        write_json(args.production_output, payload)
        print(f"production: {args.production_output}")
    else:
        print("production: refused (" + "; ".join(report.summary.production_export_reasons) + ")")


if __name__ == "__main__":
    main()
