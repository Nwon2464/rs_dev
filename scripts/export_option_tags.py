#!/usr/bin/env python3
"""Export canonical option tags shared by every web option viewer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.open_options.catalogs.option_tags import (
    DEFAULT_CAPA,
    DEFAULT_GENERAL_OPEN_CSV,
    DEFAULT_INSTANDARD_OPEN_CSV,
    DEFAULT_OUTPUT,
    DEFAULT_SOURCE_JSON,
    build_option_tags,
    collect_option_ids,
    load_source_tags,
    write_option_tags,
)
from rs_dev.parsers import parse_capa


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capa", type=Path, default=DEFAULT_CAPA)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_JSON)
    parser.add_argument("--general-open", type=Path, default=DEFAULT_GENERAL_OPEN_CSV)
    parser.add_argument("--instandard-open", type=Path, default=DEFAULT_INSTANDARD_OPEN_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    source_tags = load_source_tags(args.source)
    option_ids = collect_option_ids(args.general_open, args.instandard_open)
    payload = build_option_tags(parse_capa(args.capa), source_tags, option_ids)
    write_option_tags(args.output, payload)
    print(f"wrote {len(payload['options'])} option tag rows to {args.output}")


if __name__ == "__main__":
    main()
