#!/usr/bin/env python3
"""Audit and conditionally export Japanese OpenViewer equipment buckets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.japanese_open_equipment_buckets import (
    DEFAULT_AUDIT_OUTPUT,
    DEFAULT_PRODUCTION_OUTPUT,
    build_japanese_open_bucket_audit,
    build_production_open_buckets,
    collect_csv_bucket_counts,
    load_equipment_group_names,
    write_json,
)
from rs_dev.parsers import parse_item_groups, parse_japanese_llt


DEFAULT_LLT = Path("/mnt/c/game/Red Stone/Data/language/japanese.llt")
DEFAULT_SIMPLE_GAME_TEXT = Path("/mnt/c/game/Red Stone/Data/simpleGameText.dat")
DEFAULT_EQUIPMENT_GROUPS = (
    ROOT / "data/processed/open_options/catalogs/equipment_groups.json"
)
DEFAULT_CSV = ROOT / "data/processed/open_options/general/open_option_rows.csv"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llt", type=Path, default=DEFAULT_LLT)
    parser.add_argument(
        "--simple-game-text", type=Path, default=DEFAULT_SIMPLE_GAME_TEXT
    )
    parser.add_argument(
        "--equipment-groups", type=Path, default=DEFAULT_EQUIPMENT_GROUPS
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT_OUTPUT)
    parser.add_argument(
        "--production-output", type=Path, default=DEFAULT_PRODUCTION_OUTPUT
    )
    args = parser.parse_args()

    report = build_japanese_open_bucket_audit(
        parse_japanese_llt(args.llt),
        parse_item_groups(args.simple_game_text, expected_count=84),
        load_equipment_group_names(args.equipment_groups),
        collect_csv_bucket_counts(args.csv),
        japanese_llt_source=str(args.llt),
        equipment_groups_source=str(args.equipment_groups),
        csv_source=str(args.csv),
    )
    write_json(args.audit_output, report.model_dump(mode="json"))
    summary = report.summary
    print(f"actual buckets: {summary.actual_bucket_count}")
    print(
        "strategies: "
        f"direct={summary.direct_single_group_count}, "
        f"composite={summary.composable_multi_group_count}, "
        f"semantic={summary.semantic_category_count}"
    )
    print(
        "statuses: "
        f"confirmed={summary.confirmed_count}, "
        f"candidate={summary.strong_candidate_count}, "
        f"ambiguous={summary.ambiguous_count}, missing={summary.missing_count}"
    )
    print(f"audit: {args.audit_output}")
    if summary.production_export_eligible:
        mapping = build_production_open_buckets(report)
        write_json(args.production_output, mapping)
        print(f"production: {args.production_output} ({len(mapping)} buckets)")
    else:
        print(
            "production: refused ("
            + "; ".join(summary.production_export_reasons)
            + ")"
        )


if __name__ == "__main__":
    main()
