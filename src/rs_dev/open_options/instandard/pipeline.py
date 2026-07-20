"""Build normalized non-standard equipment and converter outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rs_dev.models.instandard_equipment import (
    InstandardEquipmentGroup,
    InstandardOptionAssignment,
    InstandardTierRoll,
)
from rs_dev.open_options.common.csv_io import write_csv
from rs_dev.open_options.instandard.equipment.catalog import build_catalog
from rs_dev.open_options.instandard.equipment.normalize import (
    discover_instandard_signatures,
    normalize_equipment,
)
from rs_dev.open_options.instandard.equipment.supplemental import apply_supplemental_assignments
from rs_dev.open_options.instandard.equipment.tiers import normalize_tier_rolls
from rs_dev.open_options.instandard.equipment.validation import validate_equipment_tables
from rs_dev.open_options.instandard.migration import (
    build_legacy_baseline,
    compare_baseline,
)
from rs_dev.open_options.instandard.open_options.export_converters import (
    FIELDNAMES as OPEN_FIELDNAMES,
    export_converter_rows,
    load_converter_rows,
)
from rs_dev.open_options.instandard.open_options.merge import merge_instandard_open_rows
from rs_dev.open_options.instandard.open_options.specs import INSTANDARD_CONVERTER_SPECS
from rs_dev.open_options.instandard.open_options.transform import transform_instandard_blocks
from rs_dev.open_options.instandard.open_options.validation import validate_instandard_open_rows
from rs_dev.parsers import parse_capa, parse_instandard_equip, parse_item_groups, parse_item_option_open
from rs_dev.open_options.templates.bindings import load_value_bindings


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = ROOT / "after"
DEFAULT_INTERMEDIATE = ROOT / "data/intermediate/open_options/instandard"
DEFAULT_OUTPUT_ROOT = ROOT / "data/processed/open_options/instandard"
DEFAULT_REPORT_ROOT = ROOT / "data/reports/open_options/instandard"
DEFAULT_CONFIG_ROOT = ROOT / "config/open_options/instandard"
DEFAULT_LEGACY_CATALOG = ROOT / "data/processed/instandard_equipment.json"
DEFAULT_LEGACY_OPEN = ROOT / "data/processed/instandard_open_option_rows.csv"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_or_create_baseline(path: Path) -> dict[str, Any]:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    baseline = build_legacy_baseline(DEFAULT_LEGACY_CATALOG, DEFAULT_LEGACY_OPEN)
    _write_json(path, baseline)
    return baseline


def build_instandard(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    intermediate_root: Path = DEFAULT_INTERMEDIATE,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report_root: Path = DEFAULT_REPORT_ROOT,
    config_root: Path = DEFAULT_CONFIG_ROOT,
) -> dict[str, Any]:
    required = (
        data_dir / "InstandardEquip.dat",
        data_dir / "item_option_open.dat",
        data_dir / "simpleGameText.dat",
        data_dir / "capa.dat",
        config_root / "supplemental_assignments.json",
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("required non-standard source(s) missing: " + ", ".join(missing))

    parsed = parse_instandard_equip(data_dir / "InstandardEquip.dat")
    blocks = parse_item_option_open(data_dir / "item_option_open.dat")
    group_names = parse_item_groups(data_dir / "simpleGameText.dat", expected_count=84)
    capa = parse_capa(data_dir / "capa.dat")
    target_ids = {group_id for group_id, _options in parsed.OptionsByItemType}
    signatures = discover_instandard_signatures(blocks, target_ids)
    equipment, raw_assignments = normalize_equipment(parsed, group_names, signatures)
    assignments = apply_supplemental_assignments(
        raw_assignments, config_root / "supplemental_assignments.json"
    )
    tiers = normalize_tier_rolls(parsed)
    validate_equipment_tables(equipment, assignments, tiers)
    catalog = build_catalog(
        parsed,
        equipment,
        assignments,
        tiers,
        capa,
        load_value_bindings(config_root / "value_bindings.json"),
    )

    write_csv(intermediate_root / "equipment_groups.csv", list(InstandardEquipmentGroup.model_fields), (row.model_dump() for row in equipment))
    write_csv(intermediate_root / "option_assignments.csv", list(InstandardOptionAssignment.model_fields), (row.model_dump() for row in assignments))
    write_csv(intermediate_root / "tier_rolls.csv", list(InstandardTierRoll.model_fields), (row.model_dump() for row in tiers))
    _write_json(
        intermediate_root / "option_metadata.json",
        {
            str(option.OptionCapaIndex): {"source_tags": option.TagName}
            for option in parsed.OptionData
        },
    )
    _write_json(output_root / "catalog.json", catalog.model_dump(mode="json"))

    converter_groups = []
    converter_counts = {}
    converter_dir = intermediate_root / "open_options"
    for spec in INSTANDARD_CONVERTER_SPECS:
        rows = transform_instandard_blocks(signatures, spec)
        path = converter_dir / spec.output_filename
        export_converter_rows(path, rows)
        reloaded = load_converter_rows(path)
        converter_groups.append(reloaded)
        converter_counts[spec.converter_type] = len(reloaded)
    open_rows = merge_instandard_open_rows(converter_groups)
    converter_audit = validate_instandard_open_rows(open_rows)
    write_csv(output_root / "open_option_rows.csv", OPEN_FIELDNAMES, (row.model_dump() for row in open_rows))

    baseline_path = report_root / "migration_baseline.json"
    baseline = _load_or_create_baseline(baseline_path)
    comparison = compare_baseline(catalog, open_rows, baseline)
    if not comparison["matches"]:
        raise ValueError(f"non-standard migration baseline mismatch: {comparison['mismatches']}")
    assignment_audit = {
        "equipment_group_count": len(equipment),
        "raw_assignment_count": sum(row.assignment_source == "raw" for row in assignments),
        "supplemental_assignments": [row.model_dump() for row in assignments if row.assignment_source == "supplemental"],
    }
    tier_audit = {
        "tier_roll_count": len(tiers),
        "active_roll_count": sum(row.enabled for row in tiers),
        "inactive_roll_count": sum(not row.enabled for row in tiers),
    }
    _write_json(report_root / "assignment_audit.json", assignment_audit)
    _write_json(report_root / "tier_audit.json", tier_audit)
    _write_json(report_root / "converter_validation.json", {**converter_audit, "converter_row_counts": converter_counts, "migration_comparison": comparison})
    return {
        "catalog": {"equipment": len(catalog.equipment), "options": len(catalog.options)},
        "open_rows": len(open_rows),
        "migration_matches": True,
    }
