"""Observed general-equipment signatures and their stable internal buckets."""

from __future__ import annotations


BUCKET_BY_GROUP_IDS: dict[tuple[int, ...], str] = {
    (18, 20, 21, 22, 23, 24, 25, 26, 28, 30, 32, 33, 54, 55, 56, 57, 58, 61, 63, 68, 70, 80, 82): "무기",
    (29,): "피리",
    (16,): "공용 갑옷",
    (17,): "전용 갑옷",
    (10, 11): "귀걸이/망토",
    (0,): "헬멧",
    (1,): "관",
    (6,): "벨트",
    (2, 5): "장갑/팔찌",
    (7,): "부츠",
    (8,): "목걸이",
}


def group_names_for_signature(
    group_ids: tuple[int, ...], group_names: dict[int, str]
) -> tuple[str, ...]:
    missing = [group_id for group_id in group_ids if group_id not in group_names]
    if missing:
        raise ValueError(f"unmapped item group IDs: {missing}")
    return tuple(group_names[group_id] for group_id in group_ids)
