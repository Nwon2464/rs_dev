"""Small helpers for selecting a converter's raw probability axis."""

from __future__ import annotations

from rs_dev.models.open_option_raw import OpenOptionParsedRow

from .specs import ConverterSpec


def converter_probability(row: OpenOptionParsedRow, spec: ConverterSpec) -> float:
    return row.float_a if spec.probability_source == "float_a" else row.float_b
