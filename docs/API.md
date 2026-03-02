# CompliFlow API Documentation

## Base URL

Development: `http://localhost:8000`

## Authentication

Currently, no authentication is required. Future versions will implement:
- API key authentication
- OAuth 2.0 for user accounts
- JWT tokens for service-to-service communication

## Endpoints

### Health Check

#### GET /health
Check if the API is running and healthy.

**Response (200):**
```json
{
  "status": "healthy"
}
```

### Intents

#### GET /intents
List all intents.

**Query Parameters:**
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Number of records to return (default: 10)

**Response (200):**
```json
[
  {
    "id": 1,
    "data": {
      "order_type": "market",
      "side": "buy",
      "quantity": 100
    }
  }
]
```

#### POST /intents
Create a new intent.

**Request Body:**
```json
{
  "data": {
    "order_type": "market",
    "side": "buy",
    "quantity": 100,
    "price": 50000
  }
}
```

**Response (200):**
```json
{
  "id": 1,
  "data": {
    "order_type": "market",
    "side": "buy",
    "quantity": 100,
    "price": 50000
  }
}
```

**Error Responses:**
- 422: Validation error

### Receipts

#### GET /receipts
List all receipts.

**Query Parameters:**
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Number of records to return (default: 10)

**Response (200):**
```json
[
  {
    "id": 1,
    "data": {
      "transaction_id": "tx123",
      "status": "confirmed"
    },
    "signature": "sig_abc123"
  }
]
```

#### POST /receipts
Create a new receipt.

**Request Body:**
```json
{
  "data": {
    "transaction_id": "tx123",
    "status": "confirmed",
    "amount": 1000
  },
  "signature": null
}
```

**Response (200):**
```json
{
  "id": 1,
  "data": {
    "transaction_id": "tx123",
    "status": "confirmed",
    "amount": 1000
  },
  "signature": "sig_abc123"
}
```

**Error Responses:**
- 422: Validation error

## Error Handling

All error responses follow this format:

```json
{
  "detail": "Error description"
}
```

Common HTTP Status Codes:
- 200: Success
- 201: Created
- 400: Bad Request
- 404: Not Found
- 422: Validation Error
- 500: Internal Server Error

## Rate Limiting

Currently not implemented. Future versions will include rate limiting to prevent abuse.

## Pagination

Use `skip` and `limit` query parameters for pagination:

```
GET /intents?skip=0&limit=10
```

## Sorting

Currently not implemented. Future versions will support sorting by various fields.

## Filtering

Currently not implemented. Future versions will support filtering by:
- Date range
- Status
- Order type
- Side (buy/sell)

## Webhooks

Not yet implemented. Will enable real-time notifications for:
- Order fills
- Receipt confirmations
- Policy violations

## Versioning

API versioning will be implemented through URL versioning:
- v1: `/api/v1/intents`
- v2: `/api/v2/intents`

## Interactive Documentation

FastAPI provides automatic interactive documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Examples

### Create Intent
```
bash
curl -X POST http://localhost:8000/intents \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "order_type": "limit",
      "side": "buy",
      "quantity": 100,
      "price": 50000
    }
  }'
```

### List Intents
```
curl http://localhost:8000/intents
```

### Health Check
```
curl http://localhost:8000/health
```

## Compliance Features

- **Policy Engine**: Validates compliance policies
- **Receipt Signing**: Cryptographic signing of receipts
- **Session Keys**: Secure session management
- **Audit Trail**: All operations stored in database

## Performance

- Response times: < 100ms (p95)
- Throughput: 1000+ requests/second
- Concurrent connections: 100+
- Data persistence: PostgreSQL with replication ready

## Support

For API support:
- GitHub Issues: https://github.com/Compliledger/CompliFlow/issues
- Documentation: https://github.com/Compliledger/CompliFlow/tree/main/docs
