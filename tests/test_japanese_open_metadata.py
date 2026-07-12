from __future__ import annotations

import pytest

from rs_dev.japanese_open_metadata import (
    CONVERTER_SPECS, GRADE_SPECS, build_japanese_open_metadata_audit,
    build_production_open_metadata,
)
from rs_dev.models import JapaneseLltRecord


def _record(section: int, text_id: int, text: str) -> JapaneseLltRecord:
    return JapaneseLltRecord(section_id=section, text_id=text_id, variant_id=0, sub_variant_id=0, text=text, kind=0)


def _report(*, omit_description: str | None = None):
    records = [_record(66, i, text) for i, text in enumerate(
        ["ノーマル", "ノーマル DX", "ノーマル ULT", "ユニーク", "DX ユニーク", "ULT ユニーク"], start=9)]
    for concept, (_, text_id, name) in CONVERTER_SPECS.items():
        records.append(_record(67, text_id, name))
        if concept != omit_description:
            records.append(_record(68, text_id, "解放オプションを変換する説明"))
    return build_japanese_open_metadata_audit(
        records, {f"{code}:{spec[0]}": 1 for code, spec in GRADE_SPECS.items()},
        {"일반 변환기": 1, "개량된 변환기": 1, "모조 변환기": 1, "불타는 변환기": 1, "협회 변환기": 1},
        {"일반": 1, "개량": 1, "모조": 1, "불타는": 1}, {},
        japanese_llt_source="fixture.llt", general_csv_source="general.csv",
        instandard_csv_source="instandard.csv", current_ui_source="index.ts")


def test_required_coverage_and_production_schema() -> None:
    report = _report()
    assert {r.internal_key for r in report.results if r.category == "grade"} == {"7", "8", "9"}
    assert {r.internal_key for r in report.results if r.category == "converter"} == set(CONVERTER_SPECS)
    assert len({(r.category, r.internal_key) for r in report.results}) == 8
    assert all(r.section_id is not None and r.text_id is not None for r in report.results)
    converters = [r for r in report.results if r.category == "converter"]
    assert all(r.description_section_id == 68 and r.description_text_id == r.text_id for r in converters)
    payload = build_production_open_metadata(report)
    assert set(payload) == {"grades", "converters"}
    assert set(payload["grades"]) == {"7", "8", "9"}
    assert set(payload["converters"]) == set(CONVERTER_SPECS)
    assert all(value.strip() for group in payload.values() for value in group.values())


def test_missing_description_refuses_production() -> None:
    report = _report(omit_description="burning")
    assert report.summary.missing_count == 1
    assert not report.summary.production_export_eligible
    with pytest.raises(ValueError, match="export refused"):
        build_production_open_metadata(report)
