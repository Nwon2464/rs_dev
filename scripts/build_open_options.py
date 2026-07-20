#!/usr/bin/env python3
"""Build general open-option rows and shared locale catalogs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.open_options.general.pipeline import DEFAULT_DATA_DIR, build_general_open_options  # noqa: E402
from rs_dev.open_options.catalogs.pipeline import (  # noqa: E402
    build_auxiliary_catalogs,
    build_japanese_catalog_audits,
)
from rs_dev.open_options.locales.pipeline import (  # noqa: E402
    DEFAULT_LLT,
    build_locale_catalogs,
)
from rs_dev.open_options.instandard.pipeline import build_instandard  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--llt",
        type=Path,
        default=DEFAULT_LLT,
    )
    args = parser.parse_args()
    general = build_general_open_options(data_dir=args.data_dir)
    instandard = build_instandard(data_dir=args.data_dir)
    locales = build_locale_catalogs(data_dir=args.data_dir, llt_path=args.llt)
    catalog_audits = build_japanese_catalog_audits(
        data_dir=args.data_dir,
        llt_path=args.llt,
    )
    catalogs = build_auxiliary_catalogs(catalog_audits, data_dir=args.data_dir)
    print(
        json.dumps(
            {
                "general_rows": general["migration_comparison"]["current"]["row_count"],
                "locale_audit_valid": locales["valid"],
                "catalogs": catalogs,
                "instandard": instandard,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
