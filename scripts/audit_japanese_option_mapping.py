#!/usr/bin/env python3
"""Audit current non-standard option IDs against japanese.llt section 22."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.japanese_option_audit import (
    DEFAULT_CURRENT_OPTIONS_JSON,
    audit_japanese_option_mapping,
    write_japanese_option_audit,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llt", type=Path, required=True)
    parser.add_argument(
        "--current-options",
        type=Path,
        default=DEFAULT_CURRENT_OPTIONS_JSON,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = audit_japanese_option_mapping(
        args.llt,
        current_options_path=args.current_options,
    )
    write_japanese_option_audit(args.output, report)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "current_option_source": report.current_option_source,
                **report.summary.model_dump(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
