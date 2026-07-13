from __future__ import annotations

import pytest

from rs_dev.open_options.catalogs.equipment_buckets import (
    build_japanese_open_bucket_audit,
    build_production_open_buckets,
)
from rs_dev.models import JapaneseLltRecord
from rs_dev.open_options import BUCKET_BY_GROUP_IDS


def _record(text_id: int, text: str, *, section_id: int = 137) -> JapaneseLltRecord:
    return JapaneseLltRecord(
        section_id=section_id,
        text_id=text_id,
        variant_id=0,
        sub_variant_id=0,
        text=text,
        kind=0,
    )


def _inputs():
    ids = {group_id for group_ids in BUCKET_BY_GROUP_IDS for group_id in group_ids}
    korean = {group_id: f"한국어{group_id}" for group_id in ids}
    japanese = {group_id: f"日本語{group_id}" for group_id in ids}
    japanese.update(
        {
            2: "グローブ",
            5: "ブレスレット",
            6: "ベルト",
            8: "ネックレス",
            10: "イヤリング",
            11: "マント",
        }
    )
    csv_counts = {bucket_name: 1 for bucket_name in BUCKET_BY_GROUP_IDS.values()}
    category_records = [
        _record(0, "武器"),
        _record(1, "盾"),
        _record(2, "鎧"),
        _record(3, "グローブ"),
        _record(4, "イヤリング"),
        _record(5, "ネックレス"),
        _record(6, "ベルト"),
    ]
    return korean, japanese, csv_counts, category_records


def _build(records: list[JapaneseLltRecord]):
    korean, japanese, csv_counts, _ = _inputs()
    return build_japanese_open_bucket_audit(
        records,
        korean,
        japanese,
        csv_counts,
        japanese_llt_source="fixture.llt",
        equipment_groups_source="equipment_groups.json",
        csv_source="rows.csv",
    )


def test_direct_composite_and_semantic_buckets_cover_csv() -> None:
    _, _, csv_counts, records = _inputs()
    report = _build(records)

    assert report.summary.csv_coverage_complete
    assert report.summary.actual_bucket_count == len(csv_counts)
    assert report.summary.direct_single_group_count == 8
    assert report.summary.composable_multi_group_count == 2
    assert report.summary.semantic_category_count == 1
    assert report.summary.confirmed_count == 11

    helmet = next(row for row in report.results if row.ko_bucket_name == "헬멧")
    assert helmet.source_type == "section_163_direct_id"
    assert helmet.source_text_id == 0

    gloves = next(
        row for row in report.results if row.ko_bucket_name == "장갑/팔찌"
    )
    assert gloves.constituent_ja_names == ["グローブ", "ブレスレット"]
    assert gloves.ja_candidate == "グローブ/ブレスレット"

    weapon = next(row for row in report.results if row.ko_bucket_name == "무기")
    assert weapon.strategy == "verified_semantic_label"
    assert weapon.source_section_id == 137
    assert weapon.source_text_id == 0
    assert weapon.ja_candidate == "武器"

    production = build_production_open_buckets(report)
    assert set(production) == set(csv_counts)
    assert all(value.strip() for value in production.values())


def test_unresolved_semantic_bucket_refuses_production_export() -> None:
    report = _build([_record(0, "武器")])

    assert report.summary.ambiguous_count == 1
    assert not report.summary.production_export_eligible
    with pytest.raises(ValueError, match="export refused"):
        build_production_open_buckets(report)
