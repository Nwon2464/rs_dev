"""Build auxiliary catalogs from their existing evidence-backed sources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rs_dev.japanese_equipment_groups import build_production_equipment_groups
from rs_dev.japanese_open_equipment_buckets import build_production_open_buckets
from rs_dev.japanese_open_metadata import build_production_open_metadata
from rs_dev.models import (
    JapaneseEquipmentGroupAuditReport,
    JapaneseOpenEquipmentBucketAuditReport,
    JapaneseOpenMetadataAuditReport,
)
from rs_dev.option_tags import (
    build_option_tags,
    collect_option_ids,
    load_source_tags,
    write_option_tags,
)
from rs_dev.parsers import parse_capa


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = Path("/mnt/c/game/Red Stone/Data")
DEFAULT_OUTPUT_ROOT = ROOT / "data/processed/open_options/catalogs"
DEFAULT_GENERAL_ROWS = ROOT / "data/processed/open_options/general/open_option_rows.csv"
DEFAULT_INSTANDARD_ROWS = ROOT / "data/processed/open_options/instandard/open_option_rows.csv"
DEFAULT_INSTANDARD_CATALOG = ROOT / "data/processed/open_options/instandard/catalog.json"


def _load_model(path: Path, model: type[Any]) -> Any:
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_auxiliary_catalogs(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    general_rows_path: Path = DEFAULT_GENERAL_ROWS,
    instandard_rows_path: Path = DEFAULT_INSTANDARD_ROWS,
    instandard_catalog_path: Path = DEFAULT_INSTANDARD_CATALOG,
) -> dict[str, int]:
    audit_root = ROOT / "data/processed/i18n/ja"
    equipment_report = _load_model(
        audit_root / "equipment_groups_audit.json", JapaneseEquipmentGroupAuditReport
    )
    bucket_report = _load_model(
        audit_root / "open_equipment_buckets_audit.json",
        JapaneseOpenEquipmentBucketAuditReport,
    )
    metadata_report = _load_model(
        audit_root / "open_metadata_audit.json", JapaneseOpenMetadataAuditReport
    )
    equipment_groups = build_production_equipment_groups(equipment_report)
    open_buckets = build_production_open_buckets(bucket_report)
    japanese_metadata = build_production_open_metadata(metadata_report)
    if "fake" not in japanese_metadata["converters"] and "replica" in japanese_metadata["converters"]:
        japanese_metadata["converters"]["fake"] = japanese_metadata["converters"].pop("replica")

    option_ids = collect_option_ids(general_rows_path, instandard_rows_path)
    source_tags = load_source_tags(instandard_catalog_path)
    option_tags = build_option_tags(
        parse_capa(data_dir / "capa.dat"), source_tags, option_ids
    )
    write_option_tags(output_root / "option_tags.json", option_tags)
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
