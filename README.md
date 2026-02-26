# SplitPay Marketing Event Service (MVP)

Minimal FastAPI service that ingests marketing events, evaluates messaging rules, applies suppression logic, and exposes an audit endpoint.

---

## Setup & Run

```sh
make install    # create venv, install dependencies, build Docker image
make migrate    # apply database migrations
make run        # start the service 
```

#### Other commands:

```sh
make logs       # open logs
make test       # run tests
make down       # stop the service
```

All commands are listed in [Makefile](Makefile).

Service will be available at:

[http://localhost:8000](http://localhost:8000)

---

## Example: POST /events

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u_12345",
    "event_type": "payment_failed",
    "event_timestamp": "2025-10-31T19:22:11Z",
    "properties": {
      "amount": 1425.00,
      "attempt_number": 3,
      "failure_reason": "INSUFFICIENT_FUNDS"
    },
    "user_traits": {
      "email": "maria@example.com",
      "country": "PT",
      "marketing_opt_in": true,
      "risk_segment": "MEDIUM"
    }
  }'
```

---

## Example: GET /audit/{user_id}

```bash
curl http://localhost:8000/audit/u_12345
```

---

## Assumptions

* Events are processed synchronously.
* Duplicate events are stored; suppression is applied at message decision level.
* Timestamps are treated as UTC.
* Outbound sending is represented by a stub.

This implementation is intentionally minimal and focused on correctness and clarity.
