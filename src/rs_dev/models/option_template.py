"""Locale catalog model for one option template."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LocalizedOptionTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_id: int = Field(ge=0)
    template: str = Field(min_length=1)
