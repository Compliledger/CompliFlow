# CompliFlow Integration Tests

## Overview

Integration tests for the complete CompliFlow workflow:

**Wallet → Session → Compliance → Receipt → Order → Yellow → Audit**

## Test Coverage

### Test Suite: `test_workflow.py`

| Test | Endpoint | Validates |
|------|----------|-----------|
| `test_01_session_validation` | `POST /v1/yellow/session/preflight` | Session exists, wallet matches, allowance/expiry present |
| `test_02_compliance_engine` | `POST /v1/intent/evaluate` | Policy engine returns PASS decision |
| `test_03_receipt_signing` | `POST /v1/intent/evaluate` | Receipt contains signature, hash, and public key |
| `test_04_receipt_verification` | `POST /v1/receipt/verify` | Ed25519 signature verification succeeds |
| `test_05_order_submission` | `POST /v1/yellow/order/submit` | Order forwarded to Yellow (or graceful failure) |
| `test_06_audit_log_persistence` | `GET /v1/audit/logs` | Events persisted to database |
| `test_07_order_audit_trail` | `GET /v1/audit/logs/{order_id}` | Chronological audit trail per order |
| `test_08_session_activity_tracking` | `GET /v1/audit/session/{session_key}/activity` | Session-level activity logs |

## Running Tests

### Run all integration tests:

```bash
pytest apps/api/tests/integration -v
```

### Run specific test:

```bash
pytest apps/api/tests/integration/test_workflow.py::TestWorkflowIntegration::test_01_session_validation -v
```

### Run with output:

```bash
pytest apps/api/tests/integration -v -s
```

## Requirements

The following packages must be installed:

```bash
pip install pytest pytest-asyncio httpx
```

## Test Database

Tests use the same database configuration as the application. The test suite:

1. Creates all tables before tests (`setup_db` fixture)
2. Creates a test session with wallet `0x1111111111111111111111111111111111111111`
3. Runs all tests against this session
4. Drops all tables after tests complete

## Expected Output

```
test_01_session_validation PASSED                                    [12%]
✔ Session validation works

test_02_compliance_engine PASSED                                     [25%]
✔ Compliance engine works

test_03_receipt_signing PASSED                                       [37%]
✔ Receipt signing works

test_04_receipt_verification PASSED                                  [50%]
✔ Receipt verification works

test_05_order_submission PASSED                                      [62%]
✔ Order submission works (Yellow unavailable: yellow_network_unavailable)

test_06_audit_log_persistence PASSED                                 [75%]
✔ Audit logging works (5 events recorded)

test_07_order_audit_trail PASSED                                     [87%]
✔ Order audit trail works (Yellow unavailable, verified logs endpoint)

test_08_session_activity_tracking PASSED                            [100%]
✔ Session activity tracking works (5 events)
```

## Notes

- Tests will pass even if Yellow Network is unavailable (graceful degradation is validated)
- Each test is independent and can run in isolation
- Tests use FastAPI `TestClient` for synchronous HTTP requests
- Database state is isolated per test run
