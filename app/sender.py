import logging

from app.rules import MessageCandidate
from app.schemas.event import InboundEvent

logger = logging.getLogger(__name__)


async def send_email_stub(event: InboundEvent, candidate: MessageCandidate) -> None:
    logger.info(
        "Outbound EMAIL request user_id=%s template=%s reason=%s",
        event.user_id,
        candidate.template_name.value,
        candidate.reason,
    )


async def send_sms_stub(event: InboundEvent, candidate: MessageCandidate) -> None:
    logger.info(
        "Outbound SMS request user_id=%s template=%s reason=%s",
        event.user_id,
        candidate.template_name.value,
        candidate.reason,
    )


async def send_internal_alert_stub(event: InboundEvent, candidate: MessageCandidate) -> None:
    logger.info(
        "Outbound INTERNAL_ALERT request user_id=%s template=%s reason=%s",
        event.user_id,
        candidate.template_name.value,
        candidate.reason,
    )


async def send_message_stub(event: InboundEvent, candidate: MessageCandidate) -> None:
    if candidate.channel == "email":
        await send_email_stub(event, candidate)
        return
    if candidate.channel == "sms":
        await send_sms_stub(event, candidate)
        return
    if candidate.channel == "internal_alert":
        await send_internal_alert_stub(event, candidate)
        return

    raise ValueError(f"Unsupported channel: {candidate.channel}")
