"""Evidence-based Japanese labels for general OpenViewer equipment buckets."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path

from rs_dev.models import (
    JapaneseLltRecord,
    JapaneseOpenEquipmentBucketAuditReport,
    JapaneseOpenEquipmentBucketAuditRow,
    JapaneseOpenEquipmentBucketAuditSummary,
)
from rs_dev.open_options import BUCKET_BY_GROUP_IDS


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT_OUTPUT = (
    ROOT
    / "data"
    / "processed"
    / "i18n"
    / "ja"
    / "open_equipment_buckets_audit.json"
)
DEFAULT_PRODUCTION_OUTPUT = (
    ROOT
    / "data"
    / "processed"
    / "i18n"
    / "ja"
    / "open_equipment_buckets.json"
)

# Search hints only. A matching word is accepted only after section-level
# category overlap and neighboring-record checks below.
SEMANTIC_SEARCH_HINTS = {"무기": "武器"}


def load_equipment_group_names(path: Path) -> dict[int, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {int(group_id): str(name) for group_id, name in payload.items()}


def collect_csv_bucket_counts(path: Path) -> dict[str, int]:
    counts: Counter[str] = Counter()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            counts[row["equipment_bucket"]] += 1
    if not counts:
        raise ValueError("open-option CSV contains no equipment buckets")
    return dict(sorted(counts.items()))


def _semantic_candidate(
    bucket_name: str,
    records: list[JapaneseLltRecord],
    reference_names: set[str],
) -> tuple[JapaneseLltRecord | None, list[str]]:
    hint = SEMANTIC_SEARCH_HINTS.get(bucket_name)
    if hint is None:
        return None, ["no semantic-category search hint is defined"]

    by_section: dict[int, list[JapaneseLltRecord]] = defaultdict(list)
    for record in records:
        by_section[record.section_id].append(record)

    ranked: list[tuple[int, float, JapaneseLltRecord, list[str]]] = []
    rejected: list[str] = []
    for section_id, section_records in by_section.items():
        exact_records = [record for record in section_records if record.text == hint]
        if not exact_records:
            continue
        section_texts = {candidate.text for candidate in section_records}
        overlap = sorted((section_texts & reference_names) - {hint})
        short_labels = sum(
            bool(candidate.text.strip())
            and len(candidate.text.strip()) <= 16
            and "\n" not in candidate.text
            and "。" not in candidate.text
            for candidate in section_records
        )
        short_ratio = short_labels / len(section_records)
        if (
            len(exact_records) != 1
            or len(section_records) > 128
            or short_ratio < 0.8
        ):
            rejected.append(
                f"section {section_id} rejected: records={len(section_records)}, "
                f"exact_hint_records={len(exact_records)}, short_label_ratio={short_ratio:.3f}"
            )
            continue
        record = exact_records[0]
        neighbors = [
            f"{candidate.text_id}:{candidate.text}"
            for candidate in sorted(section_records, key=lambda item: item.text_id)
            if abs(candidate.text_id - record.text_id) <= 4
        ][:12]
        ranked.append(
            (
                len(overlap),
                short_ratio,
                record,
                [
                    f"section {record.section_id} contains exact semantic hint {hint!r}",
                    f"same-section confirmed equipment-name overlap: {overlap}",
                    f"neighboring records: {neighbors}",
                    f"short category-like labels in section: {short_labels}/{len(section_records)} ({short_ratio:.3f})",
                    "section passed category structure filters: <=128 records, one exact hint, >=0.8 short-label ratio",
                ],
            )
        )

    if not ranked:
        return None, [f"no structurally valid category section for semantic hint {hint!r}", *rejected]
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    best = ranked[0]
    tied = [row for row in ranked if row[:2] == best[:2]]
    if best[0] < 4 or len(tied) != 1:
        evidence = best[3] + [
            f"semantic candidate is not unique enough: overlap={best[0]}, ties={len(tied)}"
        ]
        return None, evidence
    return best[2], best[3]


def build_japanese_open_bucket_audit(
    records: Iterable[JapaneseLltRecord],
    korean_group_names: Mapping[int, str],
    japanese_group_names: Mapping[int, str],
    csv_bucket_counts: Mapping[str, int],
    *,
    japanese_llt_source: str,
    equipment_groups_source: str,
    csv_source: str,
) -> JapaneseOpenEquipmentBucketAuditReport:
    record_list = list(records)
    definition_by_name = {
        bucket_name: group_ids
        for group_ids, bucket_name in BUCKET_BY_GROUP_IDS.items()
    }
    actual_bucket_names = set(csv_bucket_counts)
    unknown_csv_buckets = actual_bucket_names - set(definition_by_name)
    if unknown_csv_buckets:
        raise ValueError(f"CSV buckets missing from definitions: {unknown_csv_buckets}")

    all_constituent_ids = {
        group_id for group_ids in BUCKET_BY_GROUP_IDS for group_id in group_ids
    }
    missing_korean = all_constituent_ids - set(korean_group_names)
    missing_japanese = all_constituent_ids - set(japanese_group_names)
    if missing_korean or missing_japanese:
        raise ValueError(
            f"constituent coverage missing: Korean={sorted(missing_korean)}, "
            f"Japanese={sorted(missing_japanese)}"
        )

    reference_names = {
        japanese_group_names[group_id] for group_id in all_constituent_ids
    }
    results: list[JapaneseOpenEquipmentBucketAuditRow] = []
    for bucket_name in sorted(actual_bucket_names):
        group_ids = definition_by_name[bucket_name]
        ko_names = [korean_group_names[group_id] for group_id in group_ids]
        ja_names = [japanese_group_names[group_id] for group_id in group_ids]
        common = {
            "ko_bucket_name": bucket_name,
            "group_ids": list(group_ids),
            "group_count": len(group_ids),
            "constituent_ko_names": ko_names,
            "constituent_ja_names": ja_names,
            "csv_row_count": csv_bucket_counts[bucket_name],
        }
        if len(group_ids) == 1:
            group_id = group_ids[0]
            results.append(
                JapaneseOpenEquipmentBucketAuditRow(
                    **common,
                    strategy="direct_single_group",
                    ja_candidate=ja_names[0],
                    source_type="section_163_direct_id",
                    source_section_id=163,
                    source_text_id=group_id,
                    source_variant_id=0,
                    source_sub_variant_id=0,
                    evidence=[
                        f"bucket has one constituent item_group_id={group_id}",
                        f"section 163 text_id {group_id} directly supplies the Japanese original",
                    ],
                    confidence="high",
                    status="confirmed",
                )
            )
        elif len(group_ids) <= 2:
            results.append(
                JapaneseOpenEquipmentBucketAuditRow(
                    **common,
                    strategy="compose_constituent_names",
                    ja_candidate="/".join(ja_names),
                    source_type="section_163_constituents",
                    source_section_id=163,
                    source_text_id=None,
                    source_variant_id=0,
                    source_sub_variant_id=0,
                    evidence=[
                        "bucket contains two explicit item-group constituents",
                        "Japanese label preserves the same order and separator using only section 163 originals",
                    ],
                    confidence="high",
                    status="confirmed",
                )
            )
        else:
            candidate, evidence = _semantic_candidate(
                bucket_name, record_list, reference_names
            )
            if candidate is None:
                results.append(
                    JapaneseOpenEquipmentBucketAuditRow(
                        **common,
                        strategy="unresolved",
                        ja_candidate=None,
                        source_type=None,
                        source_section_id=None,
                        source_text_id=None,
                        source_variant_id=None,
                        source_sub_variant_id=None,
                        evidence=evidence,
                        confidence="low",
                        status="ambiguous",
                    )
                )
            else:
                results.append(
                    JapaneseOpenEquipmentBucketAuditRow(
                        **common,
                        strategy="verified_semantic_label",
                        ja_candidate=candidate.text,
                        source_type="japanese_llt_equipment_category_section",
                        source_section_id=candidate.section_id,
                        source_text_id=candidate.text_id,
                        source_variant_id=candidate.variant_id,
                        source_sub_variant_id=candidate.sub_variant_id,
                        evidence=evidence,
                        confidence="high",
                        status="confirmed",
                    )
                )

    statuses = Counter(result.status for result in results)
    strategies = Counter(result.strategy for result in results)
    japanese_counts = Counter(
        result.ja_candidate for result in results if result.ja_candidate
    )
    duplicate_names = sorted(
        name for name, count in japanese_counts.items() if count > 1
    )
    empty_count = sum(
        result.ja_candidate is not None and not result.ja_candidate.strip()
        for result in results
    )
    reasons: list[str] = []
    if {result.ko_bucket_name for result in results} != actual_bucket_names:
        reasons.append("CSV bucket coverage is incomplete")
    if statuses["ambiguous"]:
        reasons.append("ambiguous bucket mappings exist")
    if statuses["missing"]:
        reasons.append("missing bucket mappings exist")
    if statuses["strong_candidate"]:
        reasons.append("unconfirmed strong candidates exist")
    if empty_count:
        reasons.append("empty Japanese bucket labels exist")

    return JapaneseOpenEquipmentBucketAuditReport(
        japanese_llt_source=japanese_llt_source,
        equipment_groups_source=equipment_groups_source,
        csv_source=csv_source,
        summary=JapaneseOpenEquipmentBucketAuditSummary(
            actual_bucket_count=len(actual_bucket_names),
            direct_single_group_count=strategies["direct_single_group"],
            composable_multi_group_count=strategies[
                "compose_constituent_names"
            ],
            semantic_category_count=(
                strategies["verified_semantic_label"] + strategies["unresolved"]
            ),
            confirmed_count=statuses["confirmed"],
            strong_candidate_count=statuses["strong_candidate"],
            ambiguous_count=statuses["ambiguous"],
            missing_count=statuses["missing"],
            csv_coverage_complete=not unknown_csv_buckets
            and {result.ko_bucket_name for result in results} == actual_bucket_names,
            duplicate_japanese_names=duplicate_names,
            empty_japanese_name_count=empty_count,
            production_export_eligible=not reasons,
            production_export_reasons=reasons,
        ),
        results=results,
    )


def build_production_open_buckets(
    report: JapaneseOpenEquipmentBucketAuditReport,
) -> dict[str, str]:
    if not report.summary.production_export_eligible:
        raise ValueError(
            "production open-equipment bucket export refused: "
            + "; ".join(report.summary.production_export_reasons)
        )
    mapping = {
        result.ko_bucket_name: result.ja_candidate
        for result in report.results
        if result.status == "confirmed" and result.ja_candidate
    }
    if len(mapping) != report.summary.actual_bucket_count:
        raise ValueError("production open-equipment bucket key coverage mismatch")
    if any(not value.strip() for value in mapping.values()):
        raise ValueError("production open-equipment bucket contains an empty value")
    return dict(sorted(mapping.items()))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
