"""Normalized contracts for non-standard equipment data."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RawInstandardTier(Model):
    OptionLevel: int = Field(ge=0)
    Tier: int = Field(ge=0, le=9)
    TierValue: list[tuple[int, int, int]] = Field(min_length=10, max_length=10)


class RawInstandardOption(Model):
    OptionCapaIndex: int = Field(ge=0)
    TagName: list[str]
    TierData: list[RawInstandardTier]


class ParsedInstandardEquip(Model):
    OptionsByItemType: list[tuple[int, list[int]]]
    OptionData: list[RawInstandardOption]
    PrefixTagName: list[str]
    MaterialData: list[dict[str, Any]]
    DisJointData: list[Any]


class InstandardEquipmentGroup(Model):
    item_group_id: int = Field(ge=0)
    item_group_name: str
    bucket_signature_index: int = Field(ge=1)


class InstandardOptionAssignment(Model):
    item_group_id: int = Field(ge=0)
    option_id: int = Field(ge=0)
    option_order: int = Field(ge=1)
    assignment_source: Literal["raw", "supplemental"]
    evidence_id: str


class InstandardTierRoll(Model):
    option_id: int = Field(ge=0)
    raw_tier_index: int = Field(ge=0, le=9)
    option_level_raw: int = Field(ge=0)
    enabled: bool
    roll_index: int = Field(ge=0, le=9)
    value_0: int
    value_1: int
    value_2: int


class InstandardCatalogTier(Model):
    tier: int = Field(ge=0, le=9)
    option_level_raw: int = Field(ge=0)
    enabled: bool
    rolls: list[tuple[int, int, int]] = Field(min_length=10, max_length=10)


class InstandardCatalogOption(Model):
    option_id: int = Field(ge=0)
    source_tags: list[str]
    canonical_tags: list[str]
    tiers: list[InstandardCatalogTier]


class InstandardCatalogEquipment(Model):
    item_group_id: int = Field(ge=0)
    item_group_name: str
    bucket_signature_index: int = Field(ge=1)
    option_ids: list[int]
    supplemental_option_ids: list[int]


class InstandardCatalog(Model):
    schema_version: Literal[1]
    value_bindings: dict[str, dict[str, int]]
    equipment: list[InstandardCatalogEquipment]
    options: list[InstandardCatalogOption]

    @model_validator(mode="after")
    def references_exist(self) -> "InstandardCatalog":
        option_ids = {option.option_id for option in self.options}
        if any(not set(item.option_ids) <= option_ids for item in self.equipment):
            raise ValueError("equipment references an undefined option")
        return self
