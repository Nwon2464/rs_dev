"""Apply provenance-labelled supplemental assignments from configuration."""

from __future__ import annotations

import json
from pathlib import Path

from rs_dev.models.instandard_equipment import InstandardOptionAssignment


def apply_supplemental_assignments(
    assignments: list[InstandardOptionAssignment], config_path: Path
) -> list[InstandardOptionAssignment]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    result = list(assignments)
    for raw_option_id, config in payload.items():
        result.append(
            InstandardOptionAssignment(
                item_group_id=int(config["item_group_id"]),
                option_id=int(raw_option_id),
                option_order=int(config["option_order"]),
                assignment_source="supplemental",
                evidence_id=str(config["evidence_id"]),
            )
        )
    return sorted(result, key=lambda row: (row.item_group_id, row.option_order))
