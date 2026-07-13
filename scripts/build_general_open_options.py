#!/usr/bin/env python3
"""Build the general-equipment open-option pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.open_options.general.pipeline import (  # noqa: E402
    DEFAULT_DATA_DIR,
    build_general_open_options,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()
    report = build_general_open_options(data_dir=args.data_dir)
    print(json.dumps(report["migration_comparison"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
