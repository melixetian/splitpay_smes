from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.template import TemplateName


class AuditEventItem(BaseModel):
    id: int
    user_id: str
    event_type: str
    event_timestamp: datetime
    raw_payload: dict[str, Any]


class AuditMessageItem(BaseModel):
    id: int
    user_id: str
    template_name: TemplateName
    channel: str
    timestamp: datetime
    reason: str
    status: str
    suppression_reason: str | None


class AuditResponse(BaseModel):
    user_id: str
    events: list[AuditEventItem]
    message_decisions: list[AuditMessageItem]
