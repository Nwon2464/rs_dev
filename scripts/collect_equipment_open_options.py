#!/usr/bin/env python3
"""CLI for collecting equipment open-option rows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.open_options import (
    DEFAULT_DATA_DIR,
    DEFAULT_EQUIPMENT,
    DEFAULT_OUTPUT,
    run_pipeline,
    write_output,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--equipment",
        default=DEFAULT_EQUIPMENT,
        help="comma-separated equipment buckets",
    )
    parser.add_argument(
        "--grade-codes",
        default="7,8,9",
        help="comma-separated numeric grade codes",
    )
    parser.add_argument(
        "--only-improved",
        action="store_true",
        help="keep only rows with a non-zero improved-converter probability",
    )
    parser.add_argument(
        "--classify-converters",
        action="store_true",
        help="emit the four confirmed converter views with their active probability field",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="directory containing the original DAT files",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rows = run_pipeline(
        data_dir=args.data_dir,
        equipment=args.equipment,
        grade_codes=args.grade_codes,
        only_improved=args.only_improved,
        classify_converters=args.classify_converters,
    )
    write_output(args.output, rows)
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
