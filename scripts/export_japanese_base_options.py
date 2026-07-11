#!/usr/bin/env python3
"""Export japanese.llt section 22 for the web application."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.japanese_base_options import DEFAULT_OUTPUT, export_japanese_base_options


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llt", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    templates = export_japanese_base_options(
        args.llt,
        output_path=args.output,
    )
    print(f"wrote {len(templates)} Japanese base options to {args.output}")


if __name__ == "__main__":
    main()
