from __future__ import annotations

import pytest

from rs_dev.open_options.catalogs.option_tags import (
    GROUPS,
    JAPANESE_LABELS,
    TAG_GROUPS,
    build_option_tag_audit,
    canonical_tag_evidence,
    canonical_tags,
    matches_selected_tags,
)


@pytest.mark.parametrize(
    "option_id,name,description,short_text,expected",
    [
        (803, "적에게입힌대미지의일부체력으로흡수", "흡혈 [수치]0％", "흡혈 +[0％]", ["HP", "주는 피해", "흡수"]),
        (804, "적에게입힌마법대미지의일부체력으로흡수", "마법 대미지의 일부를 체력으로 흡수", "마법 대미지 흡수", ["HP", "주는 피해", "흡수", "마법"]),
        (460, "기본물리공격력증가P", "물리 공격력 증가", "물리 공격력 증가", ["공격력", "물리"]),
        (463, "치명타대미지증가", "물리 치명타 대미지 증가", "물리 치명타 대미지 증가", ["주는 피해", "치명타", "물리"]),
        (466, "더블크리티컬대미지감소", "받는 물리 더블 크리티컬 대미지 감소", "받는 물리 더블 크리티컬 대미지 감소", ["받는 피해", "방어", "치명타", "물리"]),
        (657, "받는피해감소P", "받는 대미지 감소", "받는 대미지 감소", ["받는 피해", "방어"]),
        (789, "마법대미지흡수", "마법 대미지 흡수", "마법 속성 대미지 흡수", ["받는 피해", "흡수", "마법", "속성"]),
        (651, "vs언데드악마_물리대미지증가P", "vs 언데드, 악마 물리 대미지 증가", "", ["주는 피해", "물리", "악마형", "언데드형"]),
        (652, "vs동물신수_물리대미지증가P", "vs 동물, 신수 물리 대미지 증가", "", ["주는 피해", "물리", "동물형", "신수형"]),
        (654, "vs동물신수_마법대미지증가P", "vs 동물, 신수 마법 대미지 증가", "", ["주는 피해", "마법", "동물형", "신수형"]),
        (832, "vs언데드_마법물리피격대미지감소P", "vs 언데드 물리, 마법 대미지 감소", "vs 언데드 받는 대미지 감소", ["받는 피해", "방어", "물리", "마법", "언데드형"]),
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


@pytest.mark.parametrize("name", ["마법 아이템 드랍 확률", "유니크 아이템 드랍 확률"])
def test_source_drop_tag_is_normalized_to_drop_without_damage_type(name: str) -> None:
    option = {"name": name, "description": "", "short_text": ""}
    assert canonical_tags(option, ["출현"]) == ["드롭"]


def test_broad_source_damage_tag_does_not_override_text_semantics() -> None:
    option = {
        "name": "타겟의마법저항약화",
        "description": "적의 마법 저항 감소",
        "short_text": "마법 저항",
    }
    assert canonical_tags(option, ["피해", "속성"]) == ["저항", "마법"]


def test_decrease_alone_does_not_imply_defense() -> None:
    option = {"name": "레벨감소", "description": "레벨 감소", "short_text": "레벨 -[0]"}
    assert "방어" not in canonical_tags(option, ["방어"])


def test_same_group_is_or_and_different_groups_are_and() -> None:
    option_tags = ["HP", "주는 피해", "물리"]
    assert matches_selected_tags(option_tags, ["HP", "CP"])
    assert matches_selected_tags(option_tags, ["공격력", "주는 피해", "물리"])
    assert not matches_selected_tags(option_tags, ["HP", "마법"])


def test_tag_evidence_and_audit_cover_every_decision() -> None:
    option = {
        "name": "기본물리공격력증가P",
        "description": "물리 공격력 증가",
        "short_text": "물리 공격력 증가",
    }
    evidence = canonical_tag_evidence(option, ["피해", "물리"])
    assert evidence == {
        "공격력": ["text:공격력"],
        "물리": ["source_tag:물리", "text:물리"],
    }
    audit = build_option_tag_audit({460: option}, {460: ["피해", "물리"]}, [460])
    assert audit["summary"]["untagged_count"] == 0
    assert audit["options"]["460"]["evidence"] == evidence


def test_every_tag_and_group_has_korean_and_japanese_labels() -> None:
    assert set(JAPANESE_LABELS) == set(TAG_GROUPS)
    assert all(tag.strip() and JAPANESE_LABELS[tag].strip() for tag in TAG_GROUPS)
    assert all(labels["ko"].strip() and labels["ja"].strip() for labels in GROUPS.values())
