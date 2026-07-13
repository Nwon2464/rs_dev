"""Validated records parsed from a Japanese LLT language file."""

from __future__ import annotations

from typing import Literal

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


class JapaneseEquipmentGroupAuditRow(BaseModel):
    """One evidence-backed Japanese equipment-group candidate."""

    model_config = ConfigDict(extra="forbid")

    item_group_id: int = Field(ge=0)
    ko_name: str
    ja_candidate: str | None
    section_id: int | None
    text_id: int | None
    variant_id: int | None
    sub_variant_id: int | None
    evidence: list[str]
    confidence: Literal["high", "medium", "low"]
    status: Literal[
        "confirmed_direct_id",
        "strong_structural_candidate",
        "ambiguous",
        "missing",
    ]


class JapaneseEquipmentSectionAudit(BaseModel):
    """Structural metrics for one japanese.llt section."""

    model_config = ConfigDict(extra="forbid")

    section_id: int
    record_count: int = Field(ge=0)
    unique_text_id_count: int = Field(ge=0)
    text_id_min: int | None
    text_id_max: int | None
    item_group_id_coverage: int = Field(ge=0)
    has_all_item_group_ids: bool
    duplicate_item_group_ids: list[int]
    variant_structure: dict[str, int]
    short_noun_text_ratio: float = Field(ge=0, le=1)
    hint_matches: list[dict[str, int | str | None]]


class JapaneseEquipmentGroupAuditSummary(BaseModel):
    """Counts and export eligibility for an equipment-group audit."""

    model_config = ConfigDict(extra="forbid")

    section_count: int = Field(ge=0)
    korean_group_count: int = Field(ge=0)
    current_ui_group_count: int = Field(ge=0)
    confirmed_direct_id_count: int = Field(ge=0)
    strong_structural_candidate_count: int = Field(ge=0)
    ambiguous_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    production_export_eligible: bool
    production_export_reasons: list[str]


class JapaneseEquipmentGroupAuditReport(BaseModel):
    """Full-section investigation and equipment-group mapping audit."""

    model_config = ConfigDict(extra="forbid")

    japanese_llt_source: str
    korean_group_source: str
    current_ui_source: str
    likely_section_id: int | None
    summary: JapaneseEquipmentGroupAuditSummary
    sections: list[JapaneseEquipmentSectionAudit]
    results: list[JapaneseEquipmentGroupAuditRow]


class JapaneseOpenEquipmentBucketAuditRow(BaseModel):
    """One evidence-backed Japanese OpenViewer equipment bucket."""

    model_config = ConfigDict(extra="forbid")

    ko_bucket_name: str
    group_ids: list[int]
    group_count: int = Field(ge=1)
    strategy: Literal[
        "direct_single_group",
        "compose_constituent_names",
        "verified_semantic_label",
        "unresolved",
    ]
    ja_candidate: str | None
    source_type: str | None
    source_section_id: int | None
    source_text_id: int | None
    source_variant_id: int | None
    source_sub_variant_id: int | None
    constituent_ko_names: list[str]
    constituent_ja_names: list[str]
    csv_row_count: int = Field(ge=0)
    evidence: list[str]
    confidence: Literal["high", "medium", "low"]
    status: Literal["confirmed", "strong_candidate", "ambiguous", "missing"]


class JapaneseOpenEquipmentBucketAuditSummary(BaseModel):
    """Counts and export eligibility for OpenViewer equipment buckets."""

    model_config = ConfigDict(extra="forbid")

    actual_bucket_count: int = Field(ge=0)
    direct_single_group_count: int = Field(ge=0)
    composable_multi_group_count: int = Field(ge=0)
    semantic_category_count: int = Field(ge=0)
    confirmed_count: int = Field(ge=0)
    strong_candidate_count: int = Field(ge=0)
    ambiguous_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    csv_coverage_complete: bool
    duplicate_japanese_names: list[str]
    empty_japanese_name_count: int = Field(ge=0)
    production_export_eligible: bool
    production_export_reasons: list[str]


class JapaneseOpenEquipmentBucketAuditReport(BaseModel):
    """Full audit for localized OpenViewer equipment-bucket labels."""

    model_config = ConfigDict(extra="forbid")

    japanese_llt_source: str
    equipment_groups_source: str
    csv_source: str
    summary: JapaneseOpenEquipmentBucketAuditSummary
    results: list[JapaneseOpenEquipmentBucketAuditRow]


class JapaneseOpenMetadataAuditRow(BaseModel):
    """One evidence-backed Japanese grade or converter label."""

    model_config = ConfigDict(extra="forbid")

    category: Literal["grade", "converter"]
    internal_key: str
    ko_label: str
    ja_candidate: str | None
    section_id: int | None
    text_id: int | None
    variant_id: int | None
    sub_variant_id: int | None
    description_section_id: int | None = None
    description_text_id: int | None = None
    description: str | None = None
    usage_counts: dict[str, int]
    evidence: list[str]
    confidence: Literal["high", "medium", "low"]
    status: Literal[
        "confirmed_direct",
        "confirmed_structural",
        "strong_candidate",
        "ambiguous",
        "missing",
    ]
    current_ui_value: str | None
    ui_comparison: Literal[
        "exact_match",
        "spacing_or_punctuation_difference",
        "wording_difference",
        "no_current_ui_value",
    ]


class JapaneseOpenMetadataAuditSummary(BaseModel):
    """Counts and export eligibility for grade and converter metadata."""

    model_config = ConfigDict(extra="forbid")

    section_count: int = Field(ge=0)
    grade_count: int = Field(ge=0)
    converter_count: int = Field(ge=0)
    confirmed_count: int = Field(ge=0)
    strong_candidate_count: int = Field(ge=0)
    ambiguous_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    production_export_eligible: bool
    production_export_reasons: list[str]


class JapaneseOpenMetadataAuditReport(BaseModel):
    """Full japanese.llt audit for open-option metadata labels."""

    model_config = ConfigDict(extra="forbid")

    japanese_llt_source: str
    general_csv_source: str
    instandard_csv_source: str
    current_ui_source: str
    summary: JapaneseOpenMetadataAuditSummary
    results: list[JapaneseOpenMetadataAuditRow]
