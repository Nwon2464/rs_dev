#!/usr/bin/env python3
"""CLI for collecting non-standard equipment data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.instandard_options import (
    DEFAULT_CSV,
    DEFAULT_DATA_DIR,
    DEFAULT_JSON,
    DEFAULT_MARKDOWN,
    DEFAULT_RENDER_CSV,
    run_pipeline,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--render-csv", type=Path, default=DEFAULT_RENDER_CSV)
    args = parser.parse_args()

    summary = run_pipeline(
        data_dir=args.data_dir,
        markdown_path=args.markdown,
        json_path=args.json,
        csv_path=args.csv,
        render_csv_path=args.render_csv,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
