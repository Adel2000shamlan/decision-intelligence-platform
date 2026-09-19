from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WhiteLabelWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: UUID | None = None
    display_name: str = Field(min_length=1, max_length=120)
    short_name: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=500)
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    secondary_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    background_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    theme_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    locale: str = Field(min_length=1, max_length=20)
    direction: str = Field(pattern=r"^(ltr|rtl)$")


class WhiteLabelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tenant_id: UUID
    organization_id: UUID | None
    display_name: str
    short_name: str
    description: str
    logo_url: str | None
    favicon_url: str | None
    primary_color: str
    secondary_color: str
    background_color: str
    theme_color: str
    locale: str
    direction: str
    created_at: datetime
    updated_at: datetime
    version: int
