"""Validate normalized non-standard tables before catalog assembly."""

from __future__ import annotations

from collections import Counter

from rs_dev.models.instandard_equipment import (
    InstandardEquipmentGroup,
    InstandardOptionAssignment,
    InstandardTierRoll,
)


def validate_equipment_tables(
    equipment: list[InstandardEquipmentGroup],
    assignments: list[InstandardOptionAssignment],
    tiers: list[InstandardTierRoll],
) -> None:
    if len(equipment) != 34 or len({row.item_group_id for row in equipment}) != 34:
        raise ValueError("expected 34 unique non-standard equipment groups")
    assignment_keys = [(row.item_group_id, row.option_order) for row in assignments]
    if len(assignment_keys) != len(set(assignment_keys)):
        raise ValueError("duplicate assignment order within an equipment group")
    counts = Counter((row.option_id, row.raw_tier_index) for row in tiers)
    if any(count != 10 for count in counts.values()):
        raise ValueError("every option tier must contain exactly 10 rolls")
    if len(tiers) != 8000:
        raise ValueError(f"expected 8000 tier rolls, found {len(tiers)}")
