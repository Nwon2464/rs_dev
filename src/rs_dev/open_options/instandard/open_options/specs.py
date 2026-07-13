"""Supported non-standard converter views."""

from __future__ import annotations

from rs_dev.open_options.converters.specs import ConverterSpec


INSTANDARD_CONVERTER_SPECS = (
    ConverterSpec("normal", 0, "float_a", frozenset({11}), "normal_open_options.csv"),
    ConverterSpec("improved", 0, "float_b", frozenset({11}), "improved_open_options.csv"),
    ConverterSpec("fake", 1, "float_a", frozenset({11}), "fake_open_options.csv"),
    ConverterSpec("burning", 3, "float_a", frozenset({11}), "burning_open_options.csv"),
)
