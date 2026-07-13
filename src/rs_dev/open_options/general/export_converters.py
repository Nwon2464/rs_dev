"""Write and reload one identical-schema CSV per general converter."""

from __future__ import annotations

from pathlib import Path

from rs_dev.models.general_open_option import GeneralOpenOptionRow
from rs_dev.open_options.common.csv_io import read_csv, write_csv
from rs_dev.open_options.converters.specs import ConverterSpec


FIELDNAMES = list(GeneralOpenOptionRow.model_fields)


def export_converter_rows(
    directory: Path,
    spec: ConverterSpec,
    rows: list[GeneralOpenOptionRow],
) -> Path:
    path = directory / spec.output_filename
    write_csv(path, FIELDNAMES, (row.model_dump() for row in rows))
    return path


def load_converter_rows(path: Path) -> list[GeneralOpenOptionRow]:
    return [GeneralOpenOptionRow.model_validate(row) for row in read_csv(path)]
