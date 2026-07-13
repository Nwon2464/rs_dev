"""CSV boundaries for non-standard converter rows."""

from __future__ import annotations

from pathlib import Path

from rs_dev.models.instandard_open_option import InstandardOpenOptionRow
from rs_dev.open_options.common.csv_io import read_csv, write_csv
from rs_dev.open_options.converters.specs import ConverterSpec


FIELDNAMES = list(InstandardOpenOptionRow.model_fields)


def export_converter_rows(path: Path, rows: list[InstandardOpenOptionRow]) -> None:
    write_csv(path, FIELDNAMES, (row.model_dump() for row in rows))


def load_converter_rows(path: Path) -> list[InstandardOpenOptionRow]:
    return [InstandardOpenOptionRow.model_validate(row) for row in read_csv(path)]
