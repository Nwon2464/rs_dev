from __future__ import annotations

import pytest

from rs_dev.open_options.catalogs.option_tags import (
    GROUPS,
    JAPANESE_LABELS,
    TAG_GROUPS,
    canonical_tags,
    matches_selected_tags,
)


@pytest.mark.parametrize(
    "option_id,name,description,short_text,expected",
    [
        (803, "적에게입힌대미지의일부체력으로흡수", "흡혈 [수치]0％", "흡혈 +[0％]", ["HP", "피해", "흡수"]),
        (804, "적에게입힌마법대미지의일부체력으로흡수", "마법 대미지의 일부를 체력으로 흡수", "마법 대미지 흡수", ["HP", "피해", "흡수", "마법"]),
        (736, "현아이템착용레벨감소", "이 아이템의 착용 레벨 감소", "착용 레벨 감소", ["착용 조건"]),
        (462, "강타확률증가", "물리 강타 확률 증가", "물리 강타", ["강타", "물리"]),
        (194, "타겟의마법저항약화", "적의 마법 저항 감소", "마법 저항", ["저항", "마법"]),
        (79, "불저항", "불 속성 저항 증가", "불 속성 저항", ["저항", "속성", "불"]),
        (72, "명중률증가", "물리 명중률 증가", "물리 명중", ["명중", "물리"]),
        (109, "모든스킬레벨증가", "모든 스킬 레벨 증가", "모든 스킬", ["스킬"]),
        (110, "회피율증가", "물리 회피율 증가", "물리 회피", ["회피", "물리"]),
    ],
)
def test_regression_canonical_tags(option_id, name, description, short_text, expected) -> None:
    option = {"option_id": option_id, "name": name, "description": description, "short_text": short_text}
    assert canonical_tags(option, []) == expected


def test_source_tags_are_normalized_without_broad_fallback_tags() -> None:
    option = {"name": "소환수 HP", "description": "", "short_text": ""}
    tags = canonical_tags(option, ["소환수", "자원", "대상", "기타"])
    assert tags == ["HP", "소환수/펫"]
    assert not ({"자원", "대상", "기타", "소환수"} & set(TAG_GROUPS))


def test_decrease_alone_does_not_imply_defense() -> None:
    option = {"name": "레벨감소", "description": "레벨 감소", "short_text": "레벨 -[0]"}
    assert "방어" not in canonical_tags(option, ["방어"])


def test_same_group_is_or_and_different_groups_are_and() -> None:
    option_tags = ["HP", "피해", "물리"]
    assert matches_selected_tags(option_tags, ["HP", "CP"])
    assert matches_selected_tags(option_tags, ["피해", "방어", "물리"])
    assert not matches_selected_tags(option_tags, ["HP", "마법"])


def test_every_tag_and_group_has_korean_and_japanese_labels() -> None:
    assert set(JAPANESE_LABELS) == set(TAG_GROUPS)
    assert all(tag.strip() and JAPANESE_LABELS[tag].strip() for tag in TAG_GROUPS)
    assert all(labels["ko"].strip() and labels["ja"].strip() for labels in GROUPS.values())
