from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.session_service import SessionService
from datetime import datetime

router = APIRouter()


class SessionCreateRequest(BaseModel):
    session_key: str
    wallet: str
    allowance: float = 1000000.0


class SessionResponse(BaseModel):
    session_key: str
    wallet: str
    allowance: float
    remaining_allowance: float
    is_active: bool
    expires_at: str


@router.post("/create")
async def create_session(request: SessionCreateRequest):
    try:
        session_info = SessionService.create_session(
            session_key=request.session_key,
            wallet=request.wallet,
            initial_allowance=request.allowance
        )
        
        return {
            "status": "success",
            "message": "Session created successfully",
            **session_info
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/validate/{session_key}/{wallet}")
async def validate_session(session_key: str, wallet: str):
    is_valid, reason = SessionService.validate_session(
        session_key=session_key,
        wallet=wallet,
        required_allowance=0
    )
    
    if not is_valid:
        return {
            "valid": False,
            "reason": reason
        }
    
    return {
        "valid": True,
        "session_key": session_key,
        "wallet": wallet
    }


@router.get("/info/{session_key}/{wallet}")
async def get_session_info(session_key: str, wallet: str):
    info = SessionService.get_session_info(session_key, wallet)
    
    if info is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse(**info)
