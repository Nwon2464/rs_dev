#!/usr/bin/env python3
"""Trace open-option converter evidence from the local Red Stone Data folder.

This script is intentionally evidence-first: it separates directly observed
strings/ids from weaker table-axis guesses.
"""

from __future__ import annotations

import csv
import json
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import msgpack
except ImportError:  # pragma: no cover - optional local dependency
    msgpack = None


ROOT = Path(__file__).resolve().parents[1]
DATA = Path("/mnt/c/game/Red Stone/Data")
OUT = ROOT / "data" / "processed"

ITEM = DATA / "item.dat"
CAPA = DATA / "capa.dat"
OPEN = DATA / "item_option_open.dat"
TEXT2 = DATA / "textData2.dat"
INSTANDARD = DATA / "InstandardEquip.dat"

ITEM_HEADER_SIZE = 0x46
ITEM_RECORD_SIZE = 326
OPEN_ROW_COUNT_PER_BLOCK = 124
OPEN_ROW_SIZE = 24

EFFECT_IDS = {
    920: "개방 옵션 변환창 생성",
    935: "개선된 개방 옵션 변환창 생성",
    954: "약화된 개방 옵션 변환창 생성",
    966: "협회 전용 개방 옵션 변환창 생성",
    1020: "향상된 개방 옵션 변환창 생성",
}

SEARCH_TERMS = [
    "개방 옵션 변환기",
    "개선된 개방 옵션 변환기",
    "모조 개방 옵션 변환기",
    "개방 옵션 변환기[협회]",
    "불타는",
    "향상된 개방 옵션",
    "약화된 개방옵션",
    "개방 옵션 변경",
]


def read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def clean_text(value: str) -> str:
    value = value.replace("\ufffd", "")
    value = "".join(ch for ch in value if ch >= " " or ch in "\t\r\n")
    return re.sub(r"[\x00\s]+", " ", value).strip()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def derive_item_mask(payload: bytes) -> bytes:
    sample = payload[: ITEM_RECORD_SIZE * 50000]
    return bytes(
        Counter(sample[offset::ITEM_RECORD_SIZE]).most_common(1)[0][0]
        for offset in range(ITEM_RECORD_SIZE)
    )


def decode_item_dat() -> bytes:
    data = ITEM.read_bytes()
    payload = data[ITEM_HEADER_SIZE:]
    mask = derive_item_mask(payload)
    return bytes(
        byte ^ mask[index % ITEM_RECORD_SIZE] ^ 0xFF
        for index, byte in enumerate(payload)
    )


def iter_decoded_item_strings(body: bytes):
    record_count = len(body) // ITEM_RECORD_SIZE
    for record_index in range(record_count):
        record = body[
            record_index * ITEM_RECORD_SIZE : (record_index + 1) * ITEM_RECORD_SIZE
        ]
        offset = 0
        for raw in record.split(b"\x00"):
            if len(raw) >= 2:
                text = clean_text(raw.decode("cp949", "replace"))
                if text and (
                    any("\uac00" <= char <= "\ud7a3" for char in text)
                    or "Nx" in text
                    or "NX" in text
                    or "[E]" in text
                ):
                    yield {
                        "record_index": record_index,
                        "file_offset_hex": hex(ITEM_HEADER_SIZE + record_index * ITEM_RECORD_SIZE),
                        "string_offset": offset,
                        "text": text,
                    }
            offset += len(raw) + 1


def trace_item_dat() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    body = decode_item_dat()
    strings = list(iter_decoded_item_strings(body))
    strings_by_record: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in strings:
        strings_by_record[int(row["record_index"])].append(row)

    effect_rows: list[dict[str, Any]] = []
    converter_rows: list[dict[str, Any]] = []
    record_count = len(body) // ITEM_RECORD_SIZE

    for record_index in range(record_count):
        record = body[
            record_index * ITEM_RECORD_SIZE : (record_index + 1) * ITEM_RECORD_SIZE
        ]
        for effect_id, label in EFFECT_IDS.items():
            cursor = 0
            needle = struct.pack("<I", effect_id)
            while True:
                pos = record.find(needle, cursor)
                if pos < 0:
                    break
                nearby = []
                for near_record in range(max(0, record_index - 2), min(record_count, record_index + 3)):
                    nearby.extend(strings_by_record.get(near_record, []))
                effect_rows.append(
                    {
                        "source_file": "item.dat decoded",
                        "effect_id": effect_id,
                        "effect_label": label,
                        "record_index": record_index,
                        "record_file_offset_hex": hex(ITEM_HEADER_SIZE + record_index * ITEM_RECORD_SIZE),
                        "offset_in_record": pos,
                        "absolute_file_offset_hex": hex(
                            ITEM_HEADER_SIZE + record_index * ITEM_RECORD_SIZE + pos
                        ),
                        "nearby_text": " | ".join(row["text"] for row in nearby[:12]),
                    }
                )
                cursor = pos + 1

    for row in strings:
        text = str(row["text"])
        if "변환기" not in text:
            continue
        nearby_effects = [
            effect
            for effect in effect_rows
            if abs(int(effect["record_index"]) - int(row["record_index"])) <= 2
        ]
        converter_rows.append(
            {
                **row,
                "nearby_effect_ids": ",".join(str(item["effect_id"]) for item in nearby_effects),
                "nearby_effect_offsets": ",".join(
                    str(item["absolute_file_offset_hex"]) for item in nearby_effects
                ),
                "classification": (
                    "excluded_association"
                    if "협회" in text
                    else "converter_item_name_or_context"
                ),
            }
        )

    return converter_rows, effect_rows


def read_cp949_len_string(data: bytes, offset: int, max_len: int = 2048):
    if offset + 4 > len(data):
        return None
    length = read_u32(data, offset)
    if length <= 0 or length > max_len or offset + 4 + length > len(data):
        return None
    raw = data[offset + 4 : offset + 4 + length]
    if not raw.endswith(b"\x00"):
        return None
    return {
        "length_offset": offset,
        "text_offset": offset + 4,
        "length": length,
        "text": clean_text(raw[:-1].decode("cp949", "replace")),
        "next_offset": offset + 4 + length,
    }


def parse_capa_records() -> list[dict[str, Any]]:
    data = CAPA.read_bytes()
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for offset in range(0, len(data) - 40):
        option_id = read_u32(data, offset)
        if option_id not in set(EFFECT_IDS) | {958}:
            continue
        first = read_cp949_len_string(data, offset + 32, 512)
        if not first:
            continue
        cursor = int(first["next_offset"])
        strings = [first]
        for _ in range(4):
            entry = read_cp949_len_string(data, cursor, 2048)
            if not entry:
                break
            strings.append(entry)
            cursor = int(entry["next_offset"])
        if offset in seen:
            continue
        seen.add(offset)
        texts = [str(entry["text"]) for entry in strings if entry["text"]]
        rows.append(
            {
                "source_file": "capa.dat",
                "option_id": option_id,
                "record_offset_hex": hex(offset),
                "category_or_type": read_i32(data, offset + 4),
                "texts": " | ".join(texts),
                "evidence_level": "confirmed_effect_record",
            }
        )
    return sorted(rows, key=lambda row: int(row["option_id"]))


def parse_textdata2_hits() -> list[dict[str, Any]]:
    data = TEXT2.read_bytes()
    rows: list[dict[str, Any]] = []
    cursor = 20
    index = 0
    while cursor + 4 <= len(data):
        entry = read_cp949_len_string(data, cursor, 4096)
        if not entry:
            break
        text = str(entry["text"])
        for term in SEARCH_TERMS:
            if term in text:
                rows.append(
                    {
                        "source_file": "textData2.dat",
                        "string_index": index,
                        "offset_hex": hex(cursor),
                        "matched_term": term,
                        "text": text,
                        "evidence_level": "confirmed_ui_text",
                    }
                )
                break
        cursor = int(entry["next_offset"])
        index += 1
    return rows


def parse_open_blocks() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    data = OPEN.read_bytes()
    blocks: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    cursor = 0
    block_index = 0
    while cursor < len(data):
        if cursor == 0:
            header_size = 32
            section_type = read_u32(data, 0x18)
            section_group = read_u32(data, 0x1C)
        else:
            if cursor + 8 > len(data):
                break
            header_size = 8
            section_type = read_u32(data, cursor)
            section_group = read_u32(data, cursor + 4)

        rows_offset = cursor + header_size
        rows_end = rows_offset + OPEN_ROW_COUNT_PER_BLOCK * OPEN_ROW_SIZE
        if rows_end + 4 > len(data):
            break
        after_count = read_u32(data, rows_end)
        after_values_offset = rows_end + 4
        after_end = after_values_offset + after_count * 4
        if after_count > 1000 or after_end > len(data):
            break
        after_values = [
            read_u32(data, after_values_offset + index * 4)
            for index in range(after_count)
        ]

        non_empty = 0
        option_ids: list[int] = []
        row_groups: list[int] = []
        slot_ids: list[int] = []
        value_lows: list[int] = []
        for row_index in range(OPEN_ROW_COUNT_PER_BLOCK):
            offset = rows_offset + row_index * OPEN_ROW_SIZE
            slot, option_id, value, f32_a, f32_b, row_group = struct.unpack_from(
                "<IIIffI", data, offset
            )
            if not any((slot, option_id, value, f32_a, f32_b, row_group)):
                continue
            non_empty += 1
            option_ids.append(option_id)
            row_groups.append(row_group)
            slot_ids.append(slot)
            value_lows.append(value & 0xFFFF)
            rows.append(
                {
                    "source_file": "item_option_open.dat",
                    "block_index": block_index,
                    "section_type": section_type,
                    "section_group": section_group,
                    "file_offset_hex": hex(offset),
                    "open_slot_candidate": slot,
                    "convertible_option_id": option_id,
                    "value_low16": value & 0xFFFF,
                    "value_high16": value >> 16,
                    "float_a": round(f32_a, 6),
                    "float_b": round(f32_b, 6),
                    "row_group": row_group,
                    "after_list_option_ids": ",".join(str(value) for value in after_values),
                    "evidence_level": "confirmed_table_row_unresolved_axis",
                }
            )

        blocks.append(
            {
                "source_file": "item_option_open.dat",
                "block_index": block_index,
                "header_offset_hex": hex(cursor),
                "section_type": section_type,
                "section_group": section_group,
                "non_empty_rows": non_empty,
                "slot_values": ",".join(str(v) for v in sorted(set(slot_ids))),
                "row_group_values": ",".join(str(v) for v in sorted(set(row_groups))),
                "option_id_count": len(set(option_ids)),
                "value_low16_min": min(value_lows) if value_lows else "",
                "value_low16_max": max(value_lows) if value_lows else "",
                "after_list_count": after_count,
                "after_list_values": ",".join(str(value) for value in after_values),
                "evidence_level": "confirmed_binary_structure_unresolved_axis",
            }
        )
        cursor = after_end
        block_index += 1
    return blocks, rows


def scan_file_terms_and_ids() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    encoded_terms: list[tuple[str, str, bytes]] = []
    for term in SEARCH_TERMS:
        for encoding in ("cp949", "utf-8", "utf-16le"):
            try:
                encoded_terms.append((term, encoding, term.encode(encoding)))
            except UnicodeEncodeError:
                pass

    for path in sorted(DATA.iterdir()):
        if not path.is_file():
            continue
        data = path.read_bytes()
        term_hits = []
        for term, encoding, needle in encoded_terms:
            pos = data.find(needle)
            if pos >= 0:
                term_hits.append(f"{term}/{encoding}@{hex(pos)}")
        id_hits = []
        for effect_id in EFFECT_IDS:
            needle = struct.pack("<I", effect_id)
            count = data.count(needle)
            if count:
                first = data.find(needle)
                id_hits.append(f"{effect_id}:count={count}:first={hex(first)}")
        if term_hits or id_hits:
            rows.append(
                {
                    "source_file": path.name,
                    "file_size": path.stat().st_size,
                    "term_hits": " | ".join(term_hits),
                    "little_endian_u32_effect_id_hits": " | ".join(id_hits),
                    "note": (
                        "raw scan only; encoded item.dat is separately decoded"
                        if path.name == "item.dat"
                        else "raw file scan"
                    ),
                }
            )
    return rows


def scan_instandard_msgpack() -> list[dict[str, Any]]:
    if msgpack is None or not INSTANDARD.exists():
        return []
    try:
        value = msgpack.unpackb(INSTANDARD.read_bytes(), raw=False, strict_map_key=False)
    except Exception:
        return []

    rows: list[dict[str, Any]] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                walk(child, f"{path}.{key}")
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{path}[{index}]")
        elif isinstance(node, int) and node in set(EFFECT_IDS) | {958}:
            rows.append(
                {
                    "source_file": "InstandardEquip.dat",
                    "path": path,
                    "matched_value": node,
                    "note": "MessagePack numeric value match; needs field semantics",
                }
            )
        elif isinstance(node, str):
            for term in SEARCH_TERMS:
                if term in node:
                    rows.append(
                        {
                            "source_file": "InstandardEquip.dat",
                            "path": path,
                            "matched_value": term,
                            "text": node,
                            "note": "MessagePack string match",
                        }
                    )

    walk(value, "$")
    return rows


def is_short_converter_item_name(text: str) -> bool:
    if len(text) > 40:
        return False
    if text == "변환기":
        return False
    if text.endswith("["):
        return False
    return "개방 옵션 변환기" in text


def build_confirmed_converter_map(
    capa_rows: list[dict[str, Any]],
    item_converter_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    capa_by_id = {int(row["option_id"]): row for row in capa_rows}
    names_by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in item_converter_rows:
        text = str(row["text"])
        if not is_short_converter_item_name(text):
            continue
        for effect_id in str(row["nearby_effect_ids"]).split(","):
            if effect_id.isdigit():
                names_by_id[int(effect_id)].append(row)

    mapping: list[dict[str, Any]] = []
    for effect_id, effect_label in EFFECT_IDS.items():
        rows = names_by_id.get(effect_id, [])
        names = sorted({str(row["text"]) for row in rows})
        offsets = sorted({str(row["nearby_effect_offsets"]) for row in rows if row["nearby_effect_offsets"]})
        status = "confirmed_name_and_effect" if rows else "effect_only_no_item_name_link"
        if effect_id == 1020:
            status = "effect_only_no_decoded_item_name_found"
        mapping.append(
            {
                "effect_id": effect_id,
                "effect_label_from_capa": effect_label,
                "capa_record_offset_hex": capa_by_id.get(effect_id, {}).get("record_offset_hex", ""),
                "capa_text": capa_by_id.get(effect_id, {}).get("texts", ""),
                "decoded_item_dat_names": "; ".join(names),
                "decoded_item_dat_effect_offsets": "; ".join(offsets),
                "status": status,
            }
        )
    return mapping


def write_report(
    capa_rows: list[dict[str, Any]],
    item_converter_rows: list[dict[str, Any]],
    item_effect_rows: list[dict[str, Any]],
    text_rows: list[dict[str, Any]],
    open_blocks: list[dict[str, Any]],
    open_rows: list[dict[str, Any]],
    raw_scan_rows: list[dict[str, Any]],
    msgpack_rows: list[dict[str, Any]],
) -> None:
    confirmed_map = build_confirmed_converter_map(capa_rows, item_converter_rows)

    section_counts = Counter(
        (int(row["section_type"]), int(row["section_group"])) for row in open_rows
    )
    row_group_counts = Counter(int(row["row_group"]) for row in open_rows)
    slot_counts = Counter(int(row["open_slot_candidate"]) for row in open_rows)

    lines = [
        "# Red Stone Converter Data Trace",
        "",
        "## Source",
        "",
        f"- Local data folder: `{DATA}`",
        "- Original files were read only.",
        "- Web data was not used.",
        "",
        "## Confirmed Links",
        "",
        "| effect_id | capa evidence | decoded item.dat item names | status |",
        "|---:|---|---|---|",
    ]
    for row in confirmed_map:
        lines.append(
            f"| {row['effect_id']} | {row['capa_text'] or 'not found'} | "
            f"{row['decoded_item_dat_names'] or 'not found'} | {row['status']} |"
        )

    lines.extend(
        [
            "",
            "## Confirmed Equipment IDs",
            "",
            "From `capa.dat` option `958`:",
            "",
            "- `0` = 무기",
            "- `1` = 보조무기",
            "- `2` = 갑옷",
            "- `3` = 장갑",
            "- `4` = 헬멧",
            "- `5` = 귀걸이/망토",
            "- `6` = 목걸이",
            "- `7` = 벨트",
            "- `8` = 신발",
            "- `9` = 반지",
            "",
            "## item_option_open.dat",
            "",
            f"- Parsed blocks: `{len(open_blocks)}`",
            f"- Parsed non-empty rows: `{len(open_rows)}`",
            "- These rows are confirmed binary table rows, but their block header axes are not yet linked to Korean converter names.",
            "",
            "Section pairs observed:",
        ]
    )
    for pair, count in sorted(section_counts.items()):
        lines.append(f"- `{pair[0]},{pair[1]}` rows={count}")

    lines.extend(["", "Row group values:"])
    for value, count in sorted(row_group_counts.items()):
        lines.append(f"- `{value}` rows={count}")

    lines.extend(["", "Open slot candidate values:"])
    for value, count in sorted(slot_counts.items()):
        lines.append(f"- `{value}` rows={count}")

    lines.extend(
        [
            "",
            "## UI Text Evidence",
            "",
        ]
    )
    for row in text_rows:
        lines.append(f"- `textData2.dat` index `{row['string_index']}`: {row['text']}")

    lines.extend(
        [
            "",
            "## Raw Folder Scan",
            "",
            f"- Files with raw term/id hits: `{len(raw_scan_rows)}`",
            f"- InstandardEquip MessagePack matches: `{len(msgpack_rows)}`",
            "- Raw numeric hits in unrelated binary files are not treated as evidence unless a nearby string or known structure supports them.",
            "",
            "## Current Boundary",
            "",
            "- Confirmed: converter item names in decoded `item.dat` map to effect ids `920`, `935`, `954`, `966` by nearby binary records.",
            "- Confirmed: `capa.dat` defines those effect ids as open-option conversion window effects.",
            "- Confirmed: `capa.dat` also defines `1020` as `향상된 개방 옵션 변환창 생성`, but no decoded item name is linked to it in this pass.",
            "- Confirmed: `item_option_open.dat` contains the open-option conversion option table.",
            "- Not confirmed yet: which `item_option_open.dat` section type/group corresponds to each converter item name.",
            "- Not found in current pass: a direct local table row that stores both converter effect id/name and `item_option_open.dat` section type/group together.",
        ]
    )

    (OUT / "converter_data_trace.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    item_converter_rows, item_effect_rows = trace_item_dat()
    capa_rows = parse_capa_records()
    text_rows = parse_textdata2_hits()
    open_blocks, open_rows = parse_open_blocks()
    raw_scan_rows = scan_file_terms_and_ids()
    msgpack_rows = scan_instandard_msgpack()
    confirmed_map = build_confirmed_converter_map(capa_rows, item_converter_rows)

    write_csv(OUT / "trace_confirmed_converter_effect_map.csv", confirmed_map)
    write_csv(OUT / "trace_item_dat_converter_strings.csv", item_converter_rows)
    write_csv(OUT / "trace_item_dat_effect_ids.csv", item_effect_rows)
    write_csv(OUT / "trace_capa_converter_effects.csv", capa_rows)
    write_csv(OUT / "trace_textdata2_converter_ui.csv", text_rows)
    write_csv(OUT / "trace_item_option_open_blocks.csv", open_blocks)
    write_csv(OUT / "trace_item_option_open_rows.csv", open_rows)
    write_csv(OUT / "trace_raw_data_folder_hits.csv", raw_scan_rows)
    write_csv(OUT / "trace_instandard_msgpack_hits.csv", msgpack_rows)

    write_json(
        OUT / "converter_data_trace.json",
        {
            "capa_converter_effects": capa_rows,
            "item_dat_converter_strings": item_converter_rows,
            "item_dat_effect_ids": item_effect_rows,
            "textdata2_hits": text_rows,
            "item_option_open_blocks": open_blocks,
            "raw_data_folder_hits": raw_scan_rows,
            "instandard_msgpack_hits": msgpack_rows,
        },
    )
    write_report(
        capa_rows,
        item_converter_rows,
        item_effect_rows,
        text_rows,
        open_blocks,
        open_rows,
        raw_scan_rows,
        msgpack_rows,
    )

    print(f"wrote trace outputs to {OUT}")
    print(f"decoded item.dat converter rows: {len(item_converter_rows)}")
    print(f"decoded item.dat effect id hits: {len(item_effect_rows)}")
    print(f"capa converter/equipment rows: {len(capa_rows)}")
    print(f"textData2 UI hits: {len(text_rows)}")
    print(f"item_option_open rows: {len(open_rows)}")
    print(f"raw folder hit files: {len(raw_scan_rows)}")
    print(f"InstandardEquip msgpack hits: {len(msgpack_rows)}")


if __name__ == "__main__":
    main()
