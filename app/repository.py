import json
from datetime import date, datetime, time, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.event import InboundEvent
from app.schemas.template import TemplateName
from app.storage.models import Event, Message


class Repository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_event(self, event: InboundEvent) -> Event:
        record = Event(
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
            sa.select(Event.id)
            .where(Event.user_id == user_id)
            .where(Event.event_type == event_type)
            .where(Event.event_timestamp >= start_timestamp)
            .where(Event.event_timestamp <= end_timestamp)
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def list_events_for_user(self, user_id: str) -> list[Event]:
        query = (
            sa.select(Event)
            .where(Event.user_id == user_id)
            .order_by(Event.event_timestamp.desc(), Event.id.desc())
            # SELECT * FROM events WHERE user_id = :user_id ORDER BY event_timestamp DESC id DESC
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
    ) -> Message:
        record = Message(
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

    async def latest_sent(self, user_id: str, template_name: TemplateName) -> Message | None:
        query: sa.Select[tuple[Message]] = (
            sa.select(Message)
            .where(Message.user_id == user_id)
            .where(Message.template_name == template_name.value)
            .where(Message.status == "sent")
            .order_by(Message.timestamp.desc(), Message.id.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def latest_sent_for_utc_date(
        self,
        user_id: str,
        template_name: TemplateName,
        utc_day: date | None = None,
    ) -> Message | None:
        start = datetime.combine(utc_day, time.min, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        query: sa.Select[tuple[Message]] = (
            sa.select(Message)
            .where(Message.user_id == user_id)
            .where(Message.template_name == template_name.value)
            .where(Message.status == "sent")
            .where(Message.timestamp >= start)
            .where(Message.timestamp < end)
            .order_by(Message.timestamp.desc(), Message.id.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_messages_for_user(self, user_id: str) -> list[Message]:
        query = (
            sa.select(Message)
            .where(Message.user_id == user_id)
            .order_by(Message.timestamp.desc(), Message.id.desc())
            # SELECT * FROM messages WHERE user_id = :user_id ORDER BY timestamp DESC id DESC
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
