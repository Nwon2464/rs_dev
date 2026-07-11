"""Audit current non-standard option IDs against japanese.llt templates."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from rs_dev.models import (
    JapaneseLltRecord,
    JapaneseOptionAuditReport,
    JapaneseOptionAuditSummary,
    JapaneseOptionMapping,
)
from rs_dev.parsers import parse_japanese_llt


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CURRENT_OPTIONS_JSON = (
    ROOT / "data" / "processed" / "instandard_equipment.json"
)
JAPANESE_OPTION_SECTION_ID = 22


def collect_current_option_ids(path: Path) -> set[int]:
    """Collect effective option IDs assigned to current non-standard equipment."""
    dataset: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(dataset, dict):
        raise ValueError("non-standard option dataset must be a JSON object")
    equipment = dataset.get("equipment")
    options = dataset.get("options")
    if not isinstance(equipment, list) or not isinstance(options, list):
        raise ValueError("non-standard option dataset is missing equipment or options")

    try:
        current_ids = {
            int(option_id)
            for item in equipment
            for option_id in item["option_ids"]
        }
        defined_ids = {int(option["option_id"]) for option in options}
        selectable_ids = {
            int(option["option_id"])
            for option in options
            if option["selectable"]
        }
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid non-standard option dataset structure") from error

    undefined = current_ids - defined_ids
    if undefined:
        raise ValueError(
            f"equipment references undefined option IDs: {sorted(undefined)}"
        )
    if current_ids != selectable_ids:
        raise ValueError(
            "equipment option IDs differ from selectable option definitions: "
            f"equipment_only={sorted(current_ids - selectable_ids)}, "
            f"selectable_only={sorted(selectable_ids - current_ids)}"
        )
    return current_ids


def collect_japanese_option_templates(
    records: Iterable[JapaneseLltRecord],
) -> dict[int, str]:
    """Collect unique section 22 templates indexed by text ID."""
    templates: dict[int, str] = {}
    for record in records:
        if record.section_id != JAPANESE_OPTION_SECTION_ID:
            continue
        existing = templates.get(record.text_id)
        if existing is None:
            templates[record.text_id] = record.text
            continue
        if existing == record.text:
            raise ValueError(
                "duplicate japanese.llt section 22 "
                f"text_id={record.text_id} with identical text"
            )
        raise ValueError(
            "conflicting japanese.llt section 22 "
            f"text_id={record.text_id}: {existing!r} != {record.text!r}"
        )
    return templates


def build_japanese_option_audit(
    current_option_ids: Iterable[int],
    records: Iterable[JapaneseLltRecord],
    *,
    current_option_source: str,
) -> JapaneseOptionAuditReport:
    """Build a deterministic audit report from option IDs and LLT records."""
    current_ids = set(current_option_ids)
    if any(option_id < 0 for option_id in current_ids):
        raise ValueError("current option IDs must not be negative")
    japanese_templates = collect_japanese_option_templates(records)
    japanese_ids = set(japanese_templates)

    matched_ids = sorted(current_ids & japanese_ids)
    missing_ids = sorted(current_ids - japanese_ids)
    unused_ids = sorted(japanese_ids - current_ids)
    return JapaneseOptionAuditReport(
        current_option_source=current_option_source,
        summary=JapaneseOptionAuditSummary(
            current_option_count=len(current_ids),
            japanese_section_22_count=len(japanese_ids),
            matched_count=len(matched_ids),
            missing_count=len(missing_ids),
            unused_count=len(unused_ids),
        ),
        matched=[
            JapaneseOptionMapping(
                option_id=option_id,
                japanese_template=japanese_templates[option_id],
            )
            for option_id in matched_ids
        ],
        missing_in_japanese=missing_ids,
        unused_japanese=[
            JapaneseOptionMapping(
                option_id=option_id,
                japanese_template=japanese_templates[option_id],
            )
            for option_id in unused_ids
        ],
    )


def audit_japanese_option_mapping(
    llt_path: Path,
    *,
    current_options_path: Path = DEFAULT_CURRENT_OPTIONS_JSON,
) -> JapaneseOptionAuditReport:
    """Parse japanese.llt and audit it against the current generated dataset."""
    current_ids = collect_current_option_ids(current_options_path)
    records = parse_japanese_llt(llt_path)
    source = f"{current_options_path}:equipment[].option_ids"
    return build_japanese_option_audit(
        current_ids,
        records,
        current_option_source=source,
    )


def write_japanese_option_audit(
    output_path: Path, report: JapaneseOptionAuditReport
) -> None:
    """Write an audit report as human-readable UTF-8 JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
