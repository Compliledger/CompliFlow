import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.health import router as health_router
from app.routes.intent import router as intent_router
from app.routes.receipt import router as receipt_router
from app.routes.yellow import router as yellow_router
<<<<<<< copilot/fix-concurrent-order-processing
=======
from app.routes.audit import router as audit_router
from app.routes.session import router as session_router
from app.routes.settlement import router as settlement_router

logger = logging.getLogger(__name__)
>>>>>>> main

app = FastAPI(title="CompliFlow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["health"])
app.include_router(intent_router, prefix="/v1/intent", tags=["intent"])
app.include_router(receipt_router, prefix="/v1/receipt", tags=["receipt"])
<<<<<<< copilot/fix-concurrent-order-processing
app.include_router(yellow_router, prefix="/v1/orders", tags=["orders"])
=======
app.include_router(yellow_router, prefix="/v1/yellow", tags=["yellow"])
app.include_router(audit_router, prefix="/v1/audit", tags=["audit"])
app.include_router(session_router, prefix="/v1/session", tags=["session"])
app.include_router(settlement_router, prefix="/v1/settlement", tags=["settlement"])


@app.on_event("startup")
async def startup() -> None:
    from app.db.base import Base
    from app.db.session import engine
    import app.models.session    # noqa: F401 — registers SessionKey with Base metadata
    import app.models.audit_log  # noqa: F401 — registers AuditLog with Base metadata
    import app.db.models         # noqa: F401 — registers Intent / Receipt with Base metadata

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created / verified.")
    except Exception as exc:
        logger.error("Failed to initialise database tables: %s", exc)
>>>>>>> main
