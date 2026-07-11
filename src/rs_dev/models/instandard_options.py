"""Models for non-standard equipment JSON and CSV outputs."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


RollVector = tuple[int, int, int]


class InstandardTier(Model):
    tier: int = Field(ge=0, le=9)
    raw_tier_index: int = Field(ge=0, le=9)
    option_level_raw: int = Field(ge=0)
    enabled: bool
    roll_values: list[RollVector] = Field(min_length=10, max_length=10)
    option_level_group_index: int | None
    option_level_group_number: int | None
    group_index_offset_from_raw_tier: int | None

    @model_validator(mode="after")
    def tier_indices_are_consistent(self) -> "InstandardTier":
        if self.tier != self.raw_tier_index:
            raise ValueError("tier alias differs from raw tier index")
        group_values = (
            self.option_level_group_index,
            self.option_level_group_number,
            self.group_index_offset_from_raw_tier,
        )
        if self.enabled:
            if any(value is None for value in group_values):
                raise ValueError("enabled tier is missing common-group indices")
            if self.option_level_group_number != self.option_level_group_index + 1:
                raise ValueError("common-group number is not one-based")
        elif any(value is not None for value in group_values):
            raise ValueError("disabled tier unexpectedly has common-group indices")
        return self


class InstandardOption(Model):
    option_id: int = Field(ge=0)
    name: str
    description: str
    short_text: str
    tags: list[str]
    selectable: bool
    raw_selectable: bool
    supplemental_assignment: dict[str, Any] | None
    tiers: list[InstandardTier]


class InstandardEquipment(Model):
    item_group_id: int = Field(ge=0)
    item_group_name: str
    option_ids: list[int]
    raw_option_ids: list[int]
    supplemental_option_ids: list[int]


class InstandardSummary(Model):
    equipment_group_count: int = Field(ge=0)
    option_definition_count: int = Field(ge=0)
    selectable_option_count: int = Field(ge=0)
    raw_selectable_option_count: int = Field(ge=0)
    supplemental_option_ids: list[int]
    unused_option_ids: list[int]
    prefix_count: int = Field(ge=0)
    option_level_keys: list[int]
    shifted_raw_tier_option_ids: list[int]


class InstandardDataset(Model):
    schema_version: Literal[2]
    generator: str
    source: dict[str, Any]
    summary: InstandardSummary
    equipment: list[InstandardEquipment]
    options: list[InstandardOption]
    prefix_tag_names: list[Any]
    material_data: list[Any]
    disjoint_data: list[Any]
    mechanics_capa: dict[int, dict[str, Any]]
    supplemental_assignments: dict[int, dict[str, Any]]

    @model_validator(mode="after")
    def dataset_links_are_consistent(self) -> "InstandardDataset":
        if self.summary.equipment_group_count != len(self.equipment):
            raise ValueError("equipment summary count mismatch")
        if self.summary.option_definition_count != len(self.options):
            raise ValueError("option summary count mismatch")

        option_ids = {option.option_id for option in self.options}
        for equipment in self.equipment:
            if not set(equipment.option_ids) <= option_ids:
                raise ValueError("equipment references an undefined option")

        supplemental_ids = {922, 1045}
        if set(self.summary.supplemental_option_ids) != supplemental_ids:
            raise ValueError("supplemental option summary must contain 922 and 1045")
        necklace = next(
            (item for item in self.equipment if item.item_group_id == 8), None
        )
        if necklace is None:
            raise ValueError("necklace equipment group is missing")
        if set(necklace.supplemental_option_ids) != supplemental_ids:
            raise ValueError("necklace supplemental options must be 922 and 1045")
        if supplemental_ids & set(necklace.raw_option_ids):
            raise ValueError("supplemental options appear in the raw necklace mapping")
        if not supplemental_ids <= set(necklace.option_ids):
            raise ValueError("supplemental options are absent from the necklace mapping")
        return self


class InstandardTierCsvRow(Model):
    option_id: int
    option_name: str
    short_text: str
    tags: str
    selectable: bool
    raw_selectable: bool
    assignment_basis: str
    equipment_groups: str
    tier: int
    raw_tier_index: int
    option_level_raw: int
    option_level_group_index: int | None
    option_level_group_number: int | None
    group_index_offset_from_raw_tier: int | None
    enabled: bool
    roll_index: int = Field(ge=0, lt=10)
    value_0: int
    value_1: int
    value_2: int

    @field_validator(
        "option_level_group_index",
        "option_level_group_number",
        "group_index_offset_from_raw_tier",
        mode="before",
    )
    @classmethod
    def empty_csv_value_is_none(cls, value: Any) -> Any:
        return None if value == "" else value


class InstandardRenderRow(Model):
    item_group_id: int
    item_group_name: str
    option_order_in_equipment: int = Field(ge=1)
    option_id: int
    option_name: str
    option_template: str
    tags: str
    assignment_basis: str
    raw_tier_index: int
    option_level_raw: int
    option_level_group_index: int
    option_level_group_number: int
    group_index_offset_from_raw_tier: int
    value_0_min: int
    value_0_max: int
    display_min: str
    display_max: str
    roll_vectors_json: str
    display_rolls_json: str
    mapping_basis: str
    roll_01_raw: str
    roll_01_display: str
    roll_02_raw: str
    roll_02_display: str
    roll_03_raw: str
    roll_03_display: str
    roll_04_raw: str
    roll_04_display: str
    roll_05_raw: str
    roll_05_display: str
    roll_06_raw: str
    roll_06_display: str
    roll_07_raw: str
    roll_07_display: str
    roll_08_raw: str
    roll_08_display: str
    roll_09_raw: str
    roll_09_display: str
    roll_10_raw: str
    roll_10_display: str

    @field_validator("roll_vectors_json")
    @classmethod
    def validate_roll_vectors(cls, value: str) -> str:
        vectors = json.loads(value)
        if len(vectors) != 10 or any(len(vector) != 3 for vector in vectors):
            raise ValueError("render row must contain ten three-value roll vectors")
        return value

    @field_validator("display_rolls_json")
    @classmethod
    def validate_display_rolls(cls, value: str) -> str:
        displays = json.loads(value)
        if len(displays) != 10 or not all(isinstance(item, str) for item in displays):
            raise ValueError("render row must contain ten display values")
        return value

    @model_validator(mode="after")
    def range_is_ordered(self) -> "InstandardRenderRow":
        if self.value_0_min > self.value_0_max:
            raise ValueError("render value range is reversed")
        return self
