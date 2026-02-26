import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuditEndpoint:
    EVENTS_URL = "/events"
    AUDIT_URL_TEMPLATE = "/audit/{user_id}"

    async def post_event(self, client: AsyncClient, payload: dict):
        return await client.post(self.EVENTS_URL, json=payload)

    def audit_url(self, user_id: str) -> str:
        return self.AUDIT_URL_TEMPLATE.format(user_id=user_id)

    async def test_bank_link_nudge_requires_signup_within_24h(self, client: AsyncClient):
        user_no_signup = "u_test_no_signup"
        user_expired_signup = "u_test_expired_signup"
        user_recent_signup = "u_test_recent_signup"

        await self.post_event(
            client,
            {
                "user_id": user_no_signup,
                "event_type": "link_bank_success",
                "event_timestamp": "2025-11-01T12:00:00Z",
                "properties": {},
                "user_traits": {},
            },
        )
        audit_no_signup = await client.get(self.audit_url(user_no_signup))
        messages = audit_no_signup.json()["message_decisions"]
        assert not any(item["template_name"] == "BANK_LINK_NUDGE_SMS" for item in messages)

        await self.post_event(
            client,
            {
                "user_id": user_expired_signup,
                "event_type": "signup_completed",
                "event_timestamp": "2025-10-30T10:00:00Z",
                "properties": {},
                "user_traits": {"marketing_opt_in": False},
            },
        )
        await self.post_event(
            client,
            {
                "user_id": user_expired_signup,
                "event_type": "link_bank_success",
                "event_timestamp": "2025-11-01T12:00:00Z",
                "properties": {},
                "user_traits": {},
            },
        )
        audit_expired = await client.get(self.audit_url(user_expired_signup))
        messages = audit_expired.json()["message_decisions"]
        assert not any(item["template_name"] == "BANK_LINK_NUDGE_SMS" for item in messages)

        await self.post_event(
            client,
            {
                "user_id": user_recent_signup,
                "event_type": "signup_completed",
                "event_timestamp": "2025-11-01T10:00:00Z",
                "properties": {},
                "user_traits": {"marketing_opt_in": False},
            },
        )
        await self.post_event(
            client,
            {
                "user_id": user_recent_signup,
                "event_type": "link_bank_success",
                "event_timestamp": "2025-11-01T12:00:00Z",
                "properties": {},
                "user_traits": {},
            },
        )
        audit_recent = await client.get(self.audit_url(user_recent_signup))
        messages = audit_recent.json()["message_decisions"]
        bank_msgs = [item for item in messages if item["template_name"] == "BANK_LINK_NUDGE_SMS"]
        assert len(bank_msgs) == 1
        assert bank_msgs[0]["status"] == "sent"

    async def test_insufficient_funds_once_per_utc_day(self, client: AsyncClient):
        user_id = "u_test_daily_dedup"

        await self.post_event(
            client,
            {
                "user_id": user_id,
                "event_type": "payment_failed",
                "event_timestamp": "2025-11-01T13:00:00Z",
                "properties": {"failure_reason": "INSUFFICIENT_FUNDS", "attempt_number": 1},
                "user_traits": {},
            },
        )
        await self.post_event(
            client,
            {
                "user_id": user_id,
                "event_type": "payment_failed",
                "event_timestamp": "2025-11-01T14:00:00Z",
                "properties": {"failure_reason": "INSUFFICIENT_FUNDS", "attempt_number": 1},
                "user_traits": {},
            },
        )
        await self.post_event(
            client,
            {
                "user_id": user_id,
                "event_type": "payment_failed",
                "event_timestamp": "2025-11-02T09:00:00Z",
                "properties": {"failure_reason": "INSUFFICIENT_FUNDS", "attempt_number": 1},
                "user_traits": {},
            },
        )

        audit = await client.get(self.audit_url(user_id))
        messages = audit.json()["message_decisions"]
        decisions = [item for item in messages if item["template_name"] == "INSUFFICIENT_FUNDS_EMAIL"]

        assert len(decisions) == 3
        assert decisions[0]["status"] == "sent"
        assert decisions[1]["status"] == "suppressed"
        assert "already sent today at" in decisions[1]["suppression_reason"]
        assert decisions[2]["status"] == "sent"

    async def test_payment_failed_attempt_three_triggers_high_risk_alert(self, client: AsyncClient):
        user_id = "u_test_high_risk"

        await self.post_event(
            client,
            {
                "user_id": user_id,
                "event_type": "payment_failed",
                "event_timestamp": "2025-11-01T13:00:00Z",
                "properties": {"failure_reason": "NETWORK_ERROR", "attempt_number": 3},
                "user_traits": {},
            },
        )

        audit = await client.get(self.audit_url(user_id))
        messages = audit.json()["message_decisions"]

        high_risk = [item for item in messages if item["template_name"] == "HIGH_RISK_ALERT"]
        insufficient = [item for item in messages if item["template_name"] == "INSUFFICIENT_FUNDS_EMAIL"]

        assert len(high_risk) == 1
        assert high_risk[0]["status"] == "sent"
        assert len(insufficient) == 0
