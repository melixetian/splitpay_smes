from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventType(str, Enum):
    SIGNUP_COMPLETED = "signup_completed"
    LINK_BANK_SUCCESS = "link_bank_success"
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_FAILED = "payment_failed"


class InboundEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    event_type: EventType
    event_timestamp: datetime
    properties: dict[str, Any] = Field(default_factory=dict)
    user_traits: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_timestamp")
    @classmethod
    def ensure_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("event_timestamp must include timezone and be UTC")
        return value.astimezone(timezone.utc)


class EventIngestResponse(BaseModel):
    status: str
