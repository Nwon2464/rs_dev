"""Generate language catalogs independently from numeric option rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rs_dev.open_options.common.csv_io import read_csv
from rs_dev.open_options.locales.japanese import build_japanese_catalog
from rs_dev.open_options.locales.korean import build_korean_catalog
from rs_dev.open_options.templates.audit import audit_instandard_catalog, audit_locale_catalogs
from rs_dev.open_options.templates.bindings import load_value_bindings
from rs_dev.parsers import parse_capa, parse_japanese_llt


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = Path("/mnt/c/game/Red Stone/Data")
DEFAULT_LLT = Path("/mnt/c/game/Red Stone/Data/language/japanese.llt")
DEFAULT_GENERAL_ROWS = ROOT / "data/processed/open_options/general/open_option_rows.csv"
DEFAULT_INSTANDARD_ROWS = ROOT / "data/processed/open_options/instandard/open_option_rows.csv"
DEFAULT_INSTANDARD_CATALOG = ROOT / "data/processed/open_options/instandard/catalog.json"
DEFAULT_BINDINGS = ROOT / "config/open_options/instandard/value_bindings.json"
DEFAULT_OUTPUT_ROOT = ROOT / "data/processed/open_options/i18n"
DEFAULT_REPORT = ROOT / "data/reports/open_options/locale_audit.json"


def _write_catalog(path: Path, catalog: dict[int, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_locale_catalogs(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    llt_path: Path = DEFAULT_LLT,
    general_rows_path: Path = DEFAULT_GENERAL_ROWS,
    instandard_rows_path: Path = DEFAULT_INSTANDARD_ROWS,
    instandard_catalog_path: Path = DEFAULT_INSTANDARD_CATALOG,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    required = (data_dir / "capa.dat", llt_path, general_rows_path, instandard_rows_path, instandard_catalog_path, DEFAULT_BINDINGS)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("required locale source(s) missing: " + ", ".join(missing))
    korean = build_korean_catalog(parse_capa(data_dir / "capa.dat"))
    japanese = build_japanese_catalog(parse_japanese_llt(llt_path))
    rows = [*read_csv(general_rows_path), *read_csv(instandard_rows_path)]
    row_audit = audit_locale_catalogs(rows, {"ko": korean, "ja": japanese})
    instandard_catalog = json.loads(instandard_catalog_path.read_text(encoding="utf-8"))
    catalog_audit = audit_instandard_catalog(
        instandard_catalog,
        {"ko": korean, "ja": japanese},
        load_value_bindings(DEFAULT_BINDINGS),
    )
    report = {"valid": row_audit["valid"] and catalog_audit["valid"], "row_audit": row_audit, "instandard_catalog_audit": catalog_audit}
    if not report["valid"]:
        raise ValueError(f"locale catalog audit failed: {report}")
    _write_catalog(output_root / "ko/base_options.json", korean)
    _write_catalog(output_root / "ja/base_options.json", japanese)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
