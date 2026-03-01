import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestEventsEndpoint:
    EVENTS_URL = "/events"
    AUDIT_URL_TEMPLATE = "/audit/{user_id}"

    async def post_event(self, client: AsyncClient, payload: dict):
        return await client.post(self.EVENTS_URL, json=payload)

    def audit_url(self, user_id: str) -> str:
        return self.AUDIT_URL_TEMPLATE.format(user_id=user_id)

    async def assert_post_ok(self, client: AsyncClient, payload: dict):
        response = await self.post_event(client, payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        return response

    async def test_welcome_email_once_ever_and_suppression_visible_in_audit(self, client: AsyncClient):
        user_id = "u_test_welcome"

        first = {
            "user_id": user_id,
            "event_type": "signup_completed",
            "event_timestamp": "2025-11-01T10:00:00Z",
            "properties": {},
            "user_traits": {"marketing_opt_in": True},
        }
        second = {
            "user_id": user_id,
            "event_type": "signup_completed",
            "event_timestamp": "2025-11-01T10:05:00Z",
            "properties": {},
            "user_traits": {"marketing_opt_in": True},
        }

        await self.assert_post_ok(client, first)
        await self.assert_post_ok(client, second)

        audit = await client.get(self.audit_url(user_id))
        assert audit.status_code == 200
        messages = audit.json()["message_decisions"]
        decisions = [item for item in messages if item["template_name"] == "WELCOME_EMAIL"]

        assert len(decisions) == 2
        assert decisions[0]["status"] == "suppressed"
        assert "already sent at" in decisions[0]["suppression_reason"]
        assert decisions[1]["status"] == "sent"

    async def test_link_bank_success_with_recent_signup_returns_ok_and_creates_message(self, client: AsyncClient):
        user_id = "u_test_events_bank_link"

        await self.assert_post_ok(
            client,
            {
                "user_id": user_id,
                "event_type": "signup_completed",
                "event_timestamp": "2025-11-01T10:00:00Z",
                "properties": {},
                "user_traits": {"marketing_opt_in": False},
            },
        )
        await self.assert_post_ok(
            client,
            {
                "user_id": user_id,
                "event_type": "link_bank_success",
                "event_timestamp": "2025-11-01T12:00:00Z",
                "properties": {},
                "user_traits": {},
            },
        )

        audit = await client.get(self.audit_url(user_id))
        messages = audit.json()["message_decisions"]
        decisions = [item for item in messages if item["template_name"] == "BANK_LINK_NUDGE_SMS"]

        assert len(decisions) == 1
        assert decisions[0]["status"] == "sent"

    async def test_payment_failed_insufficient_funds_and_high_risk_returns_ok(self, client: AsyncClient):
        user_id = "u_test_events_multi_trigger"

        await self.assert_post_ok(
            client,
            {
                "user_id": user_id,
                "event_type": "payment_failed",
                "event_timestamp": "2025-11-01T13:00:00Z",
                "properties": {"failure_reason": "INSUFFICIENT_FUNDS", "attempt_number": 3},
                "user_traits": {},
            },
        )
        await self.assert_post_ok(
            client,
            {
                "user_id": user_id,
                "event_type": "payment_failed",
                "event_timestamp": "2025-11-01T14:00:00Z",
                "properties": {"failure_reason": "INSUFFICIENT_FUNDS", "attempt_number": 4},
                "user_traits": {},
            },
        )

        audit = await client.get(self.audit_url(user_id))
        messages = audit.json()["message_decisions"]

        insufficient = [item for item in messages if item["template_name"] == "INSUFFICIENT_FUNDS_EMAIL"]
        high_risk = [item for item in messages if item["template_name"] == "HIGH_RISK_ALERT"]

        assert len(insufficient) == 2
        assert insufficient[0]["status"] == "suppressed"
        assert insufficient[1]["status"] == "sent"
        assert len(high_risk) == 2
        assert all(item["status"] == "sent" for item in high_risk)

    async def test_payment_initiated_without_matching_rules_returns_ok_with_no_messages(self, client: AsyncClient):
        user_id = "u_test_events_no_match"

        await self.assert_post_ok(
            client,
            {
                "user_id": user_id,
                "event_type": "payment_initiated",
                "event_timestamp": "2025-11-01T11:00:00Z",
                "properties": {"amount": 100.0},
                "user_traits": {},
            },
        )

        audit = await client.get(self.audit_url(user_id))
        assert audit.status_code == 200
        assert audit.json()["events"]
        assert audit.json()["message_decisions"] == []

    async def test_signup_without_marketing_opt_in_creates_no_welcome_message(self, client: AsyncClient):
        user_id = "u_test_signup_no_opt_in"

        await self.assert_post_ok(
            client,
            {
                "user_id": user_id,
                "event_type": "signup_completed",
                "event_timestamp": "2025-11-01T10:00:00Z",
                "properties": {},
                "user_traits": {"marketing_opt_in": False},
            },
        )

        audit = await client.get(self.audit_url(user_id))
        assert audit.status_code == 200
        messages = audit.json()["message_decisions"]
        assert not any(item["template_name"] == "WELCOME_EMAIL" for item in messages)

    async def test_payment_failed_without_matching_conditions_creates_no_messages(self, client: AsyncClient):
        user_id = "u_test_payment_failed_no_match"

        await self.assert_post_ok(
            client,
            {
                "user_id": user_id,
                "event_type": "payment_failed",
                "event_timestamp": "2025-11-01T10:00:00Z",
                "properties": {"failure_reason": "NETWORK_ERROR", "attempt_number": 2},
                "user_traits": {},
            },
        )

        audit = await client.get(self.audit_url(user_id))
        assert audit.status_code == 200
        assert audit.json()["events"]
        assert audit.json()["message_decisions"] == []

    async def test_invalid_payload_returns_422(self, client: AsyncClient):
        response = await client.post(
            self.EVENTS_URL,
            json={
                "event_type": "signup_completed",
                "event_timestamp": "2025-11-01T10:00:00Z",
                "properties": {},
                "user_traits": {},
            },
        )
        assert response.status_code == 422

    async def test_timestamp_without_timezone_returns_422(self, client: AsyncClient):
        response = await client.post(
            self.EVENTS_URL,
            json={
                "user_id": "u_test_bad_timestamp",
                "event_type": "signup_completed",
                "event_timestamp": "2025-11-01T10:00:00",
                "properties": {},
                "user_traits": {"marketing_opt_in": True},
            },
        )
        assert response.status_code == 422
