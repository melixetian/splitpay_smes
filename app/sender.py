import logging

from app.rules import MessageCandidate
from app.schemas.event import InboundEvent

logger = logging.getLogger(__name__)


async def send_message_stub(event: InboundEvent, candidate: MessageCandidate) -> None:
    logger.info(
        "Outbound send request user_id=%s template=%s channel=%s reason=%s",
        event.user_id,
        candidate.template_name,
        candidate.channel,
        candidate.reason,
    )
