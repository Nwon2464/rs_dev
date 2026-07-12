"""Evidence-based audit pipeline for Japanese equipment-group names."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path

from rs_dev.models import (
    JapaneseEquipmentGroupAuditReport,
    JapaneseEquipmentGroupAuditRow,
    JapaneseEquipmentGroupAuditSummary,
    JapaneseEquipmentSectionAudit,
    JapaneseLltRecord,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT_OUTPUT = (
    ROOT / "data" / "processed" / "i18n" / "ja" / "equipment_groups_audit.json"
)
DEFAULT_PRODUCTION_OUTPUT = (
    ROOT / "web" / "public" / "data" / "i18n" / "ja" / "equipment_groups.json"
)

SEARCH_HINTS = (
    "ヘルメット",
    "冠",
    "手袋",
    "グローブ",
    "腕輪",
    "ベルト",
    "ブーツ",
    "ネックレス",
    "イヤリング",
    "マント",
    "鎧",
    "武器",
)
_SENTENCE_MARKS = re.compile(r"[。！？\n\r]")


def collect_current_ui_groups(path: Path) -> dict[int, str]:
    """Load the item groups currently present in the processed UI dataset."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    groups: dict[int, str] = {}
    for row in payload["equipment"]:
        group_id = int(row["item_group_id"])
        if group_id in groups:
            raise ValueError(f"duplicate current UI item_group_id={group_id}")
        groups[group_id] = str(row["item_group_name"])
    return groups


def _is_short_noun_text(text: str) -> bool:
    stripped = re.sub(r"<[^>]+>", "", text).strip()
    return bool(stripped) and len(stripped) <= 24 and not _SENTENCE_MARKS.search(stripped)


def audit_sections(
    records: Iterable[JapaneseLltRecord], item_group_ids: set[int]
) -> tuple[list[JapaneseEquipmentSectionAudit], dict[int, list[JapaneseLltRecord]]]:
    """Summarize every LLT section without assuming a known section id."""
    grouped: dict[int, list[JapaneseLltRecord]] = defaultdict(list)
    for record in records:
        grouped[record.section_id].append(record)

    sections: list[JapaneseEquipmentSectionAudit] = []
    for section_id, section_records in sorted(grouped.items()):
        by_text_id: dict[int, list[JapaneseLltRecord]] = defaultdict(list)
        for record in section_records:
            by_text_id[record.text_id].append(record)
        covered_ids = item_group_ids & set(by_text_id)
        duplicate_ids = sorted(
            text_id for text_id in covered_ids if len(by_text_id[text_id]) != 1
        )
        variant_patterns: Counter[str] = Counter()
        for text_id_records in by_text_id.values():
            variants = sorted(
                {
                    (record.kind, record.variant_id, record.sub_variant_id)
                    for record in text_id_records
                },
                key=str,
            )
            if len(variants) == 1:
                kind, variant_id, sub_variant_id = variants[0]
                pattern = f"kind{kind}:{variant_id}:{sub_variant_id}"
            else:
                kinds = ",".join(map(str, sorted({variant[0] for variant in variants})))
                pattern = f"kinds[{kinds}]:{len(variants)}-variant-combinations"
            variant_patterns[pattern] += 1
        hint_matches = [
            {
                "text_id": record.text_id,
                "variant_id": record.variant_id,
                "sub_variant_id": record.sub_variant_id,
                "text": record.text,
            }
            for record in section_records
            if record.text_id in item_group_ids
            and any(hint in record.text for hint in SEARCH_HINTS)
        ][:24]
        text_ids = set(by_text_id)
        sections.append(
            JapaneseEquipmentSectionAudit(
                section_id=section_id,
                record_count=len(section_records),
                unique_text_id_count=len(text_ids),
                text_id_min=min(text_ids) if text_ids else None,
                text_id_max=max(text_ids) if text_ids else None,
                item_group_id_coverage=len(covered_ids),
                has_all_item_group_ids=covered_ids == item_group_ids,
                duplicate_item_group_ids=duplicate_ids,
                variant_structure=dict(sorted(variant_patterns.items())),
                short_noun_text_ratio=(
                    sum(_is_short_noun_text(record.text) for record in section_records)
                    / len(section_records)
                    if section_records
                    else 0
                ),
                hint_matches=hint_matches,
            )
        )
    return sections, grouped


def build_japanese_equipment_group_audit(
    records: Iterable[JapaneseLltRecord],
    korean_groups: Mapping[int, str],
    current_ui_groups: Mapping[int, str],
    *,
    japanese_llt_source: str,
    korean_group_source: str,
    current_ui_source: str,
) -> JapaneseEquipmentGroupAuditReport:
    """Find direct-ID equipment-group sections and build an auditable report."""
    if not korean_groups:
        raise ValueError("Korean item-group source is empty")
    if len(korean_groups) != len(set(korean_groups)):
        raise ValueError("duplicate Korean item-group ids")
    missing_ui_groups = set(current_ui_groups) - set(korean_groups)
    if missing_ui_groups:
        raise ValueError(
            f"current UI groups missing from Korean source: {sorted(missing_ui_groups)}"
        )

    record_list = list(records)
    group_ids = set(korean_groups)
    sections, grouped = audit_sections(record_list, group_ids)
    exact_sections = [
        section
        for section in sections
        if section.record_count == len(group_ids)
        and section.unique_text_id_count == len(group_ids)
        and section.has_all_item_group_ids
        and not section.duplicate_item_group_ids
        and len(section.variant_structure) == 1
    ]
    structural_sections = [
        section
        for section in sections
        if section.has_all_item_group_ids
        and not section.duplicate_item_group_ids
    ]
    likely_section_id = (
        exact_sections[0].section_id
        if len(exact_sections) == 1
        else structural_sections[0].section_id
        if len(structural_sections) == 1
        else None
    )

    candidates_by_id: dict[int, list[JapaneseLltRecord]] = defaultdict(list)
    if likely_section_id is not None:
        for record in grouped[likely_section_id]:
            if record.text_id in group_ids:
                candidates_by_id[record.text_id].append(record)

    results: list[JapaneseEquipmentGroupAuditRow] = []
    for group_id, ko_name in sorted(korean_groups.items()):
        candidates = candidates_by_id[group_id]
        if len(exact_sections) == 1 and len(candidates) == 1:
            candidate = candidates[0]
            results.append(
                JapaneseEquipmentGroupAuditRow(
                    item_group_id=group_id,
                    ko_name=ko_name,
                    ja_candidate=candidate.text,
                    section_id=candidate.section_id,
                    text_id=candidate.text_id,
                    variant_id=candidate.variant_id,
                    sub_variant_id=candidate.sub_variant_id,
                    evidence=[
                        f"section {candidate.section_id} has exactly one record for every item_group_id",
                        f"item_group_id {group_id} directly equals text_id {candidate.text_id}",
                        "the section covers the complete Korean item-group dictionary",
                        "all records in the direct section use one consistent variant structure",
                    ],
                    confidence="high",
                    status="confirmed_direct_id",
                )
            )
        elif len(candidates) == 1:
            candidate = candidates[0]
            results.append(
                JapaneseEquipmentGroupAuditRow(
                    item_group_id=group_id,
                    ko_name=ko_name,
                    ja_candidate=candidate.text,
                    section_id=candidate.section_id,
                    text_id=candidate.text_id,
                    variant_id=candidate.variant_id,
                    sub_variant_id=candidate.sub_variant_id,
                    evidence=[
                        "one structural section covers all item-group ids",
                        f"item_group_id {group_id} directly equals text_id {candidate.text_id}",
                        "the candidate section contains additional records or ids",
                    ],
                    confidence="medium",
                    status="strong_structural_candidate",
                )
            )
        elif candidates:
            results.append(
                JapaneseEquipmentGroupAuditRow(
                    item_group_id=group_id,
                    ko_name=ko_name,
                    ja_candidate=None,
                    section_id=likely_section_id,
                    text_id=group_id,
                    variant_id=None,
                    sub_variant_id=None,
                    evidence=[
                        f"multiple records conflict for text_id {group_id}",
                    ],
                    confidence="low",
                    status="ambiguous",
                )
            )
        else:
            status = "ambiguous" if exact_sections or structural_sections else "missing"
            results.append(
                JapaneseEquipmentGroupAuditRow(
                    item_group_id=group_id,
                    ko_name=ko_name,
                    ja_candidate=None,
                    section_id=likely_section_id,
                    text_id=group_id if likely_section_id is not None else None,
                    variant_id=None,
                    sub_variant_id=None,
                    evidence=[
                        "no unique direct-ID record was established"
                        if status == "missing"
                        else "multiple structurally plausible sections prevent a unique mapping"
                    ],
                    confidence="low",
                    status=status,
                )
            )

    counts = Counter(result.status for result in results)
    duplicate_candidates = [
        group_id
        for group_id, candidates in candidates_by_id.items()
        if len({candidate.text for candidate in candidates}) > 1
    ]
    reasons: list[str] = []
    if counts["ambiguous"]:
        reasons.append("ambiguous mappings exist")
    if counts["missing"]:
        reasons.append("missing mappings exist")
    if counts["confirmed_direct_id"] != len(korean_groups):
        reasons.append("not every Korean group is confirmed by direct id")
    if set(current_ui_groups) - {
        result.item_group_id
        for result in results
        if result.status == "confirmed_direct_id"
    }:
        reasons.append("current UI group coverage is incomplete")
    if duplicate_candidates:
        reasons.append(f"conflicting Japanese candidates: {duplicate_candidates}")

    return JapaneseEquipmentGroupAuditReport(
        japanese_llt_source=japanese_llt_source,
        korean_group_source=korean_group_source,
        current_ui_source=current_ui_source,
        likely_section_id=likely_section_id,
        summary=JapaneseEquipmentGroupAuditSummary(
            section_count=len(sections),
            korean_group_count=len(korean_groups),
            current_ui_group_count=len(current_ui_groups),
            confirmed_direct_id_count=counts["confirmed_direct_id"],
            strong_structural_candidate_count=counts[
                "strong_structural_candidate"
            ],
            ambiguous_count=counts["ambiguous"],
            missing_count=counts["missing"],
            production_export_eligible=not reasons,
            production_export_reasons=reasons,
        ),
        sections=sections,
        results=results,
    )


def build_production_equipment_groups(
    report: JapaneseEquipmentGroupAuditReport,
) -> dict[int, str]:
    """Build production data only when every export condition is satisfied."""
    if not report.summary.production_export_eligible:
        reasons = "; ".join(report.summary.production_export_reasons)
        raise ValueError(f"production equipment-group export refused: {reasons}")
    mapping: dict[int, str] = {}
    for result in report.results:
        if (
            result.status != "confirmed_direct_id"
            or result.ja_candidate is None
            or result.section_id is None
            or result.text_id != result.item_group_id
        ):
            raise ValueError(
                f"production equipment-group export refused for id={result.item_group_id}"
            )
        if result.item_group_id in mapping:
            raise ValueError(f"duplicate production item_group_id={result.item_group_id}")
        mapping[result.item_group_id] = result.ja_candidate
    return dict(sorted(mapping.items()))


def write_json(path: Path, payload: object) -> None:
    """Write stable, readable UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
