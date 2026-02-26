# Task:

Your team runs a marketing pipeline for a fintech app. When a new user signs up, you collect behavioral events (`signup`, `link_bank_success`, `payment_initiated`, `payment_failed`, etc). Based on those events and user attributes, you decide which lifecycle email/sms to send and you trigger those messages via a provider (Iterable, Braze, etc.).

Right now this pipeline is unreliable:

- Some users get duplicate messages
- Some users get nothing
- The growth team can’t explain why a given user did or didn’t get a message

## Your task

Build a small Python service that can do the following:

### A. Accept inbound events

Ingest JSON “events” via an HTTP endpoint.

Example event payload:

```json
{
    "user_id": "u_12345",
    "event_type": "payment_failed",
    "event_timestamp": "2025-10-31T19:22:11Z",
    "properties": {
        "amount": 1425.00,
        "attempt_number": 2,
        "failure_reason": "INSUFFICIENT_FUNDS"
    },
    "user_traits": {
        "email": "maria@example.com",
        "country": "PT",
        "marketing_opt_in": true,
        "risk_segment": "MEDIUM"
    }
}
```

You can assume events will come in for:
- `signup_completed`
- `link_bank_success`
- `payment_initiated`
- `payment_failed`

### B. Apply messaging rules

When an event comes in, your service should decide if we should send a marketing message (email or SMS). The logic should be declarative/configurable, not hardcoded if/else spaghetti everywhere.

For this exercise, implement at least these rules:

if `signup_completed AND user_traits.marketing_opt_in == true`,
send the `WELCOME_EMAIL`.

If `link_bank_success within 24h of signup_completed`,
send `BANK_LINK_NUDGE_SMS`
(tone: “you’re almost ready to pay your rent”).

If `payment_failed with failure_reason == "INSUFFICIENT_FUNDS"`,
send “INSUFFICIENT_FUNDS_EMAIL`,
BUT only once per user per calendar day.

If `payment_failed with attempt_number >= 3`,
escalate to `HIGH_RISK_ALERT`
(internal only, no user-facing send) so that CX can intervene.

You decide how to represent these rules (YAML, Python classes, whatever). We’re evaluating how cleanly you model it.

### C. De-duplication / suppression

Your service should prevent sending the same template to the same user more than allowed.

For example:
- We don’t want to send them 5 `INSUFFICIENT_FUNDS_EMAIL` messages in one day.
- We don’t want to send `WELCOME_EMAIL` twice.

### D. Produce an outbound “send request”

Instead of actually sending email/SMS, expose a stub function that would call Iterable (or whatever). Log or store the “intended send,” including:
- `user_id`
- `template_name` (`WELCOME_EMAIL`, etc.)
- `channel` ("email" or "sms" or "internal_alert")
- `timestamp`
- why we decided to send (short reason string)

### E. Expose an audit/debug endpoint

Growth and CX constantly ask “why didn’t Maria get the nudge?”

Expose an HTTP GET endpoint like `/audit/<user_id>` that returns:
- recent events we saw for that user
- messages we decided to send (or suppress)
- explanation for suppression (e.g. “skipped `INSUFFICIENT_FUNDS_EMAIL`: already sent today at 10:41Z”)

You can store data in memory or SQLite. In-memory is fine as long as it works in a single run.

## Non-functional expectations

1. Use Python 3.x.

2. Use something lightweight for the service layer (FastAPI or Flask are fine).

3. Don’t worry about login/auth for the endpoints.

4. Include a short README with:
- How to run it
- Example curl to `POST` an event
- Example curl to view `/audit/<user_id>`
