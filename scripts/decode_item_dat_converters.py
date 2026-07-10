#!/usr/bin/env python3
"""Decode item.dat with the discovered 326-byte mask and extract converter strings."""

from __future__ import annotations

import csv
import json
import re
import struct
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/mnt/c/game/Red Stone/Data/item.dat")
OUT = ROOT / "data" / "processed"

HEADER_SIZE = 0x46
RECORD_SIZE = 326
KEY_SAMPLE_RECORDS = 50000

TARGET_TERMS = (
    "개방 옵션 변환기",
    "개선된 개방 옵션 변환기",
    "모조 개방 옵션 변환기",
    "개방 옵션 변환기[협회]",
)

EFFECT_ID_LABELS = {
    920: "개방옵션변환창생성",
    935: "개방옵션변환창생성2 / 개선된",
    954: "개방옵션변환창생성3 / 모조",
    966: "개방옵션변환창생성4 / 협회 제외",
    1020: "개방옵션변환창생성5 / 향상된",
}


def clean_text(value: str) -> str:
    value = value.replace("\ufffd", "")
    value = "".join(ch for ch in value if ch >= " " or ch in "\t\r\n")
    value = re.sub(r"[\x00\s]+", " ", value).strip()
    return value


def derive_mask(payload: bytes) -> bytes:
    sample = payload[: RECORD_SIZE * KEY_SAMPLE_RECORDS]
    return bytes(
        Counter(sample[offset::RECORD_SIZE]).most_common(1)[0][0]
        for offset in range(RECORD_SIZE)
    )


def decode_payload(payload: bytes, mask: bytes) -> bytes:
    return bytes(byte ^ mask[index % RECORD_SIZE] ^ 0xFF for index, byte in enumerate(payload))


def iter_record_strings(body: bytes):
    for record_index in range(len(body) // RECORD_SIZE):
        record = body[record_index * RECORD_SIZE : (record_index + 1) * RECORD_SIZE]
        offset = 0
        for raw in record.split(b"\x00"):
            if len(raw) >= 2:
                text = clean_text(raw.decode("cp949", "replace"))
                if text and (
                    any("\uac00" <= ch <= "\ud7a3" for ch in text)
                    or "Nx" in text
                    or "NX" in text
                ):
                    yield {
                        "record_index": record_index,
                        "record_file_offset_hex": hex(HEADER_SIZE + record_index * RECORD_SIZE),
                        "string_offset_in_record": offset,
                        "text": text,
                    }
            offset += len(raw) + 1


def classify(text: str) -> str:
    if "협회" in text:
        return "excluded_association"
    if len(text) > 80 or "패키지" in text or "상자" in text or "획득" in text:
        return "context_or_package_text"
    if "변환기" in text:
        return "item_name_candidate"
    return "context"


def nearby_effect_ids(body: bytes, record_index: int) -> list[dict]:
    start_record = max(0, record_index - 1)
    end_record = min(len(body) // RECORD_SIZE, record_index + 2)
    region_start = start_record * RECORD_SIZE
    region = body[region_start : end_record * RECORD_SIZE]

    hits = []
    for effect_id, label in EFFECT_ID_LABELS.items():
        needle = struct.pack("<I", effect_id)
        cursor = 0
        while True:
            pos = region.find(needle, cursor)
            if pos < 0:
                break
            absolute = region_start + pos
            hits.append(
                {
                    "effect_id": effect_id,
                    "effect_label": label,
                    "nearby_record_index": absolute // RECORD_SIZE,
                    "nearby_offset_in_record": absolute % RECORD_SIZE,
                    "nearby_file_offset_hex": hex(HEADER_SIZE + absolute),
                }
            )
            cursor = pos + 1
    return hits


def main() -> None:
    data = SOURCE.read_bytes()
    payload = data[HEADER_SIZE:]
    mask = derive_mask(payload)
    body = decode_payload(payload, mask)

    all_rows = []
    short_candidates = {}

    for row in iter_record_strings(body):
        text = row["text"]
        if "변환기" not in text:
            continue
        matched_terms = [term for term in TARGET_TERMS if term in text]
        row = {
            **row,
            "matched_terms": "|".join(matched_terms),
            "classification": classify(text),
            "nearby_effect_ids": nearby_effect_ids(body, row["record_index"]),
        }
        all_rows.append(row)
        if row["classification"] in {"item_name_candidate", "excluded_association"} and len(text) <= 80:
            short_candidates.setdefault(text, []).append(row)

    summary = {
        "source": str(SOURCE),
        "header_size": HEADER_SIZE,
        "record_mask_size": RECORD_SIZE,
        "decode_formula": "plain_byte = cipher_byte XOR mask[offset % 326] XOR 0xFF",
        "total_converter_string_rows": len(all_rows),
        "unique_short_converter_strings": {
            text: {
                "count": len(rows),
                "classification": rows[0]["classification"],
                "nearby_effect_ids": rows[0]["nearby_effect_ids"],
                "examples": rows[:5],
            }
            for text, rows in sorted(short_candidates.items())
        },
        "not_found_exact_names": [
            "불타는 개방 옵션 변환기",
            "향상된 개방 옵션 변환기",
            "약화된 개방 옵션 변환기",
            "개량된 개방 옵션 변환기",
        ],
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "item_dat_converter_records.json").write_text(
        json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "item_dat_converter_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (OUT / "item_dat_converter_records.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "record_index",
                "record_file_offset_hex",
                "string_offset_in_record",
                "text",
                "matched_terms",
                "classification",
                "nearby_effect_ids",
            ],
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
