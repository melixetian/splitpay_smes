import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.repository import Repository
from app.rules import DedupPolicy, RuleContext, build_default_rules, evaluate_rules
from app.schemas.audit import AuditEventItem, AuditMessageItem, AuditResponse
from app.schemas.event import EventIngestResponse, InboundEvent
from app.sender import send_message_stub

logger = logging.getLogger(__name__)


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = Repository(session)
        self.rules = build_default_rules()

    async def ingest_event(self, event: InboundEvent) -> EventIngestResponse:
        try:
            await self.repository.create_event(event)
            candidates = await evaluate_rules(
                rules=self.rules,
                context=RuleContext(event=event, event_lookup=self.repository),
            )

            for candidate in candidates:
                status = "sent"
                suppression_reason: str | None = None

                if candidate.dedup_policy == DedupPolicy.ONCE_EVER:
                    previous = await self.repository.latest_sent(event.user_id, candidate.template_name)
                    if previous is not None:
                        status = "suppressed"
                        suppression_reason = (
                            f"skipped {candidate.template_name}: already sent at {previous.timestamp.isoformat()}"
                        )
                elif candidate.dedup_policy == DedupPolicy.ONCE_PER_UTC_DAY:
                    previous_today = await self.repository.latest_sent_for_utc_date(
                        user_id=event.user_id,
                        template_name=candidate.template_name,
                        utc_day=event.event_timestamp.date(),
                    )
                    if previous_today is not None:
                        status = "suppressed"
                        suppression_reason = (
                            f"skipped {candidate.template_name}: "
                            f"already sent today at {previous_today.timestamp.isoformat()}"
                        )

                await self.repository.create_message_decision(
                    user_id=event.user_id,
                    template_name=candidate.template_name,
                    channel=candidate.channel,
                    timestamp=event.event_timestamp,
                    reason=candidate.reason,
                    status=status,
                    suppression_reason=suppression_reason,
                )

                if status == "sent":
                    await send_message_stub(event, candidate)
                    logger.debug("Message was sent successfully.")
                else:
                    logger.debug("Message was suppressed.")

            await self.session.commit()
            return EventIngestResponse(status="ok")
        except Exception:
            await self.session.rollback()
            logger.exception("Error occurred while processing event")
            raise

    async def get_audit(self, user_id: str) -> AuditResponse:
        events = await self.repository.list_events_for_user(user_id)
        messages = await self.repository.list_messages_for_user(user_id)

        return AuditResponse(
            user_id=user_id,
            events=[
                AuditEventItem(
                    id=event.id,
                    user_id=event.user_id,
                    event_type=event.event_type,
                    event_timestamp=event.event_timestamp,
                    raw_payload=json.loads(event.raw_payload),
                )
                for event in events
            ],
            message_decisions=[
                AuditMessageItem(
                    id=message.id,
                    user_id=message.user_id,
                    template_name=message.template_name,
                    channel=message.channel,
                    timestamp=message.timestamp,
                    reason=message.reason,
                    status=message.status,
                    suppression_reason=message.suppression_reason,
                )
                for message in messages
            ],
        )
