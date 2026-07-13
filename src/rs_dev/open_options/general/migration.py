"""Immutable comparison summary for the legacy general-open CSV."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rs_dev.open_options.common.csv_io import read_csv


LEGACY_CONVERTER_KEYS = {
    "일반 변환기": "normal",
    "개량된 변환기": "improved",
    "모조 변환기": "fake",
    "불타는 변환기": "burning",
    "협회 변환기": "association",
}


def _digest(parts: list[tuple[str, ...]]) -> str:
    payload = "\n".join("\x1f".join(part) for part in sorted(parts))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_legacy_general_baseline(path: Path) -> dict[str, Any]:
    rows = read_csv(path)
    converters = Counter(LEGACY_CONVERTER_KEYS[row["converter_type"]] for row in rows)
    option_ids: dict[str, set[int]] = defaultdict(set)
    equipment = Counter(row["equipment_bucket"] for row in rows)
    grades = Counter(row["grade_code"] for row in rows)
    slot_sums: dict[str, float] = defaultdict(float)
    combinations: list[tuple[str, ...]] = []
    for row in rows:
        converter = LEGACY_CONVERTER_KEYS[row["converter_type"]]
        option_ids[converter].add(int(row["option_id"]))
        slot_key = "|".join(
            (converter, row["equipment_bucket"], row["grade_code"], row["open_slot"])
        )
        slot_sums[slot_key] += float(row["converter_probability"])
        combinations.append(
            (
                converter,
                row["equipment_bucket"],
                row["grade_code"],
                row["open_slot"],
                row["candidate_index"],
                row["option_id"],
                row["value_0_low16"],
                row["value_1_high16"],
                row["converter_probability"],
                row["option_tier"],
            )
        )
    all_ids = sorted({int(row["option_id"]) for row in rows})
    return {
        "schema_version": 1,
        "source": str(path),
        "row_count": len(rows),
        "converter_row_counts": dict(sorted(converters.items())),
        "converter_option_id_counts": {
            key: len(option_ids[key]) for key in sorted(option_ids)
        },
        "unique_option_ids": all_ids,
        "equipment_bucket_row_counts": dict(sorted(equipment.items())),
        "grade_code_row_counts": dict(sorted(grades.items(), key=lambda item: int(item[0]))),
        "open_slot_probability_sums": {
            key: float(format(value, ".9g")) for key, value in sorted(slot_sums.items())
        },
        "option_value_probability_hash": _digest(combinations),
    }


def write_baseline(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
