"""Settlement validation route.

Exposes ``POST /v1/settlement/validate`` — given a previously-evaluated
intent, its signed receipt, and the current execution state, return a
structured decision describing whether the matched trade is allowed to
settle. The endpoint is a *validation and evidence layer only*; it never
moves funds or interacts with any settlement venue.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.audit_service import AuditService
from app.services.settlement.settlement_engine import SettlementEngine

logger = logging.getLogger(__name__)

router = APIRouter()


class SettlementValidateRequest(BaseModel):
    order_id: str = Field(..., description="Identifier of the order being settled")
    intent: Dict[str, Any] = Field(default_factory=dict)
    receipt: Dict[str, Any] = Field(default_factory=dict)
    execution_status: str = Field(
        ...,
        description="One of SUBMITTED | MATCHED | ESCROW_LOCKED | SETTLED",
    )
    proofs: Optional[Dict[str, Any]] = Field(default_factory=dict)


@router.post("/validate")
async def validate_settlement(request: SettlementValidateRequest):
    decision = SettlementEngine.evaluate(
        order_id=request.order_id,
        intent=request.intent,
        receipt=request.receipt,
        execution_status=request.execution_status,
        proofs=request.proofs or {},
    )

    try:
        AuditService.log_settlement_validation(
            order_id=request.order_id,
            decision=decision,
            execution_status=request.execution_status,
            intent=request.intent,
        )
    except Exception as exc:  # pragma: no cover - defensive: never let audit fail the response
        logger.error("Failed to record settlement audit log: %s", exc)

    return decision
