"""Strict parser for Red Stone japanese.llt language files."""

from __future__ import annotations

import re
import struct
from pathlib import Path

from rs_dev.models import JapaneseLltRecord


ENCRYPTED_BODY_OFFSET = 0x10
XOR_KEY_LENGTH = 326

_HALFWIDTH_KATAKANA = re.compile(r"[ｦ-ﾝ]")
_JAPANESE_TEXT = re.compile(r"[あ-んア-ン]")


def estimate_xor_key(
    encrypted_body: bytes, *, key_length: int = XOR_KEY_LENGTH
) -> bytes:
    """Estimate a repeating XOR key from the most common byte at each position."""
    if key_length <= 0:
        raise ValueError("XOR key length must be positive")
    if len(encrypted_body) < key_length:
        raise ValueError(
            f"encrypted LLT body is shorter than XOR key length {key_length}"
        )

    counts = [[0] * 256 for _ in range(key_length)]
    for index, value in enumerate(encrypted_body):
        counts[index % key_length][value] += 1
    return bytes(max(range(256), key=row.__getitem__) for row in counts)


def decrypt_llt_body(encrypted_body: bytes, xor_key: bytes) -> bytes:
    """Decrypt an LLT body with a repeating XOR key."""
    if not xor_key:
        raise ValueError("XOR key must not be empty")
    return bytes(
        value ^ xor_key[index % len(xor_key)]
        for index, value in enumerate(encrypted_body)
    )


def decode_llt_text(payload: bytes) -> str:
    """Decode one null-terminated LLT payload, preferring CP932 over CP949."""
    encoded = payload.split(b"\x00", 1)[0]
    try:
        text = encoded.decode("cp932", errors="strict")
        if (
            _HALFWIDTH_KATAKANA.search(text) is None
            or "ﾊﾞ" in text
            or _JAPANESE_TEXT.search(text)
        ):
            return text
    except UnicodeDecodeError:
        pass

    try:
        return encoded.replace(b"\xff", b"").decode("cp949", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("LLT text is neither valid CP932 nor CP949") from error


def _read_i32(data: bytes, offset: int, label: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"truncated LLT {label} at {offset:#x}")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def _read_payload(
    data: bytes, offset: int, length: int, label: str
) -> tuple[bytes, int]:
    if length < 0:
        raise ValueError(f"negative LLT string length {length} at {offset:#x}")
    end = offset + length
    if end > len(data):
        raise ValueError(f"truncated LLT {label} at {offset:#x}")
    return data[offset:end], end


def parse_llt_structure(
    decrypted_data: bytes, *, body_offset: int = ENCRYPTED_BODY_OFFSET
) -> list[JapaneseLltRecord]:
    """Parse all text records from a fully decrypted LLT byte sequence."""
    if body_offset < 0:
        raise ValueError("LLT body offset must not be negative")
    if len(decrypted_data) < body_offset + 8:
        raise ValueError("LLT file is too short for its decrypted header")

    cursor = body_offset
    outer_count, cursor = _read_i32(decrypted_data, cursor, "outer count")
    _unknown, cursor = _read_i32(decrypted_data, cursor, "header value")
    if outer_count < 0:
        raise ValueError(f"negative LLT outer count {outer_count}")

    records: list[JapaneseLltRecord] = []
    for outer_index in range(outer_count):
        section_count, cursor = _read_i32(
            decrypted_data, cursor, f"section count for outer {outer_index}"
        )
        if section_count < 0:
            raise ValueError(
                f"negative LLT section count {section_count} for outer {outer_index}"
            )

        for section_index in range(section_count):
            section_id, cursor = _read_i32(
                decrypted_data, cursor, f"section id for outer {outer_index}"
            )
            record_count, cursor = _read_i32(
                decrypted_data, cursor, f"record count for section {section_index}"
            )
            kind, cursor = _read_i32(
                decrypted_data, cursor, f"kind for section {section_index}"
            )
            if record_count < 0:
                raise ValueError(
                    f"negative LLT record count {record_count} "
                    f"for section {section_id}"
                )

            if kind == 1:
                for text_id in range(2 * record_count):
                    length, cursor = _read_i32(
                        decrypted_data,
                        cursor,
                        f"string length for section {section_id} text {text_id}",
                    )
                    payload, cursor = _read_payload(
                        decrypted_data,
                        cursor,
                        length,
                        f"string for section {section_id} text {text_id}",
                    )
                    records.append(
                        JapaneseLltRecord(
                            section_id=section_id,
                            text_id=text_id,
                            variant_id=None,
                            sub_variant_id=None,
                            text=decode_llt_text(payload),
                            kind=kind,
                        )
                    )
                continue

            for record_index in range(record_count):
                text_id, cursor = _read_i32(
                    decrypted_data,
                    cursor,
                    f"text id for section {section_id} record {record_index}",
                )
                variant_id, cursor = _read_i32(
                    decrypted_data,
                    cursor,
                    f"variant id for section {section_id} record {record_index}",
                )
                sub_variant_id, cursor = _read_i32(
                    decrypted_data,
                    cursor,
                    f"sub-variant id for section {section_id} record {record_index}",
                )
                length, cursor = _read_i32(
                    decrypted_data,
                    cursor,
                    f"string length for section {section_id} record {record_index}",
                )
                payload, cursor = _read_payload(
                    decrypted_data,
                    cursor,
                    length,
                    f"string for section {section_id} record {record_index}",
                )
                records.append(
                    JapaneseLltRecord(
                        section_id=section_id,
                        text_id=text_id,
                        variant_id=variant_id,
                        sub_variant_id=sub_variant_id,
                        text=decode_llt_text(payload),
                        kind=kind,
                    )
                )

    if cursor != len(decrypted_data):
        raise ValueError(
            f"japanese.llt parser stopped at {cursor}, "
            f"file length is {len(decrypted_data)}"
        )
    return records


def parse_japanese_llt(path: Path) -> list[JapaneseLltRecord]:
    """Decrypt and parse every text record from a japanese.llt file."""
    raw = path.read_bytes()
    if len(raw) < ENCRYPTED_BODY_OFFSET + XOR_KEY_LENGTH:
        raise ValueError("japanese.llt is too short to estimate its XOR key")
    encrypted_body = raw[ENCRYPTED_BODY_OFFSET:]
    xor_key = estimate_xor_key(encrypted_body)
    decrypted = raw[:ENCRYPTED_BODY_OFFSET] + decrypt_llt_body(
        encrypted_body, xor_key
    )
    return parse_llt_structure(decrypted)
