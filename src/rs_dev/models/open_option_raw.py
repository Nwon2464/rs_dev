"""Raw structures parsed from item_option_open.dat without display joins."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OpenOptionParsedRow(Model):
    row_index: int = Field(ge=0, lt=124)
    source_file_offset: int = Field(ge=0)
    candidate_index: int = Field(ge=1)
    option_id: int = Field(ge=0)
    packed_value: int = Field(ge=0, le=0xFFFFFFFF)
    float_a: float = Field(ge=0)
    float_b: float = Field(ge=0)
    tier: int = Field(ge=0)


class OpenOptionBlock(Model):
    block_index: int = Field(ge=0)
    section_type: int = Field(ge=0)
    section_group: int = Field(ge=0)
    group_ids: tuple[int, ...]
    rows: list[OpenOptionParsedRow]
