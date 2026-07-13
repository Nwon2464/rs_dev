"""General converter validation and migration comparison."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rs_dev.models.general_open_option import GeneralOpenOptionRow
from rs_dev.models.open_option_raw import OpenOptionBlock
from rs_dev.open_options.common.validation import duplicate_row_keys
from rs_dev.open_options.converters.specs import ConverterSpec
from rs_dev.parsers.item_option_open import ROWS_PER_SLOT


ROW_IDENTITY = (
    "source_block_index",
    "open_slot",
    "candidate_index",
    "option_id",
)


def validate_converter_rows(
    rows: list[GeneralOpenOptionRow], spec: ConverterSpec
) -> dict[str, Any]:
    if any(row.converter_type != spec.converter_type for row in rows):
        raise ValueError(f"mixed converter rows in {spec.converter_type}")
    if any(row.section_group != spec.section_group for row in rows):
        raise ValueError(f"wrong section group in {spec.converter_type}")
    if any(row.grade_code not in spec.allowed_grade_codes for row in rows):
        raise ValueError(f"wrong grade code in {spec.converter_type}")
    duplicates = duplicate_row_keys((row.model_dump() for row in rows), ROW_IDENTITY)
    if duplicates:
        raise ValueError(f"duplicate {spec.converter_type} rows: {duplicates[:5]}")

    sums: dict[tuple[int, int], float] = defaultdict(float)
    for row in rows:
        sums[(row.source_block_index, row.open_slot)] += float(row.probability)
    anomalies = [
        {
            "source_block_index": block,
            "open_slot": slot,
            "sum": float(format(total, ".9g")),
        }
        for (block, slot), total in sorted(sums.items())
        if abs(total - 100.0) > 0.06
    ]
    return {
        "row_count": len(rows),
        "unique_option_id_count": len({row.option_id for row in rows}),
        "source_block_count": len({row.source_block_index for row in rows}),
        "probability_anomalies": anomalies,
    }


def audit_association_probability_axes(
    blocks: list[OpenOptionBlock], spec: ConverterSpec
) -> dict[str, Any]:
    checked = 0
    mismatches: list[dict[str, Any]] = []
    for block in blocks:
        if block.section_group != spec.section_group or block.section_type not in spec.allowed_grade_codes:
            continue
        for row in block.rows:
            checked += 1
            if row.float_a != row.float_b:
                mismatches.append(
                    {
                        "source_block_index": block.block_index,
                        "row_index": row.row_index,
                        "float_a": row.float_a,
                        "float_b": row.float_b,
                    }
                )
    return {
        "checked_row_count": checked,
        "float_a_float_b_equal": not mismatches,
        "mismatches": mismatches,
    }


def summarize_new_rows(rows: list[GeneralOpenOptionRow]) -> dict[str, Any]:
    converter_counts = Counter(row.converter_type for row in rows)
    converter_ids: dict[str, set[int]] = defaultdict(set)
    equipment = Counter(row.equipment_bucket for row in rows)
    grades = Counter(str(row.grade_code) for row in rows)
    slot_sums: dict[str, float] = defaultdict(float)
    combinations: list[tuple[str, ...]] = []
    for row in rows:
        converter_ids[row.converter_type].add(row.option_id)
        slot_key = "|".join(
            (row.converter_type, row.equipment_bucket, str(row.grade_code), str(row.open_slot))
        )
        slot_sums[slot_key] += float(row.probability)
        combinations.append(
            tuple(
                map(
                    str,
                    (
                        row.converter_type,
                        row.equipment_bucket,
                        row.grade_code,
                        row.open_slot,
                        row.candidate_index,
                        row.option_id,
                        row.value_0,
                        row.value_1,
                        row.probability,
                        row.tier,
                    ),
                )
            )
        )
    digest_payload = "\n".join("\x1f".join(part) for part in sorted(combinations))
    return {
        "row_count": len(rows),
        "converter_row_counts": dict(sorted(converter_counts.items())),
        "converter_option_id_counts": {
            key: len(converter_ids[key]) for key in sorted(converter_ids)
        },
        "unique_option_ids": sorted({row.option_id for row in rows}),
        "equipment_bucket_row_counts": dict(sorted(equipment.items())),
        "grade_code_row_counts": dict(sorted(grades.items(), key=lambda item: int(item[0]))),
        "open_slot_probability_sums": {
            key: float(format(value, ".9g")) for key, value in sorted(slot_sums.items())
        },
        "option_value_probability_hash": hashlib.sha256(
            digest_payload.encode("utf-8")
        ).hexdigest(),
    }


def compare_with_baseline(
    rows: list[GeneralOpenOptionRow], baseline: dict[str, Any]
) -> dict[str, Any]:
    current = summarize_new_rows(rows)
    fields = (
        "row_count",
        "converter_row_counts",
        "converter_option_id_counts",
        "unique_option_ids",
        "equipment_bucket_row_counts",
        "grade_code_row_counts",
        "open_slot_probability_sums",
        "option_value_probability_hash",
    )
    mismatches = {
        field: {"baseline": baseline[field], "current": current[field]}
        for field in fields
        if baseline[field] != current[field]
    }
    return {"matches": not mismatches, "mismatches": mismatches, "current": current}


def write_validation_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
