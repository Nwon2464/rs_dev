"""Export japanese.llt section 22 as web-ready base-option JSON."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from rs_dev.japanese_option_audit import collect_japanese_option_templates
from rs_dev.models import JapaneseLltRecord
from rs_dev.parsers import parse_japanese_llt


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "web" / "public" / "data" / "i18n" / "ja" / "base_options.json"


def build_japanese_base_options(
    records: Iterable[JapaneseLltRecord],
) -> dict[int, str]:
    """Build a numerically sorted section 22 option-template mapping."""
    templates = collect_japanese_option_templates(records)
    return dict(sorted(templates.items()))


def write_japanese_base_options(path: Path, templates: dict[int, str]) -> None:
    """Write option templates as readable UTF-8 JSON with string keys."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(templates, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_japanese_base_options(
    llt_path: Path,
    *,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[int, str]:
    """Parse japanese.llt and export every section 22 template."""
    templates = build_japanese_base_options(parse_japanese_llt(llt_path))
    write_japanese_base_options(output_path, templates)
    return templates
