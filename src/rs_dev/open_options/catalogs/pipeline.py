"""Build evidence-backed auxiliary catalogs from raw game data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rs_dev.models import (
    JapaneseEquipmentGroupAuditReport,
    JapaneseOpenEquipmentBucketAuditReport,
    JapaneseOpenMetadataAuditReport,
)
from rs_dev.open_options.catalogs.equipment_buckets import (
    build_japanese_open_bucket_audit,
    build_production_open_buckets,
    collect_csv_bucket_counts,
)
from rs_dev.open_options.catalogs.equipment_groups import (
    build_japanese_equipment_group_audit,
    build_production_equipment_groups,
    collect_current_ui_groups,
)
from rs_dev.open_options.catalogs.metadata import (
    build_japanese_open_metadata_audit,
    build_production_open_metadata,
    collect_usage,
)
from rs_dev.open_options.catalogs.option_tags import (
    DEFAULT_AUDIT_OUTPUT as DEFAULT_OPTION_TAG_AUDIT,
    build_option_tag_audit,
    build_option_tags,
    collect_option_ids,
    load_source_tags,
    write_option_tags,
    write_option_tag_audit,
)
from rs_dev.parsers import parse_capa, parse_item_groups, parse_japanese_llt


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = Path("/mnt/c/game/Red Stone/Data")
DEFAULT_LLT = DEFAULT_DATA_DIR / "language/japanese.llt"
DEFAULT_OUTPUT_ROOT = ROOT / "data/processed/open_options/catalogs"
DEFAULT_REPORT_ROOT = ROOT / "data/reports/open_options/catalogs/ja"
DEFAULT_GENERAL_ROWS = ROOT / "data/processed/open_options/general/open_option_rows.csv"
DEFAULT_INSTANDARD_ROWS = ROOT / "data/processed/open_options/instandard/open_option_rows.csv"
DEFAULT_INSTANDARD_CATALOG = ROOT / "data/processed/open_options/instandard/catalog.json"


@dataclass(frozen=True)
class JapaneseCatalogAudits:
    equipment_groups: JapaneseEquipmentGroupAuditReport
    equipment_buckets: JapaneseOpenEquipmentBucketAuditReport
    metadata: JapaneseOpenMetadataAuditReport


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_japanese_catalog_audits(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    llt_path: Path = DEFAULT_LLT,
    report_root: Path = DEFAULT_REPORT_ROOT,
    general_rows_path: Path = DEFAULT_GENERAL_ROWS,
    instandard_rows_path: Path = DEFAULT_INSTANDARD_ROWS,
    instandard_catalog_path: Path = DEFAULT_INSTANDARD_CATALOG,
) -> JapaneseCatalogAudits:
    """Rebuild all Japanese catalog evidence from raw DAT/LLT sources."""
    required = (
        data_dir / "simpleGameText.dat",
        llt_path,
        general_rows_path,
        instandard_rows_path,
        instandard_catalog_path,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "required Japanese catalog audit source(s) missing: " + ", ".join(missing)
        )

    records = parse_japanese_llt(llt_path)
    korean_groups = parse_item_groups(
        data_dir / "simpleGameText.dat", expected_count=84
    )
    current_ui_groups = collect_current_ui_groups(instandard_catalog_path)
    equipment_report = build_japanese_equipment_group_audit(
        records,
        korean_groups,
        current_ui_groups,
        japanese_llt_source=str(llt_path),
        korean_group_source=str(data_dir / "simpleGameText.dat"),
        current_ui_source=str(instandard_catalog_path),
    )
    japanese_groups = build_production_equipment_groups(equipment_report)

    bucket_report = build_japanese_open_bucket_audit(
        records,
        korean_groups,
        japanese_groups,
        collect_csv_bucket_counts(general_rows_path),
        japanese_llt_source=str(llt_path),
        equipment_groups_source="equipment_groups_audit.json",
        csv_source=str(general_rows_path),
    )

    grade_usage, converter_usage = collect_usage(
        general_rows_path, instandard_rows_path
    )
    metadata_report = build_japanese_open_metadata_audit(
        records,
        grade_usage["grades"],
        converter_usage["general"],
        converter_usage["instandard"],
        {},
        japanese_llt_source=str(llt_path),
        general_csv_source=str(general_rows_path),
        instandard_csv_source=str(instandard_rows_path),
        current_ui_source="not used by production catalog build",
    )

    reports = JapaneseCatalogAudits(
        equipment_groups=equipment_report,
        equipment_buckets=bucket_report,
        metadata=metadata_report,
    )
    _write(
        report_root / "equipment_groups_audit.json",
        equipment_report.model_dump(mode="json"),
    )
    _write(
        report_root / "open_equipment_buckets_audit.json",
        bucket_report.model_dump(mode="json"),
    )
    _write(
        report_root / "open_metadata_audit.json",
        metadata_report.model_dump(mode="json"),
    )
    return reports


def build_auxiliary_catalogs(
    audits: JapaneseCatalogAudits,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    general_rows_path: Path = DEFAULT_GENERAL_ROWS,
    instandard_rows_path: Path = DEFAULT_INSTANDARD_ROWS,
    instandard_catalog_path: Path = DEFAULT_INSTANDARD_CATALOG,
    option_tag_audit_path: Path = DEFAULT_OPTION_TAG_AUDIT,
) -> dict[str, int]:
    """Create production catalogs from freshly generated audit objects."""
    equipment_groups = build_production_equipment_groups(audits.equipment_groups)
    open_buckets = build_production_open_buckets(audits.equipment_buckets)
    japanese_metadata = build_production_open_metadata(audits.metadata)

    option_ids = collect_option_ids(general_rows_path, instandard_rows_path)
    source_tags = load_source_tags(instandard_catalog_path)
    capa = parse_capa(data_dir / "capa.dat")
    option_tags = build_option_tags(capa, source_tags, option_ids)
    option_tag_audit = build_option_tag_audit(capa, source_tags, option_ids)
    write_option_tags(output_root / "option_tags.json", option_tags)
    write_option_tag_audit(option_tag_audit_path, option_tag_audit)
    _write(output_root / "equipment_groups.json", equipment_groups)
    _write(output_root / "open_equipment_buckets.json", open_buckets)

    converter_ko = {
        "normal": "개방옵션변환기",
        "improved": "개방옵션변환기改",
        "fake": "모조변환기",
        "burning": "불타는변환기",
        "association": "협회변환기",
    }
    grade_ko = {"7": "유니크", "8": "DX 유니크", "9": "ULT 유니크"}
    open_metadata = {
        "grades": {
            code: {"ko": grade_ko[code], "ja": japanese_metadata["grades"][code]}
            for code in grade_ko
        },
        "converters": {
            concept: {
                "ko": converter_ko[concept],
                "ja": japanese_metadata["converters"][concept],
            }
            for concept in converter_ko
        },
    }
    _write(output_root / "open_metadata.json", open_metadata)
    return {
        "option_tags": len(option_tags["options"]),
        "equipment_groups": len(equipment_groups),
        "open_equipment_buckets": len(open_buckets),
        "grades": len(open_metadata["grades"]),
        "converters": len(open_metadata["converters"]),
    }
