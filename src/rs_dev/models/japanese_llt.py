"""Validated records parsed from a Japanese LLT language file."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JapaneseLltRecord(BaseModel):
    """One text record from japanese.llt."""

    model_config = ConfigDict(extra="forbid")

    section_id: int
    text_id: int
    variant_id: int | None
    sub_variant_id: int | None
    text: str
    kind: int

    @model_validator(mode="after")
    def variant_fields_match_kind(self) -> "JapaneseLltRecord":
        variants = (self.variant_id, self.sub_variant_id)
        if self.kind == 1 and any(value is not None for value in variants):
            raise ValueError("kind 1 LLT records do not contain variant fields")
        if self.kind != 1 and any(value is None for value in variants):
            raise ValueError("non-kind 1 LLT records require variant fields")
        return self


class JapaneseOptionMapping(BaseModel):
    """One current or unused Japanese option-template mapping."""

    model_config = ConfigDict(extra="forbid")

    option_id: int = Field(ge=0)
    japanese_template: str


class JapaneseOptionAuditSummary(BaseModel):
    """Counts for a Japanese option mapping audit."""

    model_config = ConfigDict(extra="forbid")

    current_option_count: int = Field(ge=0)
    japanese_section_22_count: int = Field(ge=0)
    matched_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    unused_count: int = Field(ge=0)


class JapaneseOptionAuditReport(BaseModel):
    """Comparison of current non-standard options and Japanese templates."""

    model_config = ConfigDict(extra="forbid")

    current_option_source: str
    summary: JapaneseOptionAuditSummary
    matched: list[JapaneseOptionMapping]
    missing_in_japanese: list[int]
    unused_japanese: list[JapaneseOptionMapping]
