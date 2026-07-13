"""Normalize equipment groups and raw option assignments."""

from __future__ import annotations

from collections import Counter, defaultdict

from rs_dev.models.instandard_equipment import (
    InstandardEquipmentGroup,
    InstandardOptionAssignment,
    ParsedInstandardEquip,
)
from rs_dev.models.open_option_raw import OpenOptionBlock


def discover_instandard_signatures(
    blocks: list[OpenOptionBlock], target_ids: set[int]
) -> list[tuple[tuple[int, ...], dict[int, OpenOptionBlock]]]:
    by_signature: dict[tuple[int, ...], dict[int, OpenOptionBlock]] = defaultdict(dict)
    for block in blocks:
        if block.section_type != 11 or block.section_group not in {0, 1, 3}:
            continue
        if not block.group_ids or not (set(block.group_ids) & target_ids):
            continue
        if not set(block.group_ids) <= target_ids:
            raise ValueError(f"mixed non-standard signature: {block.group_ids}")
        if block.section_group in by_signature[block.group_ids]:
            raise ValueError(f"duplicate section group for signature {block.group_ids}")
        by_signature[block.group_ids][block.section_group] = block
    if len(by_signature) != 10 or any(set(group) != {0, 1, 3} for group in by_signature.values()):
        raise ValueError("expected 10 signatures with section groups 0, 1, and 3")
    membership = Counter(group_id for signature in by_signature for group_id in signature)
    if set(membership) != target_ids or any(count != 1 for count in membership.values()):
        raise ValueError("non-standard signature coverage mismatch")
    return sorted(
        by_signature.items(),
        key=lambda item: min(block.block_index for block in item[1].values()),
    )


def normalize_equipment(
    parsed: ParsedInstandardEquip,
    item_group_names: dict[int, str],
    signatures: list[tuple[tuple[int, ...], dict[int, OpenOptionBlock]]],
) -> tuple[list[InstandardEquipmentGroup], list[InstandardOptionAssignment]]:
    signature_index = {
        group_id: index
        for index, (signature, _blocks) in enumerate(signatures, start=1)
        for group_id in signature
    }
    equipment: list[InstandardEquipmentGroup] = []
    assignments: list[InstandardOptionAssignment] = []
    for group_id, option_ids in parsed.OptionsByItemType:
        equipment.append(
            InstandardEquipmentGroup(
                item_group_id=group_id,
                item_group_name=item_group_names[group_id],
                bucket_signature_index=signature_index[group_id],
            )
        )
        assignments.extend(
            InstandardOptionAssignment(
                item_group_id=group_id,
                option_id=option_id,
                option_order=order,
                assignment_source="raw",
                evidence_id="InstandardEquip.OptionsByItemType",
            )
            for order, option_id in enumerate(option_ids, start=1)
        )
    return equipment, assignments
