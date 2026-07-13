"""Assemble the UI catalog from normalized non-standard tables."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from rs_dev.models.instandard_equipment import (
    InstandardCatalog,
    InstandardEquipmentGroup,
    InstandardOptionAssignment,
    InstandardTierRoll,
    ParsedInstandardEquip,
)
from rs_dev.option_tags import canonical_tags


def build_catalog(
    parsed: ParsedInstandardEquip,
    equipment: list[InstandardEquipmentGroup],
    assignments: list[InstandardOptionAssignment],
    tier_rolls: list[InstandardTierRoll],
    capa: Mapping[int, Mapping[str, Any]],
    value_bindings: Mapping[int, Mapping[int, int]],
) -> InstandardCatalog:
    assignment_by_group: dict[int, list[InstandardOptionAssignment]] = defaultdict(list)
    for assignment in assignments:
        assignment_by_group[assignment.item_group_id].append(assignment)
    rolls_by_option_tier: dict[tuple[int, int], list[InstandardTierRoll]] = defaultdict(list)
    for roll in tier_rolls:
        rolls_by_option_tier[(roll.option_id, roll.raw_tier_index)].append(roll)
    raw_options = {option.OptionCapaIndex: option for option in parsed.OptionData}

    catalog_options = []
    for option_id, option in raw_options.items():
        tiers = []
        for raw_tier in option.TierData:
            rows = sorted(
                rolls_by_option_tier[(option_id, raw_tier.Tier)],
                key=lambda row: row.roll_index,
            )
            tiers.append(
                {
                    "tier": raw_tier.Tier,
                    "option_level_raw": raw_tier.OptionLevel,
                    "enabled": raw_tier.OptionLevel != 99999,
                    "rolls": [(row.value_0, row.value_1, row.value_2) for row in rows],
                }
            )
        catalog_options.append(
            {
                "option_id": option_id,
                "source_tags": option.TagName,
                "canonical_tags": canonical_tags(capa[option_id], option.TagName),
                "tiers": tiers,
            }
        )

    return InstandardCatalog.model_validate(
        {
            "schema_version": 1,
            "value_bindings": {
                str(option_id): {str(target): source for target, source in bindings.items()}
                for option_id, bindings in value_bindings.items()
            },
            "equipment": [
                {
                    "item_group_id": item.item_group_id,
                    "item_group_name": item.item_group_name,
                    "bucket_signature_index": item.bucket_signature_index,
                    "option_ids": [row.option_id for row in assignment_by_group[item.item_group_id]],
                    "supplemental_option_ids": [row.option_id for row in assignment_by_group[item.item_group_id] if row.assignment_source == "supplemental"],
                }
                for item in equipment
            ],
            "options": catalog_options,
        }
    )
