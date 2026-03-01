import json
from datetime import date, datetime, time, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.event import InboundEvent
from app.schemas.template import TemplateName
from app.storage.models import EventRecord, MessageRecord


class Repository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_event(self, event: InboundEvent) -> EventRecord:
        record = EventRecord(
            user_id=event.user_id,
            event_type=event.event_type.value,
            event_timestamp=event.event_timestamp,
            raw_payload=json.dumps(event.model_dump(mode="json")),
        )
        self.session.add(record)
        return record

    async def has_event_in_range(
        self,
        user_id: str,
        event_type: str,
        start_timestamp: datetime,
        end_timestamp: datetime,
    ) -> bool:
        query: sa.Select[tuple[int]] = (
            sa.select(EventRecord.id)
            .where(EventRecord.user_id == user_id)
            .where(EventRecord.event_type == event_type)
            .where(EventRecord.event_timestamp >= start_timestamp)
            .where(EventRecord.event_timestamp <= end_timestamp)
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def list_events_for_user(self, user_id: str) -> list[EventRecord]:
        query = (
            sa.select(EventRecord)
            .where(EventRecord.user_id == user_id)
            .order_by(EventRecord.event_timestamp.desc(), EventRecord.id.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_message_decision(
        self,
        user_id: str,
        template_name: TemplateName,
        channel: str,
        timestamp: datetime,
        reason: str,
        status: str,
        suppression_reason: str | None,
    ) -> MessageRecord:
        record = MessageRecord(
            user_id=user_id,
            template_name=template_name.value,
            channel=channel,
            timestamp=timestamp,
            reason=reason,
            status=status,
            suppression_reason=suppression_reason,
        )
        self.session.add(record)
        return record

    async def latest_sent(self, user_id: str, template_name: TemplateName) -> MessageRecord | None:
        query: sa.Select[tuple[MessageRecord]] = (
            sa.select(MessageRecord)
            .where(MessageRecord.user_id == user_id)
            .where(MessageRecord.template_name == template_name.value)
            .where(MessageRecord.status == "sent")
            .order_by(MessageRecord.timestamp.desc(), MessageRecord.id.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def latest_sent_for_utc_date(
        self,
        user_id: str,
        template_name: TemplateName,
        utc_day: date | None = None,
    ) -> MessageRecord | None:
        start = datetime.combine(utc_day, time.min, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        query: sa.Select[tuple[MessageRecord]] = (
            sa.select(MessageRecord)
            .where(MessageRecord.user_id == user_id)
            .where(MessageRecord.template_name == template_name.value)
            .where(MessageRecord.status == "sent")
            .where(MessageRecord.timestamp >= start)
            .where(MessageRecord.timestamp < end)
            .order_by(MessageRecord.timestamp.desc(), MessageRecord.id.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_messages_for_user(self, user_id: str) -> list[MessageRecord]:
        query = (
            sa.select(MessageRecord)
            .where(MessageRecord.user_id == user_id)
            .order_by(MessageRecord.timestamp.desc(), MessageRecord.id.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
