#!/usr/bin/env python3
"""Audit japanese.llt equipment-group names and conditionally export them."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.open_options.catalogs.equipment_groups import (
    DEFAULT_AUDIT_OUTPUT,
    DEFAULT_PRODUCTION_OUTPUT,
    build_japanese_equipment_group_audit,
    build_production_equipment_groups,
    collect_current_ui_groups,
    write_json,
)
from rs_dev.parsers import parse_item_groups, parse_japanese_llt


DEFAULT_LLT = Path("/mnt/c/game/Red Stone/Data/language/japanese.llt")
DEFAULT_SIMPLE_GAME_TEXT = Path("/mnt/c/game/Red Stone/Data/simpleGameText.dat")
DEFAULT_CURRENT_UI = ROOT / "data/processed/open_options/instandard/catalog.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llt", type=Path, default=DEFAULT_LLT)
    parser.add_argument(
        "--simple-game-text", type=Path, default=DEFAULT_SIMPLE_GAME_TEXT
    )
    parser.add_argument("--current-ui", type=Path, default=DEFAULT_CURRENT_UI)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT_OUTPUT)
    parser.add_argument(
        "--production-output", type=Path, default=DEFAULT_PRODUCTION_OUTPUT
    )
    args = parser.parse_args()

    korean_groups = parse_item_groups(args.simple_game_text, expected_count=84)
    current_ui_groups = collect_current_ui_groups(args.current_ui)
    report = build_japanese_equipment_group_audit(
        parse_japanese_llt(args.llt),
        korean_groups,
        current_ui_groups,
        japanese_llt_source=str(args.llt),
        korean_group_source=str(args.simple_game_text),
        current_ui_source=str(args.current_ui),
    )
    write_json(args.audit_output, report.model_dump(mode="json"))

    summary = report.summary
    print(f"sections: {summary.section_count}")
    print(f"likely section: {report.likely_section_id}")
    print(f"Korean groups: {summary.korean_group_count}")
    print(f"current UI groups: {summary.current_ui_group_count}")
    print(
        "statuses: "
        f"confirmed={summary.confirmed_direct_id_count}, "
        f"candidate={summary.strong_structural_candidate_count}, "
        f"ambiguous={summary.ambiguous_count}, missing={summary.missing_count}"
    )
    print(f"audit: {args.audit_output}")

    if summary.production_export_eligible:
        mapping = build_production_equipment_groups(report)
        write_json(args.production_output, mapping)
        print(f"production: {args.production_output} ({len(mapping)} groups)")
    else:
        print(
            "production: refused ("
            + "; ".join(summary.production_export_reasons)
            + ")"
        )


if __name__ == "__main__":
    main()
