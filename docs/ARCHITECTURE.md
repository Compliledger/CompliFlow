# CompliFlow Architecture

## What CompliFlow Is

CompliFlow is the **programmable enforcement layer for tokenized markets**. It
turns trading policy, risk rules, and settlement requirements into deterministic,
signed decisions that can be enforced at the moment of execution and replayed
for audit later.

CompliFlow is not a venue, not a custodian, and not a matching engine. It is the
layer that sits between trading systems and execution venues and produces:

1. **Decisions** — versioned `ALLOW` / `DENY` / `ALLOW_WITH_CONDITIONS` results
   with structured reason codes.
2. **Proofs** — Ed25519-signed receipts and proof bundles bound to the canonical
   intent.
3. **Submissions** — approved intents forwarded into the execution venue
   (Yellow Network in the MVP) with the receipt attached.
4. **Settlement validations** — independent re-evaluation of matched trades.
5. **Audit records** — an append-only trail of every step keyed by `order_id`.

---

## Where CompliFlow Sits in the Stack

```
   Trading systems / agents / OMS
                │
                ▼
            CompliFlow
   ┌────────────────────────────────┐
   │ Decisioning  →  Proofs         │
   │ Submission   →  Settlement     │
   │              ↘  Audit log      │
   └────────────────────────────────┘
                │
                ▼
       Yellow Network (channels)
                │
                ▼
       On-chain custody / settlement
```

CompliFlow is the **decision and evidence plane**. Yellow is the **execution
plane**. On-chain custody is the **settlement plane**. CompliFlow holds no
funds and performs no on-chain transactions.

---

## How CompliFlow Works With Yellow

Yellow Network provides off-chain state channels, session keys, and escrow-backed
clearing. CompliFlow integrates with Yellow at three points:

| Stage             | CompliFlow role                                                   | Yellow role                                  |
| ----------------- | ----------------------------------------------------------------- | -------------------------------------------- |
| Pre-execution     | Session-key preflight, policy decisioning, receipt signing        | Validate session key, return capability info |
| Execution         | Submit approved intent + receipt over Yellow's WebSocket RPC      | Off-chain matching inside the state channel  |
| Post-execution    | Re-validate against intent, proof, and execution status; log it   | Report execution status, settlement events   |

The Yellow integration is implemented as a WebSocket RPC client
(`app/services/execution/yellow_websocket_client.py`) wrapped by a higher-level
client (`app/services/execution/yellow_client.py`). The MVP targets the
Yellow sandbox endpoint.

---

## Execution Lifecycle

```
   Intent ─► Decisioning ─► Proof ─► Yellow submission ─► Match
            (PolicyEngine)  (Ed25519)   (RPC)                (off-chain)
```

1. **Intent received** via `POST /v1/intent/evaluate`.
2. **Session preflight** — `SessionService` (and Yellow, when reachable)
   validates that the session key is active, scoped to the wallet, and has
   sufficient remaining allowance.
3. **Policy decision** — the `PolicyEngine` produces a versioned, structured
   decision with reason codes.
4. **Proof** — `ReceiptSigner` produces an Ed25519-signed receipt and a proof
   bundle stored via `app.services.proof.store`.
5. **Submission** — when allowed, the intent is forwarded to Yellow via
   `POST /v1/yellow/order/submit` with the receipt attached.
6. **Audit** — every step is appended to the audit log with the policy version
   and proof hash.

A `DENY` short-circuits the lifecycle: no submission, no settlement, full
audit record.

---

## Settlement Lifecycle

```
   Match ─► Execution status ─► Settlement validation ─► Settled / rejected
            (SUBMITTED → MATCHED →  (intent + proof +       (audit-logged)
             ESCROW_LOCKED → SETTLED) status re-check)
```

1. The order progresses through the execution-status states reported by Yellow.
2. `POST /v1/settlement/validate` invokes the `SettlementEngine`, which:
   - re-canonicalizes the original intent,
   - re-verifies the receipt signature against the stored public key,
   - checks the execution status against the eligible-status set, and
   - returns a structured decision with the same shape as the policy decision.
3. The settlement decision is appended to the audit log against the same
   `order_id` as the original execution decision.

The settlement engine is a **validation and evidence layer only**. It never
moves funds, and it never mutates state outside the audit log.

---

## Components

### API service (`apps/api`)

- `app/main.py` — FastAPI application; mounts the routers below.
- `app/routes/`
  - `health.py` — service health.
  - `intent.py` — execution decisioning.
  - `receipt.py` — proof verification.
  - `yellow.py` — Yellow session preflight and order submission.
  - `settlement.py` — settlement validation.
  - `session.py` — session-key lifecycle.
  - `audit.py` — audit-log queries.
- `app/services/`
  - `policy_engine.py` — deterministic decisioning.
  - `proof/` — receipt signing, canonicalization, proof storage.
  - `execution/` — Yellow WebSocket RPC client and high-level wrapper.
  - `settlement/settlement_engine.py` — settlement re-validation.
  - `session_service.py` — session-key validation and allowance accounting.
  - `audit_service.py` — append-only audit log writer.
- `app/models/` — Pydantic request/response models.
- `app/db/` — SQLAlchemy ORM models and session management.

### Infrastructure (`infra`)

- **PostgreSQL** — durable storage for intents, receipts, sessions, audit log.
- **Redis** — session/cache layer.
- **Docker Compose** — local stack.

---

## Data Model Highlights

- **Decisions** share a single shape across the policy and settlement engines:
  `decision`, `reason_codes`, `human_reason`, `conditions`, `policy_version`,
  and a context block (`intent_context` or `settlement_context`).
- **Proof bundles** include the canonicalized payload, the Ed25519 signature,
  and a content hash that is referenced by the audit log.
- **Audit log** is append-only, keyed by `order_id`, and indexed by
  `wallet`, `session_key`, `event_type`, `event_status`, `policy_version`,
  and `proof_hash`.

---

## Demo Mode vs Enforcement Mode

CompliFlow runs the same code path in both modes:

- **Demo mode (default in the MVP).** Decisions, proofs, and settlement
  validations are produced and logged, but they are advisory. Yellow
  submission and settlement proceed even when driven by scripted or synthetic
  flows. Intended for integration testing, demos, and conformance.
- **Enforcement mode.** Decisions are blocking. A `DENY` from the policy
  engine prevents Yellow submission; a `DENY` from the settlement engine
  flags a matched trade as non-final pending remediation. The decision shape,
  proof format, and audit schema are identical to demo mode.

Promoting a deployment from demo to enforcement is a configuration change,
not a redesign — the same endpoints, the same payloads, the same audit
records.

---

## Security

- Receipts are signed with **Ed25519**.
- Signing keys are loaded from environment variables; no secrets are committed
  to source control.
- The audit log is append-only and references proofs by hash, allowing
  independent replay of any decision.
- The settlement engine performs no state mutation outside the audit log.

---

## Current MVP Status

| Area                          | Status                                                              |
| ----------------------------- | ------------------------------------------------------------------- |
| Execution decisioning         | ✅ Deterministic, versioned policy engine                           |
| Proof generation              | ✅ Ed25519-signed receipts, proof bundles, verification endpoint    |
| Yellow execution submission   | ✅ Sandbox WebSocket RPC integration                                |
| Settlement validation         | ✅ Independent re-validation engine, structured decisions           |
| Audit logging                 | ✅ Append-only audit log with rich query filters                    |
| Enforcement mode              | 🟡 Wired end-to-end; default deployment runs in demo mode           |
| Multi-venue execution         | 🔜 Yellow is the only supported venue today                         |

---

## Migration Note

Earlier iterations of this project described CompliFlow as a "compliance-native
micro trading engine" composed around an execution-control layer. That framing
has been retired. CompliFlow is now positioned as a multi-capability
enforcement layer: execution decisioning, proof generation, Yellow execution
submission, settlement validation, and audit logging. The HTTP API surface is
backward-compatible — existing `POST /v1/intent/evaluate` and
`POST /v1/receipt/verify` callers continue to work unchanged.
