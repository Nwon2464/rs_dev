"""Evidence-based Japanese labels for open-option grades and converters."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path

from rs_dev.models import (
    JapaneseLltRecord,
    JapaneseOpenMetadataAuditReport,
    JapaneseOpenMetadataAuditRow,
    JapaneseOpenMetadataAuditSummary,
)

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_AUDIT_OUTPUT = ROOT / "data/reports/open_options/catalogs/ja/open_metadata_audit.json"
DEFAULT_PRODUCTION_OUTPUT = (
    ROOT / "data/reports/open_options/catalogs/ja/open_metadata_values.json"
)

GRADE_SPECS = {
    "7": ("유니크", 12, "ユニーク"),
    "8": ("DX 유니크", 13, "DX ユニーク"),
    "9": ("ULT 유니크", 14, "ULT ユニーク"),
}
CONVERTER_SPECS = {
    "normal": ("일반 변환기 / 일반", 12501, "解放オプション変換器"),
    "improved": ("개량된 변환기 / 개량", 12785, "解放オプション変換器・改"),
    "fake": ("모조 변환기 / 모조", 12859, "レプリカ解放オプション変換器"),
    "burning": ("불타는 변환기 / 불타는", 13498, "灼熱の解放オプション変換器"),
    "association": ("협회 변환기", 13039, "解放オプション変換器[協会]"),
}
GENERAL_TO_CANONICAL = {
    "일반 변환기": "normal", "개량된 변환기": "improved",
    "모조 변환기": "fake", "불타는 변환기": "burning",
    "협회 변환기": "association",
    "normal": "normal", "improved": "improved", "fake": "fake",
    "burning": "burning", "association": "association",
}
INSTANDARD_TO_CANONICAL = {
    "일반": "normal", "개량": "improved", "모조": "fake", "불타는": "burning",
    "normal": "normal", "improved": "improved", "fake": "fake", "burning": "burning",
}


def collect_usage(general_csv: Path, instandard_csv: Path) -> tuple[dict[str, Counter], dict[str, Counter]]:
    grades: Counter[str] = Counter()
    general: Counter[str] = Counter()
    instandard: Counter[str] = Counter()
    with general_csv.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            grade_name = row.get("grade_name") or GRADE_SPECS[row["grade_code"]][0]
            grades[f"{row['grade_code']}:{grade_name}"] += 1
            general[row["converter_type"]] += 1
    with instandard_csv.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            instandard[row["converter_type"]] += 1
    return {"grades": grades}, {"general": general, "instandard": instandard}


def collect_current_ui_values(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"GENERAL_CONVERTER_LABELS[\s\S]*?ja:\s*\{([^}]*)\}", text
    )
    if not match:
        return {}
    labels = dict(re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', match.group(1)))
    return {concept: labels[key] for key, concept in GENERAL_TO_CANONICAL.items() if key in labels}


def _comparison(current: str | None, candidate: str | None) -> str:
    if current is None:
        return "no_current_ui_value"
    if current == candidate:
        return "exact_match"
    compact = lambda value: re.sub(r"[\s・\[\]]", "", value)
    if candidate is not None and compact(current) == compact(candidate):
        return "spacing_or_punctuation_difference"
    return "wording_difference"


def build_japanese_open_metadata_audit(
    records: Iterable[JapaneseLltRecord], grade_usage: Mapping[str, int],
    general_usage: Mapping[str, int], instandard_usage: Mapping[str, int],
    current_ui: Mapping[str, str], *, japanese_llt_source: str,
    general_csv_source: str, instandard_csv_source: str, current_ui_source: str,
) -> JapaneseOpenMetadataAuditReport:
    record_list = list(records)
    index = {(r.section_id, r.text_id, r.variant_id, r.sub_variant_id): r for r in record_list}
    results: list[JapaneseOpenMetadataAuditRow] = []
    grade_sequence = [(index.get((66, text_id, 0, 0)) or JapaneseLltRecord(section_id=66, text_id=text_id, variant_id=0, sub_variant_id=0, text="", kind=0)).text for text_id in range(9, 15)]
    expected_sequence = ["ノーマル", "ノーマル DX", "ノーマル ULT", "ユニーク", "DX ユニーク", "ULT ユニーク"]
    for code, (ko, text_id, expected) in GRADE_SPECS.items():
        record = index.get((66, text_id, 0, 0))
        confirmed = record is not None and record.text == expected and grade_sequence == expected_sequence
        results.append(JapaneseOpenMetadataAuditRow(
            category="grade", internal_key=code, ko_label=ko,
            ja_candidate=record.text if record else None, section_id=66 if record else None,
            text_id=text_id if record else None, variant_id=record.variant_id if record else None,
            sub_variant_id=record.sub_variant_id if record else None,
            usage_counts={"general": grade_usage.get(f"{code}:{ko}", 0)},
            evidence=["section 66 text_id 9-14 is a contiguous item-grade enum: " + ", ".join(grade_sequence), f"grade codes 7-9 preserve the same three-label order at text_id 12-14 (offset +5)"] if confirmed else ["required section 66 grade sequence was not found intact"],
            confidence="high" if confirmed else "low", status="confirmed_structural" if confirmed else "missing",
            current_ui_value=None, ui_comparison="no_current_ui_value",
        ))
    for concept, (ko, text_id, expected) in CONVERTER_SPECS.items():
        name = index.get((67, text_id, 0, 0)); desc = index.get((68, text_id, 0, 0))
        confirmed = name is not None and name.text == expected and desc is not None and "解放オプション" in desc.text
        results.append(JapaneseOpenMetadataAuditRow(
            category="converter", internal_key=concept, ko_label=ko,
            ja_candidate=name.text if name else None, section_id=67 if name else None,
            text_id=text_id if name else None, variant_id=name.variant_id if name else None,
            sub_variant_id=name.sub_variant_id if name else None,
            description_section_id=68 if desc else None, description_text_id=text_id if desc else None,
            description=desc.text if desc else None,
            usage_counts={"general": sum(v for k, v in general_usage.items() if GENERAL_TO_CANONICAL.get(k) == concept), "instandard": sum(v for k, v in instandard_usage.items() if INSTANDARD_TO_CANONICAL.get(k) == concept)},
            evidence=[f"section 67 text_id {text_id} is the item name", f"section 68 uses the same text_id and describes this converter's behavior", "variant/sub_variant are consistently 0/0"] if confirmed else ["matching section 67 item name and section 68 description were not both found"],
            confidence="high" if confirmed else "low", status="confirmed_direct" if confirmed else "missing",
            current_ui_value=current_ui.get(concept), ui_comparison=_comparison(current_ui.get(concept), name.text if name else None),
        ))
    statuses = Counter(row.status for row in results)
    reasons = []
    if len(results) != 8: reasons.append("required metadata coverage is incomplete")
    if statuses["ambiguous"] or statuses["missing"] or statuses["strong_candidate"]: reasons.append("not every required value is confirmed")
    candidates = [row.ja_candidate for row in results]
    if any(not value for value in candidates): reasons.append("empty Japanese candidate exists")
    if len(set(candidates)) != len(candidates): reasons.append("Japanese candidate conflict exists")
    return JapaneseOpenMetadataAuditReport(
        japanese_llt_source=japanese_llt_source, general_csv_source=general_csv_source,
        instandard_csv_source=instandard_csv_source, current_ui_source=current_ui_source,
        summary=JapaneseOpenMetadataAuditSummary(section_count=len({r.section_id for r in record_list}), grade_count=3, converter_count=5,
            confirmed_count=statuses["confirmed_direct"] + statuses["confirmed_structural"], strong_candidate_count=statuses["strong_candidate"], ambiguous_count=statuses["ambiguous"], missing_count=statuses["missing"],
            production_export_eligible=not reasons, production_export_reasons=reasons), results=results)


def build_production_open_metadata(report: JapaneseOpenMetadataAuditReport) -> dict[str, dict[str, str]]:
    if not report.summary.production_export_eligible:
        raise ValueError("production export refused: " + "; ".join(report.summary.production_export_reasons))
    return {
        "grades": {r.internal_key: r.ja_candidate for r in report.results if r.category == "grade" and r.ja_candidate},
        "converters": {r.internal_key: r.ja_candidate for r in report.results if r.category == "converter" and r.ja_candidate},
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
