from __future__ import annotations

import pytest

from rs_dev.open_options.catalogs.equipment_groups import (
    build_japanese_equipment_group_audit,
    build_production_equipment_groups,
)
from rs_dev.models import JapaneseLltRecord


def _section(section_id: int, count: int = 84) -> list[JapaneseLltRecord]:
    return [
        JapaneseLltRecord(
            section_id=section_id,
            text_id=text_id,
            variant_id=0,
            sub_variant_id=0,
            text=f"日本語原文{text_id}",
            kind=0,
        )
        for text_id in range(count)
    ]


def _build(records: list[JapaneseLltRecord]):
    korean_groups = {group_id: f"한국어{group_id}" for group_id in range(84)}
    current_ui_groups = {group_id: korean_groups[group_id] for group_id in (0, 1, 17)}
    return build_japanese_equipment_group_audit(
        records,
        korean_groups,
        current_ui_groups,
        japanese_llt_source="fixture.llt",
        korean_group_source="simpleGameText.dat",
        current_ui_source="instandard_equipment.json",
    )


def test_direct_section_preserves_coverage_and_exports_unique_ids() -> None:
    report = _build(_section(163))

    assert report.likely_section_id == 163
    assert report.summary.section_count == 1
    assert report.summary.korean_group_count == 84
    assert report.summary.current_ui_group_count == 3
    assert report.summary.confirmed_direct_id_count == 84
    assert report.summary.ambiguous_count == 0
    assert report.summary.missing_count == 0
    assert all(row.section_id == 163 for row in report.results)
    assert all(row.text_id == row.item_group_id for row in report.results)

    production = build_production_equipment_groups(report)
    assert len(production) == 84
    assert len(production) == len(set(production))
    assert production[0] == "日本語原文0"


def test_ambiguous_direct_sections_refuse_production_export() -> None:
    report = _build(_section(160) + _section(163))

    assert report.likely_section_id is None
    assert report.summary.ambiguous_count == 84
    assert not report.summary.production_export_eligible
    with pytest.raises(ValueError, match="export refused"):
        build_production_equipment_groups(report)


def test_missing_group_refuses_production_export() -> None:
    report = _build(_section(163, count=83))

    assert report.summary.missing_count == 84
    assert not report.summary.production_export_eligible
    with pytest.raises(ValueError, match="export refused"):
        build_production_equipment_groups(report)
