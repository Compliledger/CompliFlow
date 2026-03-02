# CompliFlow API

FastAPI-based compliance engine API.

## Setup

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Tests

```bash
pytest -q
```

## Docker

```bash
docker build -t compliflow-api .
docker run -p 8000:8000 compliflow-api
```
