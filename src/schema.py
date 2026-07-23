from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SUMMARY_STYLE = Literal["bullets", "executive", "technical"]
SUMMARY_FAMILY = SUMMARY_STYLE


class SummaryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    style: SUMMARY_STYLE
    version: str = Field(min_length=1)
    overview: str = Field(min_length=1)
    key_points: list[str] = Field(min_length=1)
    risks_or_limitations: list[str] = Field(default_factory=list)


class TechnicalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overview: str = Field(min_length=1)
    key_technical_points: list[str] = Field(min_length=1)
    risks_or_limitations: list[str] = Field(default_factory=list)
    style: Literal["technical"]


class BulletsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bullets: list[str] = Field(min_length=1)
    style: Literal["bullets"]


class ExecutiveSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overview: str = Field(min_length=1)
    key_technical_and_business_points: list[str] = Field(min_length=1)
    risks_limitations_or_missing_information: list[str] = Field(default_factory=list)
    style: Literal["executive"]


SCHEMA_BY_FAMILY = {
    "technical": TechnicalSummary,
    "bullets": BulletsSummary,
    "executive": ExecutiveSummary,
}
