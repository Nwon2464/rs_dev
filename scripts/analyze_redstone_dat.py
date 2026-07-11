#!/usr/bin/env python3
"""Read-only Red Stone DAT analyzer for open-option converter candidates."""

from __future__ import annotations

import csv
import json
import math
import struct
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs_dev.parsers import u32 as read_u32


RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

ITEM = RAW / "item.dat"
CAPA = RAW / "capa.dat"
OPEN = RAW / "item_option_open.dat"

ROW_COUNT_PER_BLOCK = 124
OPEN_ROW_SIZE = 24


def read_i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def read_cp949_len_string(data: bytes, offset: int, max_len: int = 2048):
    if offset + 4 > len(data):
        return None
    length = read_u32(data, offset)
    if length > max_len or offset + 4 + length > len(data):
        return None
    raw = data[offset + 4 : offset + 4 + length]
    if length and not raw.endswith(b"\x00"):
        return None
    text_raw = raw[:-1] if raw.endswith(b"\x00") else raw
    text = text_raw.decode("cp949", "replace").replace("\r\n", "\\n")
    return {
        "length_offset": offset,
        "text_offset": offset + 4,
        "length": length,
        "text": text,
        "next_offset": offset + 4 + length,
    }


def clean_text(value: str) -> str:
    return "".join(ch for ch in value if ch >= " " or ch in "\t\n").strip()


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def find_all(data: bytes, needle: bytes):
    offsets = []
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            return offsets
        offsets.append(pos)
        start = pos + 1


def parse_item_dat() -> dict:
    data = ITEM.read_bytes()
    header = {
        "file": str(ITEM.relative_to(ROOT)),
        "file_size": len(data),
        "magic_raw_hex": data[:16].hex(" "),
        "magic_text": data[:16].rstrip(b"\x00").decode("latin1", "replace"),
        "save_error_text": data[16:60].split(b"\x00", 1)[0].decode("latin1", "replace"),
        "package_meta_u32_le_at_0x3c": read_u32(data, 0x3C),
        "count_candidate_u32_le_at_0x40": read_u32(data, 0x40),
        "reserved_u16_le_at_0x44": int.from_bytes(data[0x44:0x46], "little"),
    }
    payload_offset = 0x46
    record_size = 326
    payload = data[payload_offset:]
    keyword_hits = {}
    for encoding in ("cp949", "utf-8", "utf-16le"):
        try:
            keyword_hits[encoding] = find_all(data, "변환기".encode(encoding))[:20]
        except UnicodeEncodeError:
            keyword_hits[encoding] = []

    return {
        "header": header,
        "layout_guess": {
            "payload_offset": payload_offset,
            "record_size": record_size,
            "full_record_count": len(payload) // record_size,
            "trailing_bytes": len(payload) % record_size,
            "record_count_note": "heuristic only; item payload remains encoded/compressed",
        },
        "payload_entropy_first_1mb": round(entropy(payload[: 1024 * 1024]), 4),
        "converter_plaintext_hits": keyword_hits,
        "status": (
            "item.dat has a readable package header, but the body is high-entropy and "
            "the Korean keyword is not present in CP949/UTF-8/UTF-16LE plaintext."
        ),
    }


def parse_capa_records() -> list[dict]:
    data = CAPA.read_bytes()
    candidates = []
    seen = set()

    for offset in range(0, len(data) - 40):
        record_id = read_u32(data, offset)
        if not 1 <= record_id <= 10000:
            continue
        first = read_cp949_len_string(data, offset + 32, max_len=512)
        if not first or not clean_text(first["text"]):
            continue

        cursor = first["next_offset"]
        strings = [first]
        for _ in range(4):
            entry = read_cp949_len_string(data, cursor, max_len=2048)
            if not entry:
                break
            strings.append(entry)
            cursor = entry["next_offset"]

        non_empty = [clean_text(entry["text"]) for entry in strings if clean_text(entry["text"])]
        if len(non_empty) < 2:
            continue
        if offset in seen:
            continue
        seen.add(offset)

        next_record_id = read_u32(data, cursor + 4) if cursor + 8 <= len(data) else None
        semantic_score = 0
        joined = " ".join(non_empty)
        if "[수치]" in joined or "[0" in joined:
            semantic_score += 4
        if "％" in joined or "%" in joined:
            semantic_score += 1
        if next_record_id == record_id + 1:
            semantic_score += 2
        if 1 <= read_i32(data, offset + 4) <= 30:
            semantic_score += 1
        confidence = "high" if semantic_score >= 5 else "medium"
        candidates.append(
            {
                "option_id": record_id,
                "record_offset": offset,
                "record_offset_hex": hex(offset),
                "category_or_type": read_i32(data, offset + 4),
                "name": non_empty[0],
                "description": non_empty[1] if len(non_empty) > 1 else "",
                "short_text": non_empty[2] if len(non_empty) > 2 else "",
                "alternate_text": non_empty[3] if len(non_empty) > 3 else "",
                "next_record_id_candidate": next_record_id,
                "semantic_score": semantic_score,
                "confidence": confidence,
            }
        )

    # If duplicated IDs are found, keep the strongest and earliest candidate.
    best = {}
    score = {"high": 2, "medium": 1}
    for row in candidates:
        old = best.get(row["option_id"])
        if old is None or (
            score[row["confidence"]],
            row["semantic_score"],
            -row["record_offset"],
        ) > (
            score[old["confidence"]],
            old["semantic_score"],
            -old["record_offset"],
        ):
            best[row["option_id"]] = row
    return [best[key] for key in sorted(best)]


def parse_item_option_open() -> tuple[list[dict], list[dict]]:
    data = OPEN.read_bytes()
    blocks = []
    rows = []
    cursor = 0
    block_index = 0

    while cursor < len(data):
        if cursor == 0:
            header_size = 32
            header_type = read_u32(data, 0x18)
            header_group = read_u32(data, 0x1C)
            file_header = {
                "magic_hex": data[:4].hex(" "),
                "u32_fields_0x00_to_0x1f": [read_u32(data, i) for i in range(0, 32, 4)],
            }
        else:
            if cursor + 8 > len(data):
                break
            header_size = 8
            header_type = read_u32(data, cursor)
            header_group = read_u32(data, cursor + 4)
            file_header = None

        rows_offset = cursor + header_size
        rows_end = rows_offset + ROW_COUNT_PER_BLOCK * OPEN_ROW_SIZE
        if rows_end + 4 > len(data):
            break

        after_count = read_u32(data, rows_end)
        after_values_offset = rows_end + 4
        after_end = after_values_offset + after_count * 4
        if after_count > 1000 or after_end > len(data):
            break
        after_values = [read_u32(data, after_values_offset + i * 4) for i in range(after_count)]

        non_empty = 0
        for row_index in range(ROW_COUNT_PER_BLOCK):
            offset = rows_offset + row_index * OPEN_ROW_SIZE
            row_id, option_id, value, f32_a, f32_b, row_group = struct.unpack_from(
                "<IIIffI", data, offset
            )
            if not any((row_id, option_id, value, f32_a, f32_b, row_group)):
                continue
            non_empty += 1
            rows.append(
                {
                    "dat_row_id": len(rows) + 1,
                    "block_index": block_index,
                    "file_offset": offset,
                    "file_offset_hex": hex(offset),
                    "section_header_type": header_type,
                    "section_header_group": header_group,
                    "row_index_in_block": row_index,
                    "open_slot_candidate": row_id,
                    "option_id": option_id,
                    "value_raw": value,
                    "value_low16": value & 0xFFFF,
                    "value_high16": value >> 16,
                    "f32_a": round(f32_a, 6),
                    "f32_b": round(f32_b, 6),
                    "row_group_candidate": row_group,
                    "after_list_option_ids": ",".join(str(v) for v in after_values),
                }
            )

        blocks.append(
            {
                "block_index": block_index,
                "header_offset": cursor,
                "header_offset_hex": hex(cursor),
                "header_type": header_type,
                "header_group": header_group,
                "rows_offset_hex": hex(rows_offset),
                "rows_total": ROW_COUNT_PER_BLOCK,
                "non_empty_count": non_empty,
                "after_list_count": after_count,
                "after_list_values": after_values,
                "after_list_signature": ",".join(str(v) for v in after_values[:12]),
                "next_offset_hex": hex(after_end),
                "file_header": file_header,
            }
        )
        cursor = after_end
        block_index += 1

    return blocks, rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def option_label(option_id: int, option_map: dict[int, dict]) -> str:
    row = option_map.get(option_id)
    if not row:
        return f"option_id:{option_id}"
    text = row.get("short_text") or row.get("name") or f"option_id:{option_id}"
    return f"{option_id} {text}"


def build_final_candidates(open_rows: list[dict], option_map: dict[int, dict]) -> list[dict]:
    final_rows = []
    for row in open_rows:
        original_ids = [
            int(value)
            for value in row["after_list_option_ids"].split(",")
            if value.strip().isdigit()
        ]
        final_rows.append(
            {
                "converter_name": "unknown_converter_name",
                "converter_axis_candidate": f"row_group_{row['row_group_candidate']}",
                "target_equipment": (
                    f"section_type_{row['section_header_type']}"
                    f"_group_{row['section_header_group']}"
                ),
                "open_slot": f"slot_candidate_{row['open_slot_candidate']}",
                "original_option": "; ".join(option_label(v, option_map) for v in original_ids),
                "convertible_option": option_label(row["option_id"], option_map),
                "value_range": (
                    f"raw={row['value_raw']}; low16={row['value_low16']}; "
                    f"high16={row['value_high16']}; f32={row['f32_a']}..{row['f32_b']}"
                ),
                "probability_or_weight_candidate": (
                    f"f32_a={row['f32_a']}; f32_b={row['f32_b']}"
                ),
                "source_block_index": row["block_index"],
                "source_dat_row_id": row["dat_row_id"],
                "source_file_offset": row["file_offset_hex"],
                "confidence": "medium",
                "notes": (
                    "candidate reconstruction from local DAT files only; converter/equipment/slot "
                    "axis names are not directly encoded in the parsed block"
                ),
            }
        )
    return final_rows


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(
    item_report: dict,
    capa_rows: list[dict],
    blocks: list[dict],
    open_rows: list[dict],
    final_rows: list[dict],
):
    block_kind_counts = Counter((row["header_type"], row["header_group"]) for row in blocks)
    option_ids = sorted({row["option_id"] for row in open_rows})
    capa_ids = {row["option_id"] for row in capa_rows}
    covered = [option_id for option_id in option_ids if option_id in capa_ids]
    lines = [
        "# Red Stone DAT Local Analysis Report",
        "",
        "## Scope",
        "",
        "- Source files: `data/raw/item.dat`, `data/raw/capa.dat`, `data/raw/item_option_open.dat`",
        "- External web data: not used",
        "- Original DAT files: not modified",
        "",
        "## item.dat",
        "",
        f"- File size: `{item_report['header']['file_size']}` bytes",
        f"- Header text: `{item_report['header']['magic_text']}`",
        f"- Payload layout guess: offset `0x46`, record size `326`, full records `{item_report['layout_guess']['full_record_count']}`, trailing bytes `{item_report['layout_guess']['trailing_bytes']}`",
        f"- Payload entropy, first 1MiB: `{item_report['payload_entropy_first_1mb']}`",
        "- `변환기` plaintext hits: "
        + ", ".join(
            f"{enc}={len(offsets)}" for enc, offsets in item_report["converter_plaintext_hits"].items()
        ),
        "- Status: item master extraction is blocked by encoded/compressed payload; no item-name based converter candidate was confirmed.",
        "",
        "## capa.dat",
        "",
        f"- Parsed option dictionary candidates: `{len(capa_rows)}`",
        f"- Open-option IDs seen in `item_option_open.dat`: `{len(option_ids)}`",
        f"- Open-option IDs covered by parsed `capa.dat` records: `{len(covered)}`",
        "",
        "## item_option_open.dat",
        "",
        f"- Parsed blocks: `{len(blocks)}`",
        f"- Parsed non-empty rows: `{len(open_rows)}`",
        "- Most common header type/group pairs: "
        + ", ".join(f"{key}:{count}" for key, count in block_kind_counts.most_common(8)),
        "- Block structure used: initial 32-byte file/header area, then 124 fixed 24-byte rows; later blocks use 8-byte headers followed by the same row area and a counted u32 list.",
        "",
        "## Final Candidate Table",
        "",
        f"- Rows written: `{len(final_rows)}`",
        "- Main CSV: `data/processed/open_option_converter_candidates.csv`",
        "- Main JSON: `data/processed/open_option_converter_candidates.json`",
        "- Important caveat: converter names, equipment names, and slot names are candidate axes, not confirmed Korean display names.",
    ]
    (OUT / "analysis_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_tag_reverse_engineering(capa_rows: list[dict], blocks: list[dict], open_rows: list[dict]):
    option_map = {row["option_id"]: row for row in capa_rows}
    findings = []

    equipment_map = {
        0: "무기",
        1: "보조무기",
        2: "갑옷",
        3: "장갑",
        4: "헬멧",
        5: "귀걸이/망토",
        6: "목걸이",
        7: "벨트",
        8: "신발",
        9: "반지",
    }
    for value, name in equipment_map.items():
        findings.append(
            {
                "tag_type": "capa_fixed_value_3_equipment_type",
                "tag_value": value,
                "candidate_meaning": name,
                "confidence": "confirmed",
                "evidence": (
                    "capa option_id 958 alternate_text states: "
                    "고정수치 3 : 0(무기), 1(보조무기), 2(갑옷), 3(장갑), "
                    "4(헬멧), 5(귀걸이/망토), 6(목걸이), 7(벨트), 8(신발), 9(반지)"
                ),
            }
        )

    converter_effects = {
        920: "개방 옵션 변환창 생성",
        935: "개선된 개방 옵션 변환창 생성",
        954: "약화된 개방 옵션 변환창 생성",
        966: "협회 전용 개방 옵션 변환창 생성",
    }
    for option_id, meaning in converter_effects.items():
        row = option_map.get(option_id, {})
        findings.append(
            {
                "tag_type": "capa_converter_window_effect",
                "tag_value": option_id,
                "candidate_meaning": meaning,
                "confidence": "confirmed_effect_not_item_name",
                "evidence": (
                    f"capa option_id {option_id}: "
                    f"{row.get('name', '')} / {row.get('description', '')} / {row.get('short_text', '')}"
                ),
            }
        )

    section_pairs = sorted(
        {(int(row["section_header_type"]), int(row["section_header_group"])) for row in open_rows}
    )
    section_counts = Counter(
        (int(row["section_header_type"]), int(row["section_header_group"])) for row in open_rows
    )
    for pair in section_pairs:
        findings.append(
            {
                "tag_type": "item_option_open_section_pair",
                "tag_value": f"{pair[0]},{pair[1]}",
                "candidate_meaning": "unknown table axis; not directly resolved to equipment or converter name",
                "confidence": "unconfirmed",
                "evidence": (
                    f"parsed from block header; non-empty rows={section_counts[pair]}; "
                    "values do not match confirmed equipment ids 0..9 or converter effect ids "
                    "920/935/954/966"
                ),
            }
        )

    type_to_values = {}
    for section_type in sorted({int(row["section_header_type"]) for row in open_rows}):
        values = [
            int(row["value_low16"])
            for row in open_rows
            if int(row["section_header_type"]) == section_type and row["option_id"] == "63"
        ]
        if values:
            type_to_values[section_type] = (min(values), max(values), round(sum(values) / len(values), 2))
    for section_type, (vmin, vmax, vavg) in type_to_values.items():
        findings.append(
            {
                "tag_type": "item_option_open_section_type",
                "tag_value": section_type,
                "candidate_meaning": "possible strength/rank axis",
                "confidence": "low",
                "evidence": (
                    f"for option_id 63, value_low16 range={vmin}..{vmax}, avg={vavg}; "
                    "relative scale suggests ranking, but no local string maps this number to a converter name"
                ),
            }
        )

    row_group_counts = Counter(int(row["row_group_candidate"]) for row in open_rows)
    for row_group, count in sorted(row_group_counts.items()):
        findings.append(
            {
                "tag_type": "item_option_open_row_group",
                "tag_value": row_group,
                "candidate_meaning": "unknown row-level group; not confirmed as converter type",
                "confidence": "unconfirmed",
                "evidence": (
                    f"appears in {count} rows; five distinct values exist, while known converter-window "
                    "effects are four ids, so this is not a clean converter-name mapping"
                ),
            }
        )

    write_csv(OUT / "dat_tag_reverse_engineering.csv", findings)

    lines = [
        "# DAT Tag Reverse Engineering Findings",
        "",
        "## Confirmed",
        "",
        "- Equipment target IDs were found in `capa.dat` option_id `958`.",
        "- Converter-window effects were found in `capa.dat` option_ids `920`, `935`, `954`, `966`.",
        "- These converter-window effect names are effect labels, not necessarily item names from `item.dat`.",
        "",
        "## Equipment Target IDs",
        "",
    ]
    for value, name in equipment_map.items():
        lines.append(f"- `{value}` = {name}")
    lines.extend(
        [
            "",
            "## Converter-Window Effect IDs",
            "",
        ]
    )
    for option_id, meaning in converter_effects.items():
        lines.append(f"- `{option_id}` = {meaning}")
    lines.extend(
        [
            "",
            "## item_option_open.dat Section Tags",
            "",
            "- `section_type`/`section_group` are block-header fields from `item_option_open.dat`.",
            "- They do not directly equal the confirmed equipment IDs `0..9`.",
            "- They do not contain the converter effect IDs `920`, `935`, `954`, `966`.",
            "- Current evidence supports treating them as internal table axes until another file links them to names.",
            "",
            "Observed section pairs:",
        ]
    )
    for pair in section_pairs:
        lines.append(f"- `{pair[0]},{pair[1]}` rows={section_counts[pair]}")
    lines.extend(
        [
            "",
            "## Low-Confidence Inference",
            "",
            "- `section_type` values `7`, `8`, `9`, `11` show different numeric scales, so they may be rank/strength tiers.",
            "- No local string currently proves which one is `모조`, `개방`, `개량된`, or `불타는`.",
            "- `row_group` has five distinct values, so it should not be named as the four converter types.",
        ]
    )
    (OUT / "dat_tag_reverse_engineering.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    item_report = parse_item_dat()
    capa_rows = parse_capa_records()
    blocks, open_rows = parse_item_option_open()

    option_map = {row["option_id"]: row for row in capa_rows}
    for row in open_rows:
        option = option_map.get(row["option_id"])
        row["option_name"] = option["name"] if option else ""
        row["option_short_text"] = option["short_text"] if option else ""
        row["option_description"] = option["description"] if option else ""

    final_rows = build_final_candidates(open_rows, option_map)

    write_json(OUT / "item_dat_report.json", item_report)
    write_json(OUT / "capa_option_dictionary.json", capa_rows)
    write_json(OUT / "item_option_open_blocks.json", blocks)
    write_json(OUT / "item_option_open_rows.json", open_rows)
    write_json(OUT / "open_option_converter_candidates.json", final_rows)

    write_csv(OUT / "capa_option_dictionary.csv", capa_rows)
    write_csv(OUT / "item_option_open_blocks.csv", blocks)
    write_csv(OUT / "item_option_open_rows.csv", open_rows)
    write_csv(OUT / "open_option_converter_candidates.csv", final_rows)
    write_report(item_report, capa_rows, blocks, open_rows, final_rows)
    write_tag_reverse_engineering(capa_rows, blocks, open_rows)

    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"capa option candidates: {len(capa_rows)}")
    print(f"item_option_open blocks: {len(blocks)}")
    print(f"item_option_open non-empty rows: {len(open_rows)}")
    print(f"final candidate rows: {len(final_rows)}")


if __name__ == "__main__":
    main()
