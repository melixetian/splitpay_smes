#!/usr/bin/env sh

# Example curl calls for manual API checks.

BASE_URL="http://localhost:8000"
USER_ID="u_demo_002"

echo "Using BASE_URL=${BASE_URL}"
echo "Using USER_ID=${USER_ID}"

echo "1) signup_completed -> should trigger WELCOME_EMAIL when marketing_opt_in=true"
curl -X POST "${BASE_URL}/events" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"${USER_ID}\",
    \"event_type\": \"signup_completed\",
    \"event_timestamp\": \"2025-11-01T10:00:00Z\",
    \"properties\": {},
    \"user_traits\": {
      \"marketing_opt_in\": true,
      \"email\": \"maria@example.com\"
    }
  }" \
  | jq

echo ""

echo "2) duplicate signup_completed -> WELCOME_EMAIL should be suppressed (once ever)"
curl -X POST "${BASE_URL}/events" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"${USER_ID}\",
    \"event_type\": \"signup_completed\",
    \"event_timestamp\": \"2025-11-01T10:05:00Z\",
    \"properties\": {},
    \"user_traits\": {
      \"marketing_opt_in\": true
    }
  }" \
  | jq

echo ""

echo "3) link_bank_success within 24h of signup -> BANK_LINK_NUDGE_SMS"
curl -X POST "${BASE_URL}/events" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"${USER_ID}\",
    \"event_type\": \"link_bank_success\",
    \"event_timestamp\": \"2025-11-01T12:00:00Z\",
    \"properties\": {},
    \"user_traits\": {}
  }" \
  | jq

echo ""

echo "4) payment_failed insufficient funds + attempt_number>=3
-> INSUFFICIENT_FUNDS_EMAIL and HIGH_RISK_ALERT"
curl -X POST "${BASE_URL}/events" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"${USER_ID}\",
    \"event_type\": \"payment_failed\",
    \"event_timestamp\": \"2025-11-01T13:00:00Z\",
    \"properties\": {
      \"failure_reason\": \"INSUFFICIENT_FUNDS\",
      \"attempt_number\": 3
    },
    \"user_traits\": {}
  }" \
  | jq

echo ""

echo "5) audit endpoint -> events + decisions + suppression reasons"
curl "${BASE_URL}/audit/${USER_ID}" | jq

echo ""

echo "6) invalid payload example -> should return 422"
curl -X POST "${BASE_URL}/events" \
  -H "Content-Type: application/json" \
  -d "{
    \"event_type\": \"signup_completed\",
    \"event_timestamp\": \"2025-11-01T10:00:00Z\",
    \"properties\": {},
    \"user_traits\": {}
  }" \
  | jq

echo ""
