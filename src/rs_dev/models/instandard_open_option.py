"""Language-neutral section_type=11 open-option row."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InstandardOpenOptionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    converter_type: Literal["normal", "improved", "fake", "burning"]
    item_group_id: int = Field(ge=0)
    bucket_signature_index: int = Field(ge=1)
    bucket_group_ids: str
    section_type: int
    section_group: int
    open_slot: int = Field(ge=1, le=4)
    candidate_index: int = Field(ge=1)
    option_id: int = Field(ge=0)
    value_0: int = Field(ge=0, le=0xFFFF)
    value_1: int = Field(ge=0, le=0xFFFF)
    probability: str
    probability_source: Literal["float_a", "float_b"]
    tier: int = Field(ge=0)
    mapping_status: Literal["screen_confirmed", "structural_candidate"]
    source_block_index: int = Field(ge=0)
    source_file_offset: str

    @field_validator("probability")
    @classmethod
    def probability_is_bounded(cls, value: str) -> str:
        number = float(value)
        if not 0 < number <= 100:
            raise ValueError("probability must be greater than zero and at most 100")
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
            raise ValueError("unsupported section_group")
        return value
