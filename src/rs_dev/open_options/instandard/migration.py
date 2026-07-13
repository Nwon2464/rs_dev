"""Capture and compare the legacy non-standard outputs."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rs_dev.models.instandard_equipment import InstandardCatalog
from rs_dev.models.instandard_open_option import InstandardOpenOptionRow
from rs_dev.open_options.common.csv_io import read_csv


LEGACY_CONVERTERS = {"일반": "normal", "개량": "improved", "모조": "fake", "불타는": "burning"}


def build_legacy_baseline(catalog_path: Path, open_rows_path: Path) -> dict[str, Any]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    rows = read_csv(open_rows_path)
    tiers = [tier for option in catalog["options"] for tier in option["tiers"]]
    sums: dict[str, float] = defaultdict(float)
    combinations = []
    for row in rows:
        converter = LEGACY_CONVERTERS[row["converter_type"]]
        sums["|".join((row["item_group_id"], converter, row["open_slot"], row["source_block_index"]))] += float(row["probability"])
        combinations.append("|".join((converter, row["item_group_id"], row["open_slot"], row["candidate_index"], row["option_id"], row["value_0_low16"], row["value_1_high16"], row["probability"], row["option_tier"])))
    return {
        "schema_version": 1,
        "equipment_group_count": len(catalog["equipment"]),
        "option_definition_count": len(catalog["options"]),
        "selectable_option_ids": sorted(option["option_id"] for option in catalog["options"] if option["selectable"]),
        "equipment_option_ids": {str(item["item_group_id"]): item["option_ids"] for item in catalog["equipment"]},
        "active_tier_roll_count": sum(len(tier["roll_values"]) for tier in tiers if tier["enabled"]),
        "inactive_tier_roll_count": sum(len(tier["roll_values"]) for tier in tiers if not tier["enabled"]),
        "converter_row_counts": dict(sorted(Counter(LEGACY_CONVERTERS[row["converter_type"]] for row in rows).items())),
        "open_slot_probability_sums": {key: float(format(value, ".9g")) for key, value in sorted(sums.items())},
        "supplemental_option_ids": sorted(catalog["summary"]["supplemental_option_ids"]),
        "open_row_count": len(rows),
        "open_row_hash": hashlib.sha256("\n".join(sorted(combinations)).encode()).hexdigest(),
    }


def summarize_new(catalog: InstandardCatalog, rows: list[InstandardOpenOptionRow]) -> dict[str, Any]:
    sums: dict[str, float] = defaultdict(float)
    combinations = []
    for row in rows:
        sums["|".join((str(row.item_group_id), row.converter_type, str(row.open_slot), str(row.source_block_index)))] += float(row.probability)
        combinations.append("|".join(map(str, (row.converter_type, row.item_group_id, row.open_slot, row.candidate_index, row.option_id, row.value_0, row.value_1, row.probability, row.tier))))
    return {
        "equipment_group_count": len(catalog.equipment),
        "option_definition_count": len(catalog.options),
        "selectable_option_ids": sorted({option_id for item in catalog.equipment for option_id in item.option_ids}),
        "equipment_option_ids": {str(item.item_group_id): item.option_ids for item in catalog.equipment},
        "active_tier_roll_count": sum(len(tier.rolls) for option in catalog.options for tier in option.tiers if tier.enabled),
        "inactive_tier_roll_count": sum(len(tier.rolls) for option in catalog.options for tier in option.tiers if not tier.enabled),
        "converter_row_counts": dict(sorted(Counter(row.converter_type for row in rows).items())),
        "open_slot_probability_sums": {key: float(format(value, ".9g")) for key, value in sorted(sums.items())},
        "supplemental_option_ids": sorted({option_id for item in catalog.equipment for option_id in item.supplemental_option_ids}),
        "open_row_count": len(rows),
        "open_row_hash": hashlib.sha256("\n".join(sorted(combinations)).encode()).hexdigest(),
    }


def compare_baseline(catalog: InstandardCatalog, rows: list[InstandardOpenOptionRow], baseline: dict[str, Any]) -> dict[str, Any]:
    current = summarize_new(catalog, rows)
    mismatches = {field: {"baseline": baseline[field], "current": current[field]} for field in current if baseline[field] != current[field]}
    return {"matches": not mismatches, "mismatches": mismatches, "current": current}
