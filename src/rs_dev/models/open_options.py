"""Models for parsed and emitted equipment open-option data."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OpenOptionParsedRow(Model):
    row_index: int = Field(ge=0, lt=124)
    offset: int = Field(ge=0)
    candidate_index: int = Field(ge=1)
    option_id: int = Field(ge=0)
    packed_value: int = Field(ge=0, le=0xFFFFFFFF)
    normal: float = Field(ge=0)
    improved: float = Field(ge=0)
    tier: int = Field(ge=0)


class OpenOptionBlock(Model):
    block_index: int = Field(ge=0)
    grade_code: int
    section_group: int = Field(ge=0)
    group_ids: tuple[int, ...]
    rows: list[OpenOptionParsedRow]


class OpenOptionOutputRow(Model):
    converter_type: str = ""
    converter_probability: str = ""
    converter_probability_source: str = ""
    equipment_bucket: str
    item_group_ids: str
    item_group_names: str
    grade_code: int
    grade_name: str
    section_group: int
    open_slot: int = Field(ge=1, le=4)
    candidate_index: int = Field(ge=1)
    option_id: int = Field(ge=0)
    option_name: str
    option_value_arity: int = Field(ge=0, le=2)
    option_display: str
    value_raw: int = Field(ge=0, le=0xFFFFFFFF)
    value_0_low16: int = Field(ge=0, le=0xFFFF)
    value_1_high16: int = Field(ge=0, le=0xFFFF)
    normal_probability: str
    improved_probability: str
    option_tier: int = Field(ge=0)
    probability_sum_valid: Literal["true", "false"]
    source_file_name: Literal["item_option_open.dat"]
    source_block_index: int = Field(ge=0)
    source_file_offset: str
    mapping_basis: str
    mapping_confidence: str

    @field_validator(
        "converter_probability", "normal_probability", "improved_probability"
    )
    @classmethod
    def probability_is_numeric_and_bounded(cls, value: str) -> str:
        if value == "":
            return value
        number = float(value)
        if not 0 <= number <= 100:
            raise ValueError("probability must be between 0 and 100")
        return value

    @model_validator(mode="after")
    def classified_fields_are_consistent(self) -> "OpenOptionOutputRow":
        values = (
            self.converter_type,
            self.converter_probability,
            self.converter_probability_source,
        )
        if any(values) and not all(values):
            raise ValueError("converter classification fields must be set together")
        return self
