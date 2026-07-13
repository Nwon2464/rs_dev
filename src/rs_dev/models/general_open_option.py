"""Language-neutral output contract for general equipment open options."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ConverterType = Literal["normal", "improved", "fake", "burning", "association"]
ProbabilitySource = Literal["float_a", "float_b"]


class GeneralOpenOptionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    converter_type: ConverterType
    equipment_bucket: str
    group_ids: str
    group_names: str
    grade_code: int = Field(ge=0)
    section_group: int = Field(ge=0)
    open_slot: int = Field(ge=1, le=4)
    candidate_index: int = Field(ge=1)
    option_id: int = Field(ge=0)
    value_0: int = Field(ge=0, le=0xFFFF)
    value_1: int = Field(ge=0, le=0xFFFF)
    probability: str
    probability_source: ProbabilitySource
    tier: int = Field(ge=0)
    source_block_index: int = Field(ge=0)
    source_file_offset: str

    @field_validator("probability")
    @classmethod
    def probability_is_bounded(cls, value: str) -> str:
        number = float(value)
        if not 0 < number <= 100:
            raise ValueError("probability must be greater than zero and at most 100")
        return value
