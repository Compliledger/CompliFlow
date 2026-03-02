# CompliFlow

CompliFlow is a programmable execution control layer built on Yellow Network that enables high-frequency multi-asset trading with deterministic compliance enforcement and session-key governance.

It demonstrates how real-time off-chain execution can integrate escrow-backed settlement and policy-based authority control without sacrificing performance.

---

## Overview

Modern high-speed trading systems optimize for execution speed but lack programmable governance at the moment of transaction execution.

CompliFlow solves this by embedding:

- Deterministic compliance evaluation  
- Session-key authority validation  
- Signed execution receipts  
- Off-chain intent validation  
- Escrow-aware trade gating  

directly into the transaction flow.

This project is built as part of the Yellow Acceleration Program.

---

## Architecture

```
User / AI Agent
       │
       ▼
Yellow Session Key
       │
       ▼
CompliFlow API
  ├── Policy Engine
  ├── Session Key Preflight
  ├── Receipt Signer
  └── Intent Validator
       │
       ▼
Escrow + Off-chain Matching (Yellow)
       │
       ▼
On-chain Settlement
```

### Core Principles

- Off-chain execution first  
- Deterministic policy gating before match  
- Escrow-aware validation  
- Signed compliance receipts  
- Minimal on-chain footprint  

---

## Repository Structure

```
compliflow/
  apps/api/        → FastAPI backend
  infra/           → Docker & local infrastructure
  docs/            → Architecture documentation
```

---

## Backend (FastAPI)

The API provides:

### Health Check

```
GET /health
```

Returns service status.

---

### Evaluate Intent

```
POST /v1/intent/evaluate
```

Evaluates a trade intent against policy rules and returns:

- PASS / FAIL decision  
- Reason (if blocked)  
- Signed execution receipt  

---

### Verify Receipt

```
POST /v1/receipt/verify
```

Verifies signature and receipt integrity.

---

## Policy Engine (MVP Scope)

Current deterministic rules include:

- Amount validation  
- Price validation  
- Side validation (BUY/SELL)  
- Jurisdiction restrictions (configurable)  
- Session key expiry preflight (stub)  
- Allowance validation (extensible)  

This will expand as Yellow integration deepens.

---

## Yellow Integration Strategy

CompliFlow is designed to integrate with:

- Yellow State Channels  
- Session Keys  
- Escrow-backed off-chain matching  
- On-chain custody contracts  

The backend enforces:

1. Intent validation before matching  
2. Session-key preflight checks  
3. Escrow-aware gating  
4. Signed compliance receipts attached to each execution  

The goal is to stress test Yellow SDK capabilities in a real execution environment.

---

## Local Development

### Requirements

- Python 3.11+
- Docker (optional but recommended)

---

### Run Locally (without Docker)

From `apps/api`:

```
pip install -e .
uvicorn app.main:app --reload
```

Open:

```
http://127.0.0.1:8000/docs
```

---

### Run with Docker

From root:

```
docker-compose -f infra/docker-compose.yml up --build
```

---

## Running Tests

From `apps/api`:

```
pytest -q
```

---

## CI

GitHub Actions runs:

- Ruff linting  
- Pytest  
- Python 3.11 build  
- Working directory: apps/api  

---

## Roadmap

### Phase 1 (MVP)
- Policy engine  
- Signed receipts  
- Intent validation  
- CI + Docker  

### Phase 2
- Yellow session-key RPC integration  
- Allowance mirror tracking  
- Escrow state validation  
- Matching engine stub  

### Phase 3
- Full off-chain match flow  
- Settlement hooks  
- Multichain asset abstraction  
- AI-agent execution mode  

---

## Why CompliFlow?

CompliFlow demonstrates how programmable authority and deterministic compliance can coexist with high-performance off-chain clearing infrastructure.

It is not just a trading app.

It is an execution control layer.

---

## License

MIT
