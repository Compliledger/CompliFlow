# CompliFlow API Reference

The CompliFlow API is the HTTP surface of the **programmable enforcement layer
for tokenized markets**. It exposes the five core capabilities of CompliFlow:

- Execution decisioning
- Proof generation and verification
- Yellow execution submission
- Settlement validation
- Audit logging
- Session-key management

For positioning and lifecycle context, see the [root README](../README.md) and
[`ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## Base URL

Local development: `http://localhost:8000`

Interactive docs:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication

The MVP does not require API authentication on inbound HTTP requests.
Authority is asserted *inside the payload* via session keys, which are
validated by `SessionService` and (when reachable) cross-checked with Yellow.

---

## Endpoint Map

| Capability                  | Method | Path                                  |
| --------------------------- | ------ | ------------------------------------- |
| Health                      | GET    | `/health`                             |
| Execution decisioning       | POST   | `/v1/intent/evaluate`                 |
| Proof verification          | POST   | `/v1/receipt/verify`                  |
| Session-key preflight       | POST   | `/v1/yellow/session/preflight`        |
| Yellow order submission     | POST   | `/v1/yellow/order/submit`             |
| Yellow order status         | GET    | `/v1/yellow/order/{order_id}/status`  |
| Settlement validation       | POST   | `/v1/settlement/validate`             |
| Session-key create          | POST   | `/v1/session/create`                  |
| Audit log query             | GET    | `/v1/audit/logs`                      |

The exact request/response models are also published live in the OpenAPI
schema at `/openapi.json` and through the Swagger UI.

---

## Health

### `GET /health`

Liveness probe.

**Response 200**

```json
{ "status": "healthy" }
```

---

## Execution Decisioning

### `POST /v1/intent/evaluate`

Evaluates a `TradeIntent` against the policy engine. Performs session-key
preflight, runs deterministic policy rules, signs a receipt, generates a
v1.0 proof bundle, and writes an audit-log entry.

**Request**

```json
{
  "session_key": "sess_abc123",
  "user_wallet": "0xabc...",
  "side": "BUY",
  "amount": 100,
  "price": 50000,
  "asset": "ETH-USDC",
  "expires_at": 1735689600,
  "jurisdiction": "US"
}
```

**Response 200**

```json
{
  "payload": { "intent": { "...": "..." }, "decision": { "decision": "ALLOW", "reason_codes": [], "policy_version": "..." } },
  "signature": "<base64 ed25519 signature>",
  "receipt_hash": "<sha256 of canonical payload>",
  "order_id": "order_<uuid12>",
  "proof_bundle": {
    "proof_version": "1.0",
    "issued_at": 1735689000,
    "expires_at": 1735689600,
    "intent_hash": "...",
    "decision_hash": "...",
    "proof_hash": "...",
    "wallet": "0xabc...",
    "session_key_hash": "...",
    "decision": { "decision": "ALLOW", "reason_codes": [], "policy_version": "..." },
    "signature": "...",
    "public_key": "..."
  }
}
```

**Errors**

- `403` — session validation failed. The body contains the failure reason and
  a denial-shaped decision so callers can treat the result uniformly with a
  policy `DENY`.
- `422` — request validation error.

In **enforcement mode**, a `DENY` decision blocks downstream Yellow
submission. In **demo mode**, the same decision is produced and logged but
treated as advisory.

---

## Proof Generation & Verification

### `POST /v1/receipt/verify`

Verifies either a v1.0 proof bundle (preferred) or the legacy
`{ payload, signature }` shape returned by older clients.

**Response 200 (valid)**

```json
{ "valid": true }
```

**Response 200 (invalid)**

```json
{ "valid": false, "reason": "invalid_signature" }
```

Possible `reason` values include `invalid_encoding`, `invalid_signature`,
and `verification_error`.

---

## Yellow Execution Submission

### `POST /v1/yellow/session/preflight`

Validates a session key locally and (when reachable) against the Yellow
sandbox.

**Request**

```json
{ "session_key": "sess_abc123", "wallet": "0xabc..." }
```

**Response 200**

```json
{
  "valid": true,
  "session_key": "sess_abc123",
  "wallet": "0xabc...",
  "expires_at": 1735689600,
  "allowance_remaining": 999000.0,
  "yellow_status": "available"
}
```

If Yellow cannot be reached but the local session is valid, `yellow_status`
will be `"unavailable"` and the upstream-only fields will be `null`.

### `POST /v1/yellow/order/submit`

Submits an approved intent (with its receipt) into the Yellow channel.
Re-runs session preflight, consumes allowance, forwards to Yellow over the
WebSocket RPC, and writes audit-log entries for submission and status
change.

**Request**

```json
{
  "intent": { "session_key": "sess_abc123", "user_wallet": "0xabc...", "side": "BUY", "amount": 100, "price": 50000, "asset": "ETH-USDC", "expires_at": 1735689600 },
  "receipt": { "payload": { "...": "..." }, "signature": "...", "receipt_hash": "...", "order_id": "order_..." }
}
```

**Response 200**

```json
{
  "order_id": "order_...",
  "status": "SUBMITTED",
  "details": { "...": "..." }
}
```

**Errors**

- `403` — session validation failed or insufficient allowance.
- `500` — Yellow rejected the submission.

### `GET /v1/yellow/order/{order_id}/status`

Returns the current execution status reported by Yellow for an order.
Status values follow the execution lifecycle:
`SUBMITTED → MATCHED → ESCROW_LOCKED → SETTLED`.

---

## Settlement Validation

### `POST /v1/settlement/validate`

Independently re-validates a matched or settled trade against the original
intent, the stored receipt, and the current execution status. Produces a
structured settlement decision in the same shape as a policy decision.

**Request**

```json
{
  "order_id": "order_...",
  "intent": { "...": "..." },
  "receipt": { "...": "..." },
  "execution_status": "SETTLED",
  "proofs": { "...": "..." }
}
```

`execution_status` must be one of
`SUBMITTED | MATCHED | ESCROW_LOCKED | SETTLED`.

**Response 200**

```json
{
  "decision": "ALLOW",
  "reason_codes": [],
  "human_reason": "Settlement evidence is consistent with the original decision.",
  "conditions": { "valid_until": null },
  "policy_version": "settlement.v1",
  "settlement_context": {
    "order_id": "order_...",
    "match_id": null,
    "proof_hash": "..."
  }
}
```

In **enforcement mode**, a `DENY` here flags the matched trade as non-final
pending remediation. In **demo mode** the result is recorded but advisory.
The settlement engine never moves funds and never mutates external state.

---

## Session-Key Management

### `POST /v1/session/create`

Registers a session key with an initial allowance. Used in both demo and
enforcement modes.

**Request**

```json
{ "session_key": "sess_abc123", "wallet": "0xabc...", "allowance": 1000000.0 }
```

**Response 200**

```json
{
  "status": "success",
  "message": "Session created successfully",
  "session_key": "sess_abc123",
  "wallet": "0xabc...",
  "allowance": 1000000.0,
  "remaining_allowance": 1000000.0,
  "is_active": true,
  "expires_at": "2026-04-23T14:00:00Z"
}
```

---

## Audit Logging

### `GET /v1/audit/logs`

Queries the append-only audit log. Every decision, submission, status
change, and settlement validation is recorded against an `order_id` and
indexed by wallet, session key, event type, event status, policy version,
and proof hash.

**Query parameters**

| Parameter        | Description                                  |
| ---------------- | -------------------------------------------- |
| `order_id`       | Filter to a single order                     |
| `session_key`    | Filter by session key                        |
| `wallet`         | Filter by wallet                             |
| `event_type`     | e.g. `intent_evaluation`, `order_submission` |
| `event_status`   | e.g. `ALLOW`, `DENY`, `SUBMITTED`, `SETTLED` |
| `policy_version` | Filter by decision policy version            |
| `proof_hash`     | Filter by proof hash                         |
| `limit`          | Max rows (default 100, max 1000)             |

**Response 200**

```json
{ "logs": [ { "order_id": "order_...", "event_type": "intent_evaluation", "event_status": "ALLOW", "policy_version": "...", "proof_hash": "...", "...": "..." } ] }
```

---

## Demo Mode vs Enforcement Mode

The HTTP surface is identical in both modes; only the *consequences* of a
`DENY` change:

- **Demo mode (default in the MVP).** Decisions are produced and logged but
  do not block downstream Yellow submission or settlement. Used for
  integration, demos, and conformance.
- **Enforcement mode.** A `DENY` from `/v1/intent/evaluate` blocks Yellow
  submission, and a `DENY` from `/v1/settlement/validate` flags a matched
  trade as non-final.

The decision shape, proof format, and audit schema are identical between
the two modes, so promoting a deployment is a configuration change and not
a redesign.

---

## Error Handling

All error responses follow FastAPI's convention:

```json
{ "detail": "Error description" }
```

Common status codes: `200`, `403`, `404`, `422`, `500`.

---

## Versioning

API endpoints are mounted under `/v1/...`. Backwards-incompatible changes
will be introduced under a new version prefix.

---

## Support

- Issues: <https://github.com/Compliledger/CompliFlow/issues>
- Documentation: <https://github.com/Compliledger/CompliFlow/tree/main/docs>
