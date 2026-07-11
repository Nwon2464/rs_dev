from __future__ import annotations

import json

import pytest

from rs_dev.japanese_base_options import (
    build_japanese_base_options,
    write_japanese_base_options,
)
from rs_dev.models import JapaneseLltRecord


def _record(text_id: int, text: str, *, section_id: int = 22) -> JapaneseLltRecord:
    return JapaneseLltRecord(
        section_id=section_id,
        text_id=text_id,
        variant_id=0,
        sub_variant_id=0,
        text=text,
        kind=0,
    )


def test_export_mapping_contains_only_section_22_in_numeric_order() -> None:
    templates = build_japanese_base_options(
        [
            _record(721, "武器最小攻撃力 +[0]"),
            _record(1, "別セクション", section_id=23),
            _record(63, "力 +[0]"),
            _record(736, "このアイテムの着用レベル [-0]"),
        ]
    )

    assert list(templates) == [63, 721, 736]
    assert len(templates) == 3


def test_writer_preserves_japanese_utf8_and_json_key_order(tmp_path) -> None:
    path = tmp_path / "base_options.json"
    templates = {63: "力 +[0]", 721: "武器最小攻撃力 +[0]"}

    write_japanese_base_options(path, templates)

    raw = path.read_bytes()
    assert "力 +[0]".encode() in raw
    assert b"\\u" not in raw
    parsed = json.loads(raw)
    assert list(parsed) == ["63", "721"]
    assert parsed["721"] == "武器最小攻撃力 +[0]"


def test_duplicate_section_22_text_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate.*text_id=63"):
        build_japanese_base_options(
            [_record(63, "力 +[0]"), _record(63, "力 +[0]")]
        )
