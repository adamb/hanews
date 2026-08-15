from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

ALLOWED_TOPICS = {
    "matter",
    "thread",
    "home_assistant",
    "esphome",
    "zigbee",
    "zwave",
    "wifi",
    "bluetooth",
    "devices",
    "sensors",
    "switches",
    "lighting",
    "locks",
    "cameras",
    "energy",
    "presence",
    "voice",
    "automation_ideas",
    "integrations",
    "developer_tools",
    "privacy",
    "security",
    "standards",
    "industry",
}


class Classification(BaseModel):
    topics: list[str] = Field(default_factory=list)
    relevance_score: int = Field(ge=0, le=100)
    novelty_score: int = Field(ge=0, le=100)
    importance_score: int = Field(ge=0, le=100)
    personal_interest_score: int = Field(ge=0, le=100)
    decision: Literal["keep", "reject"]
    reason: str
    why_it_matters: str
    why_you_care: str
    claims_to_verify: list[str] = Field(default_factory=list)
    summary: str

    @field_validator("topics")
    @classmethod
    def filter_topics(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for topic in value:
            key = topic.strip().lower().replace(" ", "_").replace("-", "_")
            if key == "z_wave":
                key = "zwave"
            if key in ALLOWED_TOPICS and key not in cleaned:
                cleaned.append(key)
        return cleaned
