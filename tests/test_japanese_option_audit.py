from __future__ import annotations

import json

import pytest

from rs_dev.japanese_option_audit import (
    build_japanese_option_audit,
    collect_current_option_ids,
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


def test_all_current_option_ids_match_japanese_templates() -> None:
    report = build_japanese_option_audit(
        {63, 64},
        [_record(63, "力 +[0]"), _record(64, "知恵 +[0]")],
        current_option_source="fixture",
    )

    assert report.summary.model_dump() == {
        "current_option_count": 2,
        "japanese_section_22_count": 2,
        "matched_count": 2,
        "missing_count": 0,
        "unused_count": 0,
    }
    assert [row.option_id for row in report.matched] == [63, 64]


def test_report_separates_missing_and_unused_ids() -> None:
    report = build_japanese_option_audit(
        {63, 99},
        [_record(63, "力 +[0]"), _record(100, "未使用")],
        current_option_source="fixture",
    )

    assert report.missing_in_japanese == [99]
    assert [row.option_id for row in report.unused_japanese] == [100]
    assert report.summary.matched_count == 1
    assert report.summary.missing_count == 1
    assert report.summary.unused_count == 1


@pytest.mark.parametrize(
    "second_text, message",
    [
        ("力 +[0]", "duplicate.*text_id=63"),
        ("別のテンプレート", "conflicting.*text_id=63"),
    ],
)
def test_duplicate_or_conflicting_section_22_ids_are_rejected(
    second_text: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        build_japanese_option_audit(
            {63},
            [_record(63, "力 +[0]"), _record(63, second_text)],
            current_option_source="fixture",
        )


def test_current_option_ids_are_collected_from_equipment_assignments(
    tmp_path,
) -> None:
    path = tmp_path / "instandard_equipment.json"
    path.write_text(
        json.dumps(
            {
                "equipment": [
                    {"option_ids": [64, 63]},
                    {"option_ids": [63]},
                ],
                "options": [
                    {"option_id": 63, "selectable": True},
                    {"option_id": 64, "selectable": True},
                    {"option_id": 65, "selectable": False},
                ],
            }
        ),
        encoding="utf-8",
    )

    assert collect_current_option_ids(path) == {63, 64}
