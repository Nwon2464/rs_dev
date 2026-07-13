"""Validate section_type=11 structure, probability and screen fixtures."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from rs_dev.models.instandard_open_option import InstandardOpenOptionRow


SCREEN_ROWS = ((1, 15, 736, 300), (2, 13, 623, 25), (3, 1, 623, 20), (4, 17, 464, 20))


def validate_instandard_open_rows(rows: list[InstandardOpenOptionRow]) -> dict[str, Any]:
    if len(rows) != 12199:
        raise ValueError(f"expected 12199 non-standard open rows, found {len(rows)}")
    if len({row.item_group_id for row in rows}) != 34:
        raise ValueError("non-standard open rows do not cover 34 equipment groups")
    if len({row.bucket_group_ids for row in rows}) != 10:
        raise ValueError("non-standard open rows do not preserve 10 signatures")
    sums: dict[tuple[int, str, int, int], float] = defaultdict(float)
    for row in rows:
        sums[(row.item_group_id, row.converter_type, row.open_slot, row.source_block_index)] += float(row.probability)
    anomalies = {
        (*key, format(total, ".9g"))
        for key, total in sums.items()
        if abs(total - 100.0) > 0.06
    }
    expected = {(1, "burning", 4, 73, "88.8899989")}
    if anomalies != expected:
        raise ValueError(f"unexpected probability anomalies: {sorted(anomalies)}")
    cannon = [row for row in rows if row.item_group_id == 82 and row.converter_type == "burning"]
    for slot, candidate, option_id, value_0 in SCREEN_ROWS:
        if not any(row.open_slot == slot and row.candidate_index == candidate and row.option_id == option_id and row.value_0 == value_0 for row in cannon):
            raise ValueError(f"screen-confirmed row missing: {(slot, candidate, option_id, value_0)}")
    return {
        "row_count": len(rows),
        "equipment_group_count": 34,
        "signature_count": 10,
        "probability_anomalies": [
            {
                "item_group_id": item_group_id,
                "converter_type": converter,
                "open_slot": slot,
                "source_block_index": block,
                "sum": total,
            }
            for item_group_id, converter, slot, block, total in sorted(anomalies)
        ],
    }
