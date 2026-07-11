#!/usr/bin/env python3
"""Export section-type 11 open-option candidates for in-standard equipment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.instandard_open_options import (
    DEFAULT_DATA_DIR,
    DEFAULT_INSTANDARD_JSON,
    DEFAULT_OUTPUT,
    collect_rows,
    write_output,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--instandard-json", type=Path, default=DEFAULT_INSTANDARD_JSON
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rows, summary = collect_rows(
        data_dir=args.data_dir, instandard_json=args.instandard_json
    )
    write_output(args.output, rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
