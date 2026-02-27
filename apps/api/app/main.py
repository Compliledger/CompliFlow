from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.intent import router as intent_router
from app.routes.receipt import router as receipt_router

app = FastAPI(title="CompliFlow API", version="0.1.0")

app.include_router(health_router, tags=["health"])
app.include_router(intent_router, prefix="/v1/intent", tags=["intent"])
app.include_router(receipt_router, prefix="/v1/receipt", tags=["receipt"])
