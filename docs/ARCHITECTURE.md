# CompliFlow Architecture

## Overview

CompliFlow is a compliance-native micro trading engine. The system is structured as a monorepo with the following components:

```
compliflow/
  apps/api/        FastAPI application
  infra/           Infrastructure (Docker Compose, PostgreSQL)
  docs/            Documentation
```

## Components

### API (`apps/api`)

- **`app/main.py`** — FastAPI application entry point
- **`app/core/`** — Configuration and logging
- **`app/routes/`** — HTTP route handlers (health, intents, receipts)
- **`app/services/`** — Business logic (PolicyEngine, ReceiptSigner, SessionKeyManager)
- **`app/models/`** — Pydantic request/response models
- **`app/db/`** — SQLAlchemy ORM models and session management

### Infrastructure

- **PostgreSQL** — Persistent storage for intents and receipts
- **Redis** — Session and cache layer

## Data Flow

1. Client sends a `POST /v1/intent/evaluate` with a `TradeIntent`
2. `PolicyEngine` validates compliance rules
3. `ReceiptSigner` signs the result
4. Signed receipt is returned to the client

## Security

- Receipts are cryptographically signed using Ed25519
- Private keys are loaded from environment variables
- No secrets are committed to source control
