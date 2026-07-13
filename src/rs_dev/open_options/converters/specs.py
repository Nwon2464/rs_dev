"""Declarative converter axes observed in item_option_open.dat."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from rs_dev.models.general_open_option import ConverterType, ProbabilitySource


@dataclass(frozen=True)
class ConverterSpec:
    converter_type: ConverterType
    section_group: int
    probability_source: ProbabilitySource
    allowed_grade_codes: frozenset[int]
    output_filename: str


CONVERTER_SPECS: tuple[ConverterSpec, ...] = (
    ConverterSpec("normal", 0, "float_a", frozenset({7, 8, 9}), "normal_open_options.csv"),
    ConverterSpec("improved", 0, "float_b", frozenset({7, 8, 9}), "improved_open_options.csv"),
    ConverterSpec("fake", 1, "float_a", frozenset({7, 8, 9}), "fake_open_options.csv"),
    ConverterSpec("burning", 3, "float_a", frozenset({7, 8, 9}), "burning_open_options.csv"),
    ConverterSpec("association", 2, "float_a", frozenset({8}), "association_open_options.csv"),
)
