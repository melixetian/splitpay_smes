from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol

from app.schemas.event import EventType, InboundEvent
from app.schemas.template import TemplateName


class EventLookupPort(Protocol):
    async def has_event_in_range(
        self,
        user_id: str,
        event_type: str,
        start_timestamp: datetime,
        end_timestamp: datetime,
    ) -> bool: ...


class DedupPolicy(str, Enum):
    NONE = "none"
    ONCE_EVER = "once_ever"
    ONCE_PER_UTC_DAY = "once_per_utc_day"


@dataclass(frozen=True)
class MessageCandidate:
    template_name: TemplateName
    channel: str
    reason: str
    dedup_policy: DedupPolicy


@dataclass(frozen=True)
class RuleContext:
    event: InboundEvent
    event_lookup: EventLookupPort


class Rule(ABC):
    @abstractmethod
    async def evaluate(self, context: RuleContext) -> MessageCandidate | None:
        raise NotImplementedError


class WelcomeEmailRule(Rule):
    async def evaluate(self, context: RuleContext) -> MessageCandidate | None:
        event = context.event
        if event.event_type != EventType.SIGNUP_COMPLETED:
            return None
        if event.user_traits.get("marketing_opt_in") is not True:
            return None
        return MessageCandidate(
            template_name=TemplateName.WELCOME_EMAIL,
            channel="email",
            reason="signup_completed with marketing_opt_in=true",
            dedup_policy=DedupPolicy.ONCE_EVER,
        )


class BankLinkNudgeSmsRule(Rule):
    async def evaluate(self, context: RuleContext) -> MessageCandidate | None:
        event = context.event
        if event.event_type != EventType.LINK_BANK_SUCCESS:
            return None

        has_signup = await context.event_lookup.has_event_in_range(
            user_id=event.user_id,
            event_type=EventType.SIGNUP_COMPLETED.value,
            start_timestamp=event.event_timestamp - timedelta(hours=24),
            end_timestamp=event.event_timestamp,
        )
        if not has_signup:
            return None

        return MessageCandidate(
            template_name=TemplateName.BANK_LINK_NUDGE_SMS,
            channel="sms",
            reason="link_bank_success and signup_completed in previous 24h",
            dedup_policy=DedupPolicy.NONE,
        )


class InsufficientFundsEmailRule(Rule):
    async def evaluate(self, context: RuleContext) -> MessageCandidate | None:
        event = context.event
        if event.event_type != EventType.PAYMENT_FAILED:
            return None
        if event.properties.get("failure_reason") != "INSUFFICIENT_FUNDS":
            return None
        return MessageCandidate(
            template_name=TemplateName.INSUFFICIENT_FUNDS_EMAIL,
            channel="email",
            reason='payment_failed with failure_reason="INSUFFICIENT_FUNDS"',
            dedup_policy=DedupPolicy.ONCE_PER_UTC_DAY,
        )


class HighRiskAlertRule(Rule):
    async def evaluate(self, context: RuleContext) -> MessageCandidate | None:
        event = context.event
        if event.event_type != EventType.PAYMENT_FAILED:
            return None

        attempt_number = event.properties.get("attempt_number")
        if not isinstance(attempt_number, int):
            return None
        if attempt_number < 3:
            return None

        return MessageCandidate(
            template_name=TemplateName.HIGH_RISK_ALERT,
            channel="internal_alert",
            reason="payment_failed with attempt_number >= 3",
            dedup_policy=DedupPolicy.NONE,
        )


def build_default_rules() -> list[Rule]:
    return [
        WelcomeEmailRule(),
        BankLinkNudgeSmsRule(),
        InsufficientFundsEmailRule(),
        HighRiskAlertRule(),
    ]


async def evaluate_rules(rules: list[Rule], context: RuleContext) -> list[MessageCandidate]:
    matches: list[MessageCandidate] = []
    for rule in rules:
        candidate = await rule.evaluate(context)
        if candidate is not None:
            matches.append(candidate)
    return matches
