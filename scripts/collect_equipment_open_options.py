#!/usr/bin/env python3
"""Collect equipment open-option rows from the local Red Stone DAT files.

The output schema follows data/processed/equipment_data_collection_research.md.
No probability is normalized or repaired.
"""

from __future__ import annotations

import argparse
import csv
import struct
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = Path("/mnt/c/game/Red Stone/Data")
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "equipment_open_options_test.csv"

ROWS_PER_BLOCK = 124
ROWS_PER_SLOT = 31
ROW_SIZE = 24
PROBABILITY_TOLERANCE = 0.06

FIELDNAMES = [
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


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_cp949_string(
    data: bytes, offset: int, *, allow_empty: bool = False
) -> tuple[str, int]:
    if offset + 4 > len(data):
        raise ValueError(f"truncated CP949 string length at {offset:#x}")
    length = u32(data, offset)
    end = offset + 4 + length
    if end > len(data):
        raise ValueError(f"invalid CP949 string at {offset:#x}")
    if length == 0:
        if allow_empty:
            return "", end
        raise ValueError(f"empty CP949 string at {offset:#x}")
    if data[end - 1] != 0:
        raise ValueError(f"unterminated CP949 string at {offset:#x}")
    return data[offset + 4 : end - 1].decode("cp949"), end


def parse_simple_game_text(path: Path) -> dict[int, str]:
    data = path.read_bytes()
    count = u32(data, 0x78F)
    if count != 84:
        raise ValueError(f"expected 84 item groups at 0x78f, found {count}")
    cursor = 0x793
    groups: dict[int, str] = {}
    for expected_id in range(count):
        group_id = u32(data, cursor)
        if group_id != expected_id:
            raise ValueError(
                f"item group sequence mismatch at {cursor:#x}: "
                f"expected {expected_id}, found {group_id}"
            )
        name, cursor = read_cp949_string(data, cursor + 4)
        groups[group_id] = name
    return groups


def parse_capa_record_at(data: bytes, offset: int, expected_id: int) -> dict | None:
    if offset + 32 > len(data) or u32(data, offset) != expected_id:
        return None
    try:
        name, cursor = read_cp949_string(data, offset + 32)
        description, cursor = read_cp949_string(data, cursor, allow_empty=True)
        short_text, _ = read_cp949_string(data, cursor, allow_empty=True)
    except (UnicodeDecodeError, ValueError):
        return None
    return {
        "option_id": expected_id,
        "name": name,
        "description": description,
        "short_text": short_text,
        "record_offset": offset,
    }


def parse_option_dictionary(path: Path) -> dict[int, dict]:
    """Parse the capa records in physical ID order, beginning with ID zero."""
    data = path.read_bytes()
    record_count = u32(data, 0x10)
    first_record_offset = 0x25D
    records: dict[int, dict] = {}
    cursor = first_record_offset

    for expected_id in range(record_count):
        if expected_id == 0:
            record = parse_capa_record_at(data, cursor, expected_id)
        else:
            needle = struct.pack("<I", expected_id)
            candidate = data.find(needle, cursor + 33)
            record = None
            while candidate >= 0:
                record = parse_capa_record_at(data, candidate, expected_id)
                if record is not None:
                    cursor = candidate
                    break
                candidate = data.find(needle, candidate + 1)
        if record is None:
            raise ValueError(
                f"capa.dat sequential parse stopped at option_id={expected_id}"
            )
        records[expected_id] = record

    if list(records) != list(range(record_count)):
        raise ValueError("capa.dat option IDs are not contiguous from zero")
    return records


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

        blocks.append(
            {
                "block_index": block_index,
                "grade_code": grade_code,
                "section_group": section_group,
                "group_ids": group_ids,
                "rows": rows,
            }
        )
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
                    "option_name": options[option_id]["name"],
                    "value_raw": packed,
                    "value_0_low16": packed & 0xFFFF,
                    "value_1_high16": packed >> 16,
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--equipment",
        default="헬멧,관,벨트",
        help="comma-separated equipment buckets",
    )
    parser.add_argument(
        "--grade-codes",
        default="7,8,9,11",
        help="comma-separated numeric grade codes",
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

    group_names = parse_simple_game_text(required["simpleGameText.dat"])
    mapping_basis = "simpleGameText.dat item_group_id + capa.dat option_id"
    mapping_confidence = "high_direct_local_join"

    rows = collect(
        parse_blocks(required["item_option_open.dat"]),
        group_names,
        parse_option_dictionary(required["capa.dat"]),
        comma_set(args.equipment),
        int_set(args.grade_codes),
        mapping_basis,
        mapping_confidence,
    )
    if not rows:
        raise ValueError("the requested filters produced no rows")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
