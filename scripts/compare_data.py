#!/usr/bin/env python3
"""Print a concise comparison report for two game Data snapshots."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.data_diff import (  # noqa: E402
    compare_directories,
    render_markdown,
    render_report,
    report_to_dict,
)


def _new_report_directory(docs_root: Path) -> Path:
    """같은 초에 여러 번 실행해도 기존 폴더를 덮어쓰지 않는다."""
    base_name = f"game-data-inspection-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}"
    for suffix in range(10_000):
        name = base_name if suffix == 0 else f"{base_name}-{suffix}"
        path = docs_root / name
        try:
            path.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return path
    raise OSError("새 보고서 폴더 이름을 만들 수 없습니다")


def write_reports(report, docs_root: Path | None = None) -> tuple[Path, Path]:
    markdown = render_markdown(report)
    json_text = json.dumps(report_to_dict(report), ensure_ascii=False, indent=2) + "\n"
    output_dir = _new_report_directory(docs_root or ROOT / "docs")
    markdown_path = output_dir / "report.md"
    json_path = output_dir / "report.json"
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json_text, encoding="utf-8")
    return markdown_path, json_path


def main() -> int:
    parser = argparse.ArgumentParser(description="before/after 게임 Data 비교 보고서")
    parser.add_argument("paths", nargs="*", type=Path, metavar="경로")
    args = parser.parse_args()
    if len(args.paths) not in (0, 2):
        parser.error("경로 인자는 생략하거나 before와 after 두 개를 지정해야 합니다")
    before, after = args.paths or (ROOT / "before", ROOT / "after")
    report = compare_directories(before, after, require_complete_inputs=True)
    print(render_report(report))
    if report.fatal_error:
        print("필수 입력 검사에 실패하여 보고서 폴더를 만들지 않았습니다.")
        return 1
    try:
        markdown_path, json_path = write_reports(report)
    except (OSError, TypeError, ValueError) as error:
        print(f"보고서를 저장할 수 없습니다: {error}")
        return 1
    print(f"Markdown: {markdown_path}")
    print(f"JSON: {json_path}")
    return 1 if report.warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
