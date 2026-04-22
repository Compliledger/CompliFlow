import logging
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.db.session import get_db
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/logs")
async def get_audit_logs(
    order_id: Optional[str] = Query(None),
    session_key: Optional[str] = Query(None),
    wallet: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    event_status: Optional[str] = Query(None),
    policy_version: Optional[str] = Query(None),
    proof_hash: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    try:
        with get_db() as db:
            query = db.query(AuditLog)
            if order_id:
                query = query.filter(AuditLog.order_id == order_id)
            if session_key:
                query = query.filter(AuditLog.session_key == session_key)
            if wallet:
                query = query.filter(AuditLog.wallet == wallet)
            if event_type:
                query = query.filter(AuditLog.event_type == event_type)
            if event_status:
                # Match either the legacy ``status`` column or the new
                # ``event_status`` column so callers can use either name.
                query = query.filter(
                    (AuditLog.event_status == event_status)
                    | (AuditLog.status == event_status)
                )
            if policy_version:
                query = query.filter(AuditLog.policy_version == policy_version)
            if proof_hash:
                query = query.filter(AuditLog.proof_hash == proof_hash)

            query = query.order_by(AuditLog.timestamp.desc())
            total = query.count()
            records = query.limit(limit).all()
            logs = [r.to_dict() for r in records]

        return {
            "total": total,
            "limit": limit,
            "filters": {
                "order_id": order_id,
                "session_key": session_key,
                "wallet": wallet,
                "event_type": event_type,
                "event_status": event_status,
                "policy_version": policy_version,
                "proof_hash": proof_hash,
            },
            "logs": logs,
        }
    except Exception as exc:
        logger.error("Failed to fetch audit logs: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit logs: {exc}")


@router.get("/logs/{order_id}")
async def get_order_audit_trail(order_id: str):
    try:
        with get_db() as db:
            records = (
                db.query(AuditLog)
                .filter(AuditLog.order_id == order_id)
                .order_by(AuditLog.timestamp.asc())
                .all()
            )
            logs = [r.to_dict() for r in records]

        return {
            "order_id": order_id,
            "total_events": len(logs),
            "audit_trail": logs,
        }
    except Exception as exc:
        logger.error("Failed to fetch audit trail for order_id=%s: %s", order_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit trail: {exc}")


@router.get("/session/{session_key}/activity")
async def get_session_activity(session_key: str):
    try:
        with get_db() as db:
            records = (
                db.query(AuditLog)
                .filter(AuditLog.session_key == session_key)
                .order_by(AuditLog.timestamp.asc())
                .all()
            )
            logs = [r.to_dict() for r in records]

        return {
            "session_key": session_key,
            "total_events": len(logs),
            "activity": logs,
        }
    except Exception as exc:
        logger.error("Failed to fetch session activity for session=%s: %s", session_key, exc)
        raise HTTPException(status_code=500, detail=f"Failed to fetch session activity: {exc}")
