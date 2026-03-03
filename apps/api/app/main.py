from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.health import router as health_router
from app.routes.intent import router as intent_router
from app.routes.receipt import router as receipt_router
from app.routes.yellow import router as yellow_router

app = FastAPI(title="CompliFlow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["health"])
app.include_router(intent_router, prefix="/v1/intent", tags=["intent"])
app.include_router(receipt_router, prefix="/v1/receipt", tags=["receipt"])
app.include_router(yellow_router, prefix="/v1/yellow", tags=["yellow"])
