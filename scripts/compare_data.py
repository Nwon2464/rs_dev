#!/usr/bin/env python3
"""Print a concise comparison report for two game Data snapshots."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.data_diff import compare_directories, render_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="before/after 게임 Data 비교 보고서")
    parser.add_argument("paths", nargs="*", type=Path, metavar="경로")
    args = parser.parse_args()
    if len(args.paths) not in (0, 2):
        parser.error("경로 인자는 생략하거나 before와 after 두 개를 지정해야 합니다")
    before, after = args.paths or (ROOT / "before", ROOT / "after")
    report = compare_directories(before, after)
    print(render_report(report))
    return 1 if report.warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
