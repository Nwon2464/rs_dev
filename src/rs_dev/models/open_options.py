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
    section_type: int
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


class InstandardOpenOptionRow(Model):
    item_group_id: int = Field(ge=0)
    item_group_name: str
    bucket_signature_index: int = Field(ge=1)
    bucket_group_ids: str
    bucket_group_names: str
    converter_type: Literal["일반", "개량", "모조", "불타는"]
    mapping_status: Literal["screen_confirmed", "structural_candidate"]
    section_type: int
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
    option_tier: int = Field(ge=0)
    probability: str
    probability_source: Literal["float_a", "float_b"]
    slot_probability_sum: str
    probability_sum_valid: Literal["true", "false"]
    source_file_name: Literal["item_option_open.dat"]
    source_block_index: int = Field(ge=0)
    source_file_offset: str

    @field_validator("probability", "slot_probability_sum")
    @classmethod
    def probability_value_is_numeric(cls, value: str) -> str:
        number = float(value)
        if not 0 <= number <= 100.06:
            raise ValueError("probability value must be between 0 and 100.06")
        return value

    @field_validator("section_type")
    @classmethod
    def section_type_is_11(cls, value: int) -> int:
        if value != 11:
            raise ValueError("section_type must be 11")
        return value

    @field_validator("section_group")
    @classmethod
    def section_group_is_supported(cls, value: int) -> int:
        if value not in {0, 1, 3}:
            raise ValueError("section_group must be 0, 1, or 3")
        return value
