# CompliFlow

**CompliFlow is the programmable enforcement layer for tokenized markets.**

It sits between trading systems and execution venues and turns policy, risk, and
settlement rules into deterministic, signed decisions that can be enforced at the
moment of execution — without slowing the trade path down.

CompliFlow is built to integrate natively with the [Yellow Network](https://yellow.org)
state-channel infrastructure, but its enforcement model is venue-agnostic by design.

---

## What CompliFlow Does

CompliFlow provides five composable capabilities:

| Capability                  | Purpose                                                                                |
| --------------------------- | -------------------------------------------------------------------------------------- |
| **Execution decisioning**   | Deterministic, versioned policy evaluation of every trade intent before it is routed.  |
| **Proof generation**        | Cryptographically signed receipts and proof bundles for every decision.                |
| **Yellow execution submission** | Submission of approved intents into Yellow state channels via session-key authority. |
| **Settlement validation**   | Independent re-validation of matched trades against the original decision and proofs.  |
| **Audit logging**           | Append-only, queryable record of every decision, submission, and settlement event.    |

These capabilities can be used independently or as a single end-to-end enforcement
pipeline.

---

## Where CompliFlow Sits in the Stack

```
        ┌────────────────────────────────────────────────────┐
        │  Trading systems / agents / OMS / market-making    │
        └──────────────────────┬─────────────────────────────┘
                               │  Trade intents
                               ▼
        ┌────────────────────────────────────────────────────┐
        │                   CompliFlow                       │
        │                                                    │
        │   Decisioning → Proofs → Submission → Settlement   │
        │                       │                            │
        │                       ▼                            │
        │                 Audit logging                      │
        └──────────────────────┬─────────────────────────────┘
                               │  Approved, signed intents
                               ▼
        ┌────────────────────────────────────────────────────┐
        │  Yellow Network (state channels, escrow, matching) │
        └──────────────────────┬─────────────────────────────┘
                               │  Settlement evidence
                               ▼
        ┌────────────────────────────────────────────────────┐
        │              On-chain custody / settlement         │
        └────────────────────────────────────────────────────┘
```

CompliFlow does not custody assets and does not match trades. It enforces the
rules around execution and produces the evidence that those rules were followed.

---

## How CompliFlow Works With Yellow

Yellow Network provides off-chain state channels, session keys, and escrow-backed
clearing. CompliFlow uses Yellow as its primary execution surface:

1. **Session-key preflight** — CompliFlow validates that the session key
   submitting an intent is active, scoped to the requesting wallet, and has
   sufficient remaining allowance.
2. **Decision before submission** — every intent is policy-evaluated and
   accompanied by a signed receipt **before** it is forwarded to Yellow.
3. **Yellow submission** — approved intents are submitted to the Yellow channel
   over the project's RPC integration, carrying the receipt as evidence.
4. **Settlement validation** — when an order reaches a settled state, CompliFlow
   re-validates the result against the stored intent, proof bundle, and current
   execution status before treating the trade as final.
5. **Audit logging** — every step is logged with the policy version, proof hash,
   session key, and execution status.

This gives Yellow-based markets a deterministic, replayable enforcement record
without changing how Yellow itself clears or settles trades.

---

## Execution Lifecycle

```
   Intent  ─►  Decisioning  ─►  Proof  ─►  Yellow submission  ─►  Match
              (policy + session)   (signed)        (RPC)            (off-chain)
```

1. **Intent** — a trade intent is submitted to the CompliFlow API.
2. **Decisioning** — the policy engine produces a structured decision
   (`ALLOW` / `DENY` / `ALLOW_WITH_CONDITIONS`) tagged with reason codes and a
   policy version.
3. **Proof** — an Ed25519-signed receipt and proof bundle are generated and
   stored.
4. **Submission** — approved intents are submitted to Yellow with the receipt
   attached.
5. **Match** — Yellow performs off-chain matching inside the state channel.

If decisioning denies an intent, no submission occurs and the denial is
recorded in the audit log with full reason codes.

---

## Settlement Lifecycle

```
   Match  ─►  Execution status  ─►  Settlement validation  ─►  Settled / rejected
              (SUBMITTED → MATCHED →   (re-check intent +        (audit-logged)
               ESCROW_LOCKED → SETTLED) proof + status)
```

1. The order progresses through the execution-status states reported by Yellow.
2. CompliFlow's settlement engine independently re-evaluates the intent, the
   stored receipt, the proof bundle, and the current execution status.
3. The result is a structured settlement decision with the same shape as a
   policy decision (`ALLOW` / `DENY` / `ALLOW_WITH_CONDITIONS`).
4. The settlement decision is appended to the audit log alongside the original
   execution decision, giving a complete, signed record per `order_id`.

The settlement engine is a **validation and evidence layer only** — it never
moves funds and never mutates external state.

---

## Demo Mode vs Enforcement Mode

CompliFlow is designed to operate in two modes against the same API surface:

- **Demo mode (default in the MVP).** CompliFlow runs end-to-end against the
  Yellow sandbox. Decisions, proofs, and settlement validations are produced
  and logged, but they are advisory — Yellow submission and settlement proceed
  even when the project is being driven by scripted or synthetic flows. This
  mode is intended for integration, demos, and conformance testing.
- **Enforcement mode.** The same decisions become blocking: a `DENY` from the
  policy engine prevents Yellow submission, and a `DENY` from the settlement
  engine flags a matched trade as non-final pending remediation. The decision
  shape, proof format, and audit schema are identical between the two modes,
  so promoting from demo to enforcement is a configuration change, not a
  redesign.

---

## Current MVP Status

| Area                          | Status                                                              |
| ----------------------------- | ------------------------------------------------------------------- |
| Execution decisioning         | ✅ Deterministic policy engine with versioned, structured decisions |
| Proof generation              | ✅ Ed25519-signed receipts and proof bundles, verifiable via API    |
| Yellow execution submission   | ✅ Sandbox integration over Yellow's WebSocket RPC                  |
| Settlement validation         | ✅ Independent re-validation engine with structured decisions       |
| Audit logging                 | ✅ Append-only audit log, queryable by order, wallet, session, etc. |
| Enforcement mode              | 🟡 Wiring exists end-to-end; default deployment runs in demo mode   |
| Multi-venue execution         | 🔜 Yellow is the only supported venue today                         |

The MVP is intentionally narrow: one venue (Yellow sandbox), one signing scheme
(Ed25519), one decision shape across both lifecycles. The goal is correctness
and replayability before breadth.

---

## Repository Layout

```
compliflow/
  apps/api/        FastAPI service implementing the enforcement layer
  infra/           Docker Compose and local infrastructure
  docs/            Architecture and API documentation
```

See [`apps/api/README.md`](apps/api/README.md) for service-level details, and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) / [`docs/API.md`](docs/API.md)
for the architecture and API references.

---

## Local Development

### Requirements

- Python 3.11+
- Docker (optional, recommended for the full stack)

### Run the API directly

From `apps/api`:

```bash
pip install -e .
uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000/docs>.

### Run with Docker

From the repository root:

```bash
docker-compose -f infra/docker-compose.yml up --build
```

### Tests

From `apps/api`:

```bash
pytest -q
```

---

## CI

GitHub Actions runs Ruff linting and Pytest against `apps/api` on Python 3.11.

---

## License

MIT
