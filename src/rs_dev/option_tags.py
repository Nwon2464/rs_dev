"""Generate canonical UI tags from capa text and preserved source tags."""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_JSON = ROOT / "data/processed/instandard_equipment.json"
DEFAULT_GENERAL_OPEN_CSV = ROOT / "data/processed/equipment_converter_type_options.csv"
DEFAULT_INSTANDARD_OPEN_CSV = ROOT / "data/processed/instandard_open_option_rows.csv"
DEFAULT_CAPA = Path("/mnt/c/game/Red Stone/Data/capa.dat")
DEFAULT_OUTPUT = ROOT / "data/processed/option_tags.json"

GROUPS = {
    "resource": {"ko": "자원", "ja": "リソース"},
    "effect": {"ko": "효과", "ja": "効果"},
    "damage_type": {"ko": "피해 유형", "ja": "ダメージタイプ"},
    "element": {"ko": "속성 원소", "ja": "属性元素"},
    "target": {"ko": "대상", "ja": "対象"},
    "condition": {"ko": "조건", "ja": "条件"},
}

TAG_GROUPS = {
    "HP": "resource", "CP": "resource",
    "스탯": "effect", "피해": "effect", "방어": "effect", "저항": "effect",
    "흡수": "effect", "속도": "effect", "스킬": "effect", "명중": "effect",
    "회피": "effect", "치명타": "effect", "강타": "effect", "상태 이상": "effect",
    "한계 돌파": "effect", "즉사": "effect", "무시": "effect",
    "물리": "damage_type", "마법": "damage_type", "속성": "damage_type",
    "불": "element", "물": "element", "바람": "element", "대지": "element",
    "빛": "element", "어둠": "element",
    "PvP": "target", "소환수/펫": "target", "인간형": "target", "동물형": "target",
    "신수형": "target", "악마형": "target", "언데드형": "target",
    "착용 조건": "condition", "레벨 비례": "condition",
}

JAPANESE_LABELS = {
    "HP": "HP", "CP": "CP", "스탯": "ステータス", "피해": "ダメージ",
    "방어": "防御", "저항": "抵抗", "흡수": "吸収", "속도": "速度",
    "스킬": "スキル", "명중": "命中", "회피": "回避", "치명타": "致命打",
    "강타": "強打", "상태 이상": "状態異常", "한계 돌파": "限界突破",
    "즉사": "即死", "무시": "無視", "물리": "物理", "마법": "魔法",
    "속성": "属性", "불": "火", "물": "水", "바람": "風", "대지": "大地",
    "빛": "光", "어둠": "闇", "PvP": "PvP", "소환수/펫": "召喚獣/ペット",
    "인간형": "人間型", "동물형": "動物型", "신수형": "神獣型",
    "악마형": "悪魔型", "언데드형": "アンデッド型", "착용 조건": "装備条件",
    "레벨 비례": "レベル比例",
}

TAG_ORDER = tuple(TAG_GROUPS)
REMOVED_SOURCE_TAGS = {"자원", "대상", "기타", "소환수"}
TEXT_DISTINGUISHED_TAGS = {"방어", "저항", "치명타", "강타", "마법", "속성"}


def _contains(text: str, *needles: str) -> bool:
    return any(needle.casefold() in text.casefold() for needle in needles)


def canonical_tags(capa_option: Mapping[str, Any], source_tags: Iterable[str]) -> list[str]:
    """Classify one option without changing its source strings or values."""
    text = " ".join(
        str(capa_option.get(field, ""))
        for field in ("name", "description", "short_text")
    )
    compact = re.sub(r"\s+", "", text)
    tags: set[str] = set()

    for source_tag in source_tags:
        if source_tag == "소환수":
            tags.add("소환수/펫")
        elif source_tag in TAG_GROUPS and source_tag not in TEXT_DISTINGUISHED_TAGS:
            tags.add(source_tag)

    if _contains(text, "HP", "체력"): tags.add("HP")
    if _contains(text, "CP", "마나"): tags.add("CP")
    if _contains(text, "힘", "민첩", "건강", "지혜", "지식", "카리스마", "운", "능력치", "기초능력"): tags.add("스탯")
    if _contains(text, "공격력", "대미지", "데미지", "피해"): tags.add("피해")
    if _contains(text, "방어", "피격", "받은 대미지", "받는 대미지", "입은 대미지"): tags.add("방어")
    if _contains(text, "저항"): tags.add("저항")
    if _contains(text, "흡수", "흡혈"): tags.add("흡수")
    if _contains(text, "속도"): tags.add("속도")
    if _contains(text, "스킬"): tags.add("스킬")
    if _contains(text, "명중"): tags.add("명중")
    if _contains(text, "회피"): tags.add("회피")
    if _contains(text, "치명타", "크리티컬"): tags.add("치명타")
    if _contains(text, "강타", "결정타"): tags.add("강타")
    if _contains(text, "상태 이상", "상태이상"): tags.add("상태 이상")
    if _contains(text, "한계 돌파", "한계돌파"): tags.add("한계 돌파")
    if _contains(text, "즉사"): tags.add("즉사")
    if _contains(text, "무시"): tags.add("무시")

    if _contains(text, "물리"): tags.add("물리")
    if _contains(text, "마법"): tags.add("마법")
    if _contains(text, "속성"): tags.add("속성")

    element_patterns = {
        "불": ("불속성", "불 속성", "불저항", "불 저항", "불,"),
        "물": ("물속성", "물 속성", "물저항", "물 저항", "물,"),
        "바람": ("바람속성", "바람 속성", "바람저항", "바람 저항", "바람,"),
        "대지": ("대지속성", "대지 속성", "대지저항", "대지 저항", "대지,"),
        "빛": ("빛속성", "빛 속성", "빛저항", "빛 저항", "빛,"),
        "어둠": ("어둠속성", "어둠 속성", "어둠저항", "어둠 저항", "어둠,"),
    }
    for tag, patterns in element_patterns.items():
        if _contains(text, *patterns) or tag in source_tags:
            tags.add(tag)

    if _contains(text, "pvp"): tags.add("PvP")
    if _contains(text, "소환수", "펫", "조련"): tags.add("소환수/펫")
    for tag, patterns in {
        "인간형": ("인간형", "인간계"), "동물형": ("동물형", "동물계"),
        "신수형": ("신수형", "신수계"), "악마형": ("악마형", "악마계"),
        "언데드형": ("언데드형", "언데드계"),
    }.items():
        if _contains(text, *patterns): tags.add(tag)

    if _contains(compact, "착용레벨", "장착레벨"): tags.add("착용 조건")
    if _contains(compact, "레벨비례", "/레벨", "레벨당") or re.search(r"레벨\s*\[[^]]+\]\s*당", text):
        tags.add("레벨 비례")

    return [tag for tag in TAG_ORDER if tag in tags]


def matches_selected_tags(option_tags: Iterable[str], selected_tags: Iterable[str]) -> bool:
    """Apply OR inside each canonical group and AND between groups."""
    option_values = set(option_tags)
    selected_by_group: dict[str, set[str]] = {}
    for tag in selected_tags:
        group = TAG_GROUPS[tag]
        selected_by_group.setdefault(group, set()).add(tag)
    return all(option_values & group_tags for group_tags in selected_by_group.values())


def collect_option_ids(*csv_paths: Path) -> set[int]:
    result: set[int] = set()
    for path in csv_paths:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            result.update(int(row["option_id"]) for row in csv.DictReader(handle))
    return result


def load_source_tags(path: Path) -> dict[int, list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        int(option["option_id"]): list(option["tags"])
        for option in payload["options"]
    }


def build_option_tags(
    capa: Mapping[int, Mapping[str, Any]],
    source_tags: Mapping[int, list[str]],
    option_ids: Iterable[int],
) -> dict[str, Any]:
    ids = sorted(set(option_ids) | set(source_tags))
    missing = [option_id for option_id in ids if option_id not in capa]
    if missing:
        raise ValueError(f"option ids missing from capa.dat: {missing}")
    return {
        "schema_version": 1,
        "groups": GROUPS,
        "tags": {
            tag: {
                "group": group,
                "labels": {"ko": tag, "ja": JAPANESE_LABELS[tag]},
            }
            for tag, group in TAG_GROUPS.items()
        },
        "options": {
            str(option_id): {
                "source_tags": source_tags.get(option_id, []),
                "canonical_tags": canonical_tags(
                    capa[option_id], source_tags.get(option_id, [])
                ),
            }
            for option_id in ids
        },
    }


def write_option_tags(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
