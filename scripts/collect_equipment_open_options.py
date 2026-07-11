#!/usr/bin/env python3
"""Collect equipment open-option rows from the local Red Stone DAT files.

The output schema follows data/processed/equipment_data_collection_research.md.
No probability is normalized or repaired.
"""

from __future__ import annotations

import argparse
import csv
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.parsers import parse_capa, parse_item_groups, u32
from rs_dev.models import OpenOptionBlock, OpenOptionOutputRow


DEFAULT_DATA_DIR = Path("/mnt/c/game/Red Stone/Data")
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "equipment_open_options_test.csv"

ROWS_PER_BLOCK = 124
ROWS_PER_SLOT = 31
ROW_SIZE = 24
PROBABILITY_TOLERANCE = 0.06

FIELDNAMES = [
    "converter_type",
    "converter_probability",
    "converter_probability_source",
    "equipment_bucket",
    "item_group_ids",
    "item_group_names",
    "grade_code",
    "grade_name",
    "section_group",
    "open_slot",
    "candidate_index",
    "option_id",
    "option_name",
    "option_value_arity",
    "option_display",
    "value_raw",
    "value_0_low16",
    "value_1_high16",
    "normal_probability",
    "improved_probability",
    "option_tier",
    "probability_sum_valid",
    "source_file_name",
    "source_block_index",
    "source_file_offset",
    "mapping_basis",
    "mapping_confidence",
]

GRADE_NAMES = {7: "유니크", 8: "DX 유니크", 9: "ULT 유니크"}

CONVERTER_TYPE_SPECS = (
    ("일반 변환기", 0, "normal_probability", "float_a", {7, 8, 9}),
    ("개량된 변환기", 0, "improved_probability", "float_b", {7, 8, 9}),
    ("모조 변환기", 1, "normal_probability", "float_a", {7, 8, 9}),
    ("불타는 변환기", 3, "normal_probability", "float_a", {7, 8, 9}),
    ("협회 변환기", 2, "normal_probability", "float_a", {8}),
)

BUCKET_BY_GROUP_IDS = {
    (18, 20, 21, 22, 23, 24, 25, 26, 28, 30, 32, 33, 54, 55, 56, 57, 58, 61, 63, 68, 70, 80, 82): "무기",
    (29,): "피리",
    (16,): "공용 갑옷",
    (17,): "전용 갑옷",
    (10, 11): "귀걸이/망토",
    (0,): "헬멧",
    (1,): "관",
    (6,): "벨트",
    (2, 5): "장갑/팔찌",
    (7,): "부츠",
    (8,): "목걸이",
}

DEFAULT_EQUIPMENT = ",".join(dict.fromkeys(BUCKET_BY_GROUP_IDS.values()))


def parse_blocks(path: Path) -> list[dict]:
    data = path.read_bytes()
    blocks = []
    cursor = 0
    block_index = 0
    while cursor < len(data):
        header_size = 32 if block_index == 0 else 8
        if cursor + header_size > len(data):
            raise ValueError(f"truncated block header at {cursor:#x}")
        grade_code = u32(data, cursor + (24 if block_index == 0 else 0))
        section_group = u32(data, cursor + (28 if block_index == 0 else 4))
        rows_offset = cursor + header_size
        rows_end = rows_offset + ROWS_PER_BLOCK * ROW_SIZE
        if rows_end + 4 > len(data):
            raise ValueError(f"truncated row table in block {block_index}")

        group_count = u32(data, rows_end)
        groups_end = rows_end + 4 + group_count * 4
        if group_count > 84 or groups_end > len(data):
            raise ValueError(f"invalid after_list in block {block_index}")
        group_ids = tuple(
            u32(data, rows_end + 4 + index * 4) for index in range(group_count)
        )

        rows = []
        for row_index in range(ROWS_PER_BLOCK):
            offset = rows_offset + row_index * ROW_SIZE
            values = struct.unpack_from("<IIIffI", data, offset)
            if not any(values):
                continue
            candidate_index, option_id, packed_value, normal, improved, tier = values
            rows.append(
                {
                    "row_index": row_index,
                    "offset": offset,
                    "candidate_index": candidate_index,
                    "option_id": option_id,
                    "packed_value": packed_value,
                    "normal": normal,
                    "improved": improved,
                    "tier": tier,
                }
            )

        block = {
            "block_index": block_index,
            "grade_code": grade_code,
            "section_group": section_group,
            "group_ids": group_ids,
            "rows": rows,
        }
        OpenOptionBlock.model_validate(block)
        blocks.append(block)
        cursor = groups_end
        block_index += 1

    if cursor != len(data) or len(blocks) != 176:
        raise ValueError(
            f"item_option_open.dat boundary mismatch: cursor={cursor}, "
            f"size={len(data)}, blocks={len(blocks)}"
        )
    return blocks


def probability_validity(rows: list[dict]) -> dict[int, bool]:
    by_slot: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        by_slot[row["row_index"] // ROWS_PER_SLOT + 1].append(row)

    result = {}
    for slot in range(1, 5):
        slot_rows = by_slot[slot]
        normal_sum = sum(row["normal"] for row in slot_rows)
        improved_sum = sum(row["improved"] for row in slot_rows)
        normal_valid = abs(normal_sum - 100.0) <= PROBABILITY_TOLERANCE
        improved_valid = (
            abs(improved_sum) <= PROBABILITY_TOLERANCE
            or abs(improved_sum - 100.0) <= PROBABILITY_TOLERANCE
        )
        result[slot] = normal_valid and improved_valid
    return result


LONG_VALUE_PLACEHOLDER = re.compile(r"\[수치(?:\.(\d+)F)?\]([01])")
SHORT_VALUE_PLACEHOLDER = re.compile(r"\[(\+?)([01])(?:\.(\d+))?(%?)\]")


def option_value_arity(
    template: str, placeholder: re.Pattern[str], index_group: int
) -> int:
    """Return the number of value arguments required by an option template."""
    indices = [int(match.group(index_group)) for match in placeholder.finditer(template)]
    if not indices:
        return 0
    return 2 if 1 in indices else 1


def render_long_display(template: str, value_0: int, value_1: int) -> str:
    def replace(match: re.Match[str]) -> str:
        precision = match.group(1)
        value = (value_0, value_1)[int(match.group(2))]
        if precision is None:
            return str(value)
        digits = int(precision)
        return f"{value / (10 ** digits):.{digits}f}"

    return LONG_VALUE_PLACEHOLDER.sub(replace, template)


def render_short_display(template: str, value_0: int, value_1: int) -> str:
    def replace(match: re.Match[str]) -> str:
        sign, index, precision, suffix = match.groups()
        value = (value_0, value_1)[int(index)]
        if precision is None:
            rendered = str(value)
        else:
            digits = int(precision)
            rendered = f"{value / (10 ** digits):.{digits}f}"
        return f"{sign}{rendered}{suffix}"

    return SHORT_VALUE_PLACEHOLDER.sub(replace, template)


def option_display(option: dict, value_0: int, value_1: int) -> tuple[int, str]:
    """Build a compact display string from an option's declared argument shape."""
    short_text = option["short_text"]
    short_arity = option_value_arity(short_text, SHORT_VALUE_PLACEHOLDER, 2)
    if short_arity:
        return short_arity, render_short_display(short_text, value_0, value_1)

    description = option["description"]
    long_arity = option_value_arity(description, LONG_VALUE_PLACEHOLDER, 2)
    if long_arity:
        return long_arity, render_long_display(description, value_0, value_1)
    return 0, option["name"]


def collect(
    blocks: list[dict],
    group_names: dict[int, str],
    options: dict[int, dict],
    equipment: set[str],
    grade_codes: set[int],
    mapping_basis: str,
    mapping_confidence: str,
) -> list[dict]:
    output = []
    for block in blocks:
        group_ids = block["group_ids"]
        missing_groups = [group_id for group_id in group_ids if group_id not in group_names]
        if missing_groups:
            raise ValueError(
                f"block {block['block_index']} has unmapped item groups: {missing_groups}"
            )
        if not block["rows"]:
            continue
        if group_ids not in BUCKET_BY_GROUP_IDS:
            raise ValueError(
                f"block {block['block_index']} has unknown equipment signature: {group_ids}"
            )
        bucket = BUCKET_BY_GROUP_IDS[group_ids]
        if bucket not in equipment or block["grade_code"] not in grade_codes:
            continue

        validity = probability_validity(block["rows"])
        for row in block["rows"]:
            option_id = row["option_id"]
            if option_id not in options:
                raise ValueError(
                    f"block {block['block_index']} has unmapped option_id={option_id}"
                )
            slot = row["row_index"] // ROWS_PER_SLOT + 1
            packed = row["packed_value"]
            value_0 = packed & 0xFFFF
            value_1 = packed >> 16
            option = options[option_id]
            value_arity, display = option_display(option, value_0, value_1)
            output.append(
                {
                    "equipment_bucket": bucket,
                    "item_group_ids": ",".join(map(str, group_ids)),
                    "item_group_names": ",".join(group_names[value] for value in group_ids),
                    "grade_code": block["grade_code"],
                    "grade_name": GRADE_NAMES.get(block["grade_code"], ""),
                    "section_group": block["section_group"],
                    "open_slot": slot,
                    "candidate_index": row["candidate_index"],
                    "option_id": option_id,
                    "option_name": option["name"],
                    "option_value_arity": value_arity,
                    "option_display": display,
                    "value_raw": packed,
                    "value_0_low16": value_0,
                    "value_1_high16": value_1,
                    "normal_probability": format(row["normal"], ".6g"),
                    "improved_probability": format(row["improved"], ".6g"),
                    "option_tier": row["tier"],
                    "probability_sum_valid": str(validity[slot]).lower(),
                    "source_file_name": "item_option_open.dat",
                    "source_block_index": block["block_index"],
                    "source_file_offset": hex(row["offset"]),
                    "mapping_basis": mapping_basis,
                    "mapping_confidence": mapping_confidence,
                }
            )
    return output


def comma_set(value: str) -> set[str]:
    return {part.strip() for part in value.split(",") if part.strip()}


def int_set(value: str) -> set[int]:
    return {int(part.strip()) for part in value.split(",") if part.strip()}


def classify_converter_rows(rows: list[dict]) -> list[dict]:
    """Create disjoint converter views from directly observed table axes.

    Association data is restricted to the observed DX Unique table
    (section_group=2, section_type=8).  Its float_a and float_b values are
    identical in the current source revision, so float_a is the canonical
    displayed field.
    """
    classified = []
    for (
        converter_type,
        section_group,
        probability_key,
        probability_source,
        allowed_grade_codes,
    ) in CONVERTER_TYPE_SPECS:
        for row in rows:
            if int(row["section_group"]) != section_group:
                continue
            if int(row["grade_code"]) not in allowed_grade_codes:
                continue
            probability = float(row[probability_key])
            if probability <= 0.0:
                continue
            classified.append(
                {
                    **row,
                    "converter_type": converter_type,
                    "converter_probability": row[probability_key],
                    "converter_probability_source": probability_source,
                }
            )
    return classified


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--equipment",
        default=DEFAULT_EQUIPMENT,
        help="comma-separated equipment buckets",
    )
    parser.add_argument(
        "--grade-codes",
        default="7,8,9",
        help="comma-separated numeric grade codes",
    )
    parser.add_argument(
        "--only-improved",
        action="store_true",
        help="keep only rows with a non-zero improved-converter probability",
    )
    parser.add_argument(
        "--classify-converters",
        action="store_true",
        help="emit the four confirmed converter views with their active probability field",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="directory containing the original DAT files",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    required = {
        "simpleGameText.dat": args.data_dir / "simpleGameText.dat",
        "item_option_open.dat": args.data_dir / "item_option_open.dat",
        "capa.dat": args.data_dir / "capa.dat",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("required source file(s) missing: " + ", ".join(missing))

    group_names = parse_item_groups(
        required["simpleGameText.dat"], expected_count=84
    )
    mapping_basis = "simpleGameText.dat item_group_id + capa.dat option_id"
    mapping_confidence = "high_direct_local_join"

    rows = collect(
        parse_blocks(required["item_option_open.dat"]),
        group_names,
        parse_capa(required["capa.dat"]),
        comma_set(args.equipment),
        int_set(args.grade_codes),
        mapping_basis,
        mapping_confidence,
    )
    if args.only_improved:
        rows = [row for row in rows if float(row["improved_probability"]) > 0.0]
    if args.classify_converters:
        rows = classify_converter_rows(rows)
    if not rows:
        raise ValueError("the requested filters produced no rows")

    if list(OpenOptionOutputRow.model_fields) != FIELDNAMES:
        raise ValueError("open-option output model field order differs from CSV schema")
    for row in rows:
        OpenOptionOutputRow.model_validate(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
