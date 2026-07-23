#!/usr/bin/env python3
"""Decode Red Stone Data/language/japanese.llt and export key sections.

No third-party package is required. NumPy is used when available for speed.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
from collections import Counter
from pathlib import Path

OFFSET = 0x10
KEY_LENGTH = 326
TARGET_SECTIONS = {22: "baseop", 23: "op", 67: "item_name", 68: "item_text"}


def derive_key(body: bytes) -> bytes:
    try:
        import numpy as np

        arr = np.frombuffer(body, dtype=np.uint8)
        key = np.empty(KEY_LENGTH, dtype=np.uint8)
        for i in range(KEY_LENGTH):
            counts = np.bincount(arr[i::KEY_LENGTH], minlength=256)
            key[i] = counts.argmax()
        return key.tobytes()
    except ImportError:
        counts = [[0] * 256 for _ in range(KEY_LENGTH)]
        for index, value in enumerate(body):
            counts[index % KEY_LENGTH][value] += 1
        return bytes(max(range(256), key=row.__getitem__) for row in counts)


def decrypt(raw: bytes) -> bytes:
    body = raw[OFFSET:]
    key = derive_key(body)
    try:
        import numpy as np

        arr = np.frombuffer(body, dtype=np.uint8)
        key_arr = np.frombuffer(key, dtype=np.uint8)
        decrypted = np.bitwise_xor(arr, np.resize(key_arr, len(arr))).tobytes()
    except ImportError:
        decrypted = bytes(value ^ key[i % KEY_LENGTH] for i, value in enumerate(body))
    return raw[:OFFSET] + decrypted


def decode_text(data: bytes) -> str:
    data = data.split(b"\x00", 1)[0]
    try:
        text = data.decode("cp932", errors="strict")
        if (
            re.search(r"[ｦ-ﾝ]", text) is None
            or "ﾊﾞ" in text
            or re.search(r"[あ-んア-ン]", text)
        ):
            return text
    except UnicodeError:
        pass

    try:
        return data.replace(b"\xff", b"").decode("cp949", errors="strict")
    except UnicodeError:
        return repr(data)


def parse_llt(path: Path) -> tuple[dict[int, dict[int, str]], dict[str, object]]:
    raw = path.read_bytes()
    dec = decrypt(raw)

    idx = OFFSET
    n0, unknown = struct.unpack_from("<2i", dec, idx)
    idx += 8

    sections = {section: {} for section in TARGET_SECTIONS}
    section_counts: Counter[int] = Counter()
    kind_counts: Counter[int] = Counter()
    total_rows = 0

    for _i0 in range(n0):
        n1 = struct.unpack_from("<i", dec, idx)[0]
        idx += 4

        for _i1 in range(n1):
            i2, n2, kind = struct.unpack_from("<3i", dec, idx)
            idx += 12
            kind_counts[kind] += 1

            if kind == 1:
                for i3 in range(2 * n2):
                    slen = struct.unpack_from("<i", dec, idx)[0]
                    idx += 4
                    payload = dec[idx:idx + slen]
                    idx += slen

                    section_counts[i2] += 1
                    total_rows += 1
                    if i2 in sections:
                        sections[i2][i3] = decode_text(payload)
            else:
                for _ in range(n2):
                    i3, _i4, _i5, slen = struct.unpack_from("<4i", dec, idx)
                    idx += 16
                    payload = dec[idx:idx + slen]
                    idx += slen

                    section_counts[i2] += 1
                    total_rows += 1
                    if i2 in sections:
                        sections[i2][i3] = decode_text(payload)

    if idx != len(dec):
        raise ValueError(f"Parser stopped at {idx}, file length is {len(dec)}")

    metadata = {
        "file_size": len(raw),
        "n0": n0,
        "unknown": unknown,
        "key_length": KEY_LENGTH,
        "total_rows": total_rows,
        "kind_counts": dict(kind_counts),
        "complete_consumption": True,
    }
    return sections, metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, default=Path("japanese_llt_output"))
    args = parser.parse_args()

    sections, metadata = parse_llt(args.input)
    args.out.mkdir(parents=True, exist_ok=True)

    for section_id, filename in TARGET_SECTIONS.items():
        mapping = {
            str(key): value
            for key, value in sorted(sections[section_id].items())
        }
        (args.out / f"{filename}.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    (args.out / "summary.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
