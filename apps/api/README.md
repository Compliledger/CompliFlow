# CompliFlow API

The CompliFlow API is the FastAPI service that implements the **programmable
enforcement layer for tokenized markets**. It exposes the five core capabilities
of CompliFlow as HTTP endpoints:

- **Execution decisioning** — `POST /v1/intent/evaluate`
- **Proof generation & verification** — `POST /v1/receipt/verify`
- **Yellow execution submission** — `POST /v1/yellow/...`
- **Settlement validation** — `POST /v1/settlement/validate`
- **Audit logging** — `GET  /v1/audit/logs`
- **Session-key management** — `POST /v1/session/...`

For positioning, lifecycle diagrams, and where this service fits in the broader
stack, see the [root README](../../README.md) and
[`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md). For per-endpoint reference,
see [`docs/API.md`](../../docs/API.md).

---

## Capabilities

### Execution decisioning

The policy engine evaluates each `TradeIntent` and returns a deterministic,
versioned decision (`ALLOW` / `DENY` / `ALLOW_WITH_CONDITIONS`) with structured
reason codes. The same decision shape is used by the settlement engine, so
downstream consumers (audit log, UI, evidence storage) see one unified format.

### Proof generation

Every approved decision is paired with an **Ed25519-signed receipt** and a
proof bundle that captures the canonical intent, the decision, the policy
version, and a signature. Receipts can be re-verified via the API at any time.

### Yellow execution submission

Approved intents are forwarded into Yellow Network state channels via the
project's WebSocket RPC integration, carrying the signed receipt as evidence.
Session-key preflight runs both locally and against Yellow before submission.

### Settlement validation

Once an order has progressed through Yellow's execution-status states
(`SUBMITTED → MATCHED → ESCROW_LOCKED → SETTLED`), the settlement engine
re-validates the trade against the original intent, the stored proof bundle,
and the current execution status. The result is a structured settlement
decision and a hashed evidence record. The engine never moves funds.

### Audit logging

Every decision, submission, and settlement event is written to an append-only
audit log keyed by `order_id`, `wallet`, `session_key`, and `policy_version`,
and is queryable through the audit API.

---

## Execution & Settlement Lifecycle (API view)

```
POST /v1/session/create            → register a session key
POST /v1/intent/evaluate           → policy decision + signed receipt
POST /v1/yellow/order/submit       → submit approved intent to Yellow
POST /v1/settlement/validate       → re-validate matched/settled order
POST /v1/receipt/verify            → verify a previously issued receipt
GET  /v1/audit/logs                → query the append-only audit trail
```

---

## Demo Mode vs Enforcement Mode

The API exposes the same surface in both modes:

- **Demo mode (default in the MVP).** Decisions, proofs, and settlement
  validations are produced and logged, but they are advisory — Yellow
  submissions proceed even when driven by scripted or synthetic flows. Used
  for integration, demos, and conformance.
- **Enforcement mode.** A `DENY` from `/v1/intent/evaluate` blocks Yellow
  submission, and a `DENY` from `/v1/settlement/validate` flags a matched
  trade as non-final. The decision shape, proof format, and audit schema are
  identical to demo mode.

---

## Setup

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open the interactive docs at <http://127.0.0.1:8000/docs>.

## Tests

```bash
pytest -q
```

## Docker

```bash
docker build -t compliflow-api .
docker run -p 8000:8000 compliflow-api
```

---

## Status

This service is the MVP implementation of the CompliFlow enforcement layer.
Yellow sandbox is the only supported execution venue today; the decision,
proof, and audit schemas are stable across both demo and enforcement modes.
