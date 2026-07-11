"""Export section-type 11 open options for all in-standard equipment groups."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from rs_dev.models import InstandardOpenOptionRow
from rs_dev.open_options import (
    DEFAULT_DATA_DIR,
    PROBABILITY_TOLERANCE,
    ROWS_PER_SLOT,
    option_display,
    parse_blocks,
)
from rs_dev.parsers import parse_capa, parse_item_groups


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INSTANDARD_JSON = ROOT / "data/processed/instandard_equipment.json"
DEFAULT_OUTPUT = ROOT / "data/processed/instandard_open_option_rows.csv"

FIELDNAMES = list(InstandardOpenOptionRow.model_fields)

CONVERTER_VIEWS = (
    ("일반", 0, "normal", "float_a"),
    ("개량", 0, "improved", "float_b"),
    ("모조", 1, "normal", "float_a"),
    ("불타는", 3, "normal", "float_a"),
)

SCREEN_CONFIRMED_WEAPON_SIGNATURE = (
    18,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    28,
    30,
    32,
    33,
    54,
    55,
    56,
    57,
    58,
    61,
    63,
    68,
    70,
    80,
    82,
)

SCREEN_RESULT = (
    (1, 15, 736, 300),
    (2, 13, 623, 25),
    (3, 1, 623, 20),
    (4, 17, 464, 20),
)


def load_instandard_groups(path: Path) -> dict[int, str]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    groups = {
        int(row["item_group_id"]): row["item_group_name"]
        for row in dataset["equipment"]
    }
    if len(groups) != 34:
        raise ValueError(f"expected 34 in-standard equipment groups, found {len(groups)}")
    return groups


def discover_signature_blocks(
    blocks: list[dict], target_ids: set[int]
) -> dict[tuple[int, ...], dict[int, dict]]:
    by_signature: dict[tuple[int, ...], dict[int, dict]] = defaultdict(dict)
    for block in blocks:
        if block["section_type"] != 11 or block["section_group"] not in {0, 1, 3}:
            continue
        signature = block["group_ids"]
        if not signature or not (set(signature) & target_ids):
            continue
        if not set(signature) <= target_ids:
            raise ValueError(
                f"block {block['block_index']} mixes in-standard and extra groups: {signature}"
            )
        section_group = block["section_group"]
        if section_group in by_signature[signature]:
            raise ValueError(
                f"duplicate section group {section_group} for signature {signature}"
            )
        by_signature[signature][section_group] = block

    if len(by_signature) != 10:
        raise ValueError(f"expected 10 raw bucket signatures, found {len(by_signature)}")
    if any(set(group_blocks) != {0, 1, 3} for group_blocks in by_signature.values()):
        raise ValueError("every raw signature must have section groups 0, 1, and 3")

    membership = Counter(group_id for signature in by_signature for group_id in signature)
    missing = sorted(target_ids - set(membership))
    extras = sorted(set(membership) - target_ids)
    duplicates = sorted(group_id for group_id, count in membership.items() if count != 1)
    if missing or extras or duplicates:
        raise ValueError(
            f"signature coverage mismatch: missing={missing}, extras={extras}, "
            f"duplicates={duplicates}"
        )
    return dict(by_signature)


def probability_sums(block: dict, probability_key: str) -> dict[int, float]:
    by_slot: dict[int, list[dict]] = defaultdict(list)
    for row in block["rows"]:
        by_slot[row["row_index"] // ROWS_PER_SLOT + 1].append(row)
    return {
        slot: sum(row[probability_key] for row in by_slot[slot])
        for slot in range(1, 5)
    }


def collect_rows(
    *, data_dir: Path, instandard_json: Path = DEFAULT_INSTANDARD_JSON
) -> tuple[list[dict], dict[str, object]]:
    required = {
        "simpleGameText.dat": data_dir / "simpleGameText.dat",
        "item_option_open.dat": data_dir / "item_option_open.dat",
        "capa.dat": data_dir / "capa.dat",
        "instandard_equipment.json": instandard_json,
    }
    missing_files = [str(path) for path in required.values() if not path.is_file()]
    if missing_files:
        raise FileNotFoundError("required source file(s) missing: " + ", ".join(missing_files))

    instandard_groups = load_instandard_groups(instandard_json)
    local_group_names = parse_item_groups(required["simpleGameText.dat"], expected_count=84)
    for group_id, name in instandard_groups.items():
        if local_group_names.get(group_id) != name:
            raise ValueError(
                f"group name mismatch for {group_id}: "
                f"{name!r} != {local_group_names.get(group_id)!r}"
            )

    blocks = parse_blocks(required["item_option_open.dat"])
    signatures = discover_signature_blocks(blocks, set(instandard_groups))
    options = parse_capa(required["capa.dat"])
    ordered_signatures = sorted(
        signatures.items(),
        key=lambda item: min(block["block_index"] for block in item[1].values()),
    )

    output = []
    for signature_index, (signature, group_blocks) in enumerate(
        ordered_signatures, start=1
    ):
        signature_names = tuple(instandard_groups[group_id] for group_id in signature)
        for group_id in signature:
            for converter_type, section_group, probability_key, probability_source in CONVERTER_VIEWS:
                block = group_blocks[section_group]
                sums = probability_sums(block, probability_key)
                mapping_status = (
                    "screen_confirmed"
                    if converter_type == "불타는"
                    and signature == SCREEN_CONFIRMED_WEAPON_SIGNATURE
                    else "structural_candidate"
                )
                for row in block["rows"]:
                    option_id = row["option_id"]
                    if option_id not in options:
                        raise ValueError(
                            f"block {block['block_index']} has unknown option_id={option_id}"
                        )
                    slot = row["row_index"] // ROWS_PER_SLOT + 1
                    packed = row["packed_value"]
                    value_0 = packed & 0xFFFF
                    value_1 = packed >> 16
                    option = options[option_id]
                    value_arity, display = option_display(option, value_0, value_1)
                    slot_sum = sums[slot]
                    output.append(
                        {
                            "item_group_id": group_id,
                            "item_group_name": instandard_groups[group_id],
                            "bucket_signature_index": signature_index,
                            "bucket_group_ids": ",".join(map(str, signature)),
                            "bucket_group_names": ",".join(signature_names),
                            "converter_type": converter_type,
                            "mapping_status": mapping_status,
                            "section_type": block["section_type"],
                            "section_group": section_group,
                            "open_slot": slot,
                            "candidate_index": row["candidate_index"],
                            "option_id": option_id,
                            "option_name": option["name"],
                            "option_value_arity": value_arity,
                            "option_display": display,
                            "value_raw": packed,
                            "value_0_low16": value_0,
                            "value_1_high16": value_1,
                            "option_tier": row["tier"],
                            "probability": format(row[probability_key], ".9g"),
                            "probability_source": probability_source,
                            "slot_probability_sum": format(slot_sum, ".9g"),
                            "probability_sum_valid": str(
                                abs(slot_sum - 100.0) <= PROBABILITY_TOLERANCE
                            ).lower(),
                            "source_file_name": "item_option_open.dat",
                            "source_block_index": block["block_index"],
                            "source_file_offset": hex(row["offset"]),
                        }
                    )

    converter_order = {name: index for index, (name, *_rest) in enumerate(CONVERTER_VIEWS)}
    output.sort(
        key=lambda row: (
            row["item_group_id"],
            converter_order[row["converter_type"]],
            row["open_slot"],
            row["candidate_index"],
        )
    )
    for row in output:
        InstandardOpenOptionRow.model_validate(row)

    validate_output(output, signatures, set(instandard_groups))
    summary = {
        "equipment_group_count": len({row["item_group_id"] for row in output}),
        "bucket_signature_count": len(signatures),
        "source_block_count": len(
            {(row["section_group"], row["source_block_index"]) for row in output}
        ),
        "row_count": len(output),
        "invalid_probability_slot_count": len(
            {
                (
                    row["item_group_id"],
                    row["converter_type"],
                    row["open_slot"],
                    row["source_block_index"],
                )
                for row in output
                if row["probability_sum_valid"] == "false"
            }
        ),
    }
    return output, summary


def validate_output(
    rows: list[dict],
    signatures: dict[tuple[int, ...], dict[int, dict]],
    target_ids: set[int],
) -> None:
    actual_ids = {row["item_group_id"] for row in rows}
    if actual_ids != target_ids:
        raise ValueError(
            f"output group coverage differs: missing={sorted(target_ids - actual_ids)}, "
            f"extras={sorted(actual_ids - target_ids)}"
        )
    if len(signatures) != 10:
        raise ValueError("output does not use exactly 10 bucket signatures")
    if any(row["section_type"] != 11 or row["section_group"] == 2 for row in rows):
        raise ValueError("output contains an unexpected section axis")

    cannon_burning = [
        row
        for row in rows
        if row["item_group_id"] == 82 and row["converter_type"] == "불타는"
    ]
    for slot, candidate, option_id, value_0 in SCREEN_RESULT:
        if not any(
            row["open_slot"] == slot
            and row["candidate_index"] == candidate
            and row["option_id"] == option_id
            and row["value_0_low16"] == value_0
            for row in cannon_burning
        ):
            raise ValueError(
                f"screen result is missing: slot={slot}, candidate={candidate}, "
                f"option_id={option_id}, value={value_0}"
            )

    invalid_slots = {
        (
            row["item_group_id"],
            row["converter_type"],
            row["open_slot"],
            row["source_block_index"],
            row["slot_probability_sum"],
        )
        for row in rows
        if row["probability_sum_valid"] == "false"
    }
    expected_invalid = {(1, "불타는", 4, 73, "88.8899989")}
    if invalid_slots != expected_invalid:
        raise ValueError(f"unexpected probability anomalies: {sorted(invalid_slots)}")


def write_output(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
