from __future__ import annotations

import struct

import pytest
from pydantic import ValidationError

import rs_dev.parsers.japanese_llt as japanese_llt_parser
from rs_dev.models import JapaneseLltRecord
from rs_dev.parsers import (
    decode_llt_text,
    decrypt_llt_body,
    estimate_xor_key,
    parse_japanese_llt,
    parse_llt_structure,
)


def _i32(*values: int) -> bytes:
    return struct.pack(f"<{len(values)}i", *values)


def _payload(text: str, encoding: str) -> bytes:
    encoded = text.encode(encoding) + b"\x00"
    return _i32(len(encoded)) + encoded


def _decrypted_fixture(*, trailing_payload_zeros: int = 0) -> bytes:
    data = bytearray(16)
    data.extend(_i32(1, 12))
    data.extend(_i32(2))

    data.extend(_i32(7, 2, 0))
    data.extend(_i32(10, 2, 3))
    data.extend(_payload("力 +[0]", "cp932"))
    data.extend(_i32(11, 4, 5))
    data.extend(_payload("장비", "cp949"))

    data.extend(_i32(9, 1, 1))
    data.extend(_payload("名前", "cp932"))
    final_payload = "説明".encode("cp932") + b"\x00"
    final_payload += b"\x00" * trailing_payload_zeros
    data.extend(_i32(len(final_payload)))
    data.extend(final_payload)
    return bytes(data)


def test_xor_key_estimation_and_body_decryption() -> None:
    xor_key = b"\x13\x57\x9b\xdf"
    plaintext = bytearray(len(xor_key) * 20)
    for index in range(len(xor_key)):
        plaintext[index] = index + 1
    encrypted = bytes(
        value ^ xor_key[index % len(xor_key)]
        for index, value in enumerate(plaintext)
    )

    assert estimate_xor_key(encrypted, key_length=len(xor_key)) == xor_key
    assert decrypt_llt_body(encrypted, xor_key) == bytes(plaintext)


def test_text_decoder_prefers_cp932_and_falls_back_to_cp949() -> None:
    assert decode_llt_text("名前".encode("cp932") + b"\x00ignored") == "名前"
    assert decode_llt_text("장비".encode("cp949") + b"\x00") == "장비"


def test_structure_parser_returns_all_kinds_and_identifiers() -> None:
    records = parse_llt_structure(_decrypted_fixture())

    assert records == [
        JapaneseLltRecord(
            section_id=7,
            text_id=10,
            variant_id=2,
            sub_variant_id=3,
            text="力 +[0]",
            kind=0,
        ),
        JapaneseLltRecord(
            section_id=7,
            text_id=11,
            variant_id=4,
            sub_variant_id=5,
            text="장비",
            kind=0,
        ),
        JapaneseLltRecord(
            section_id=9,
            text_id=0,
            variant_id=None,
            sub_variant_id=None,
            text="名前",
            kind=1,
        ),
        JapaneseLltRecord(
            section_id=9,
            text_id=1,
            variant_id=None,
            sub_variant_id=None,
            text="説明",
            kind=1,
        ),
    ]


def test_structure_parser_rejects_trailing_and_truncated_bytes() -> None:
    with pytest.raises(ValueError, match="parser stopped"):
        parse_llt_structure(_decrypted_fixture() + b"\x00")
    with pytest.raises(ValueError, match="truncated LLT"):
        parse_llt_structure(_decrypted_fixture()[:-1])


def test_file_parser_rejects_too_short_input(tmp_path) -> None:
    path = tmp_path / "sample.llt"
    path.write_bytes(b"\x00" * 32)

    with pytest.raises(ValueError, match="too short to estimate"):
        parse_japanese_llt(path)


def test_file_parser_reads_an_artificial_encrypted_file(
    tmp_path, monkeypatch
) -> None:
    decrypted = _decrypted_fixture(trailing_payload_zeros=326)
    xor_key = bytes(index % 256 for index in range(326))
    encrypted = decrypted[:16] + decrypt_llt_body(decrypted[16:], xor_key)
    path = tmp_path / "sample.llt"
    path.write_bytes(encrypted)
    monkeypatch.setattr(japanese_llt_parser, "estimate_xor_key", lambda _body: xor_key)

    records = parse_japanese_llt(path)

    assert len(records) == 4
    assert records[-1].text == "説明"


def test_record_model_rejects_variant_fields_for_kind_one() -> None:
    with pytest.raises(ValidationError, match="do not contain variant fields"):
        JapaneseLltRecord(
            section_id=1,
            text_id=2,
            variant_id=0,
            sub_variant_id=0,
            text="invalid",
            kind=1,
        )
