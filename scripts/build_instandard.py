#!/usr/bin/env python3
"""Build normalized non-standard equipment data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.open_options.instandard.pipeline import DEFAULT_DATA_DIR, build_instandard  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()
    print(json.dumps(build_instandard(data_dir=args.data_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
