from typing import Any, Optional

from pydantic import BaseModel, Field


class ReceiptVerifyRequest(BaseModel):
    payload: dict
    signature: str


class ReceiptRequest(BaseModel):
    data: dict
    signature: str | None = None


class ReceiptResponse(BaseModel):
    id: int
    data: dict
    signature: str | None = None


class ProofBundle(BaseModel):
    """Proof bundle (v1.0).

    Generic container for a signed compliance attestation.  The same shape
    is used for execution-approval proofs today and will be reused for
    settlement-validation proofs in the future.
    """

    proof_version: str = "1.0"
    issued_at: int
    expires_at: int
    intent_hash: str
    decision_hash: str
    proof_hash: str
    wallet: str
    session_key_hash: str
    decision: dict
    signature: str
    public_key: str

    model_config = {"extra": "allow"}


class ProofBundleVerifyRequest(BaseModel):
    """Request body for ``POST /v1/receipt/verify``.

    Accepts either a full proof bundle (preferred) or the legacy
    ``{payload, signature}`` shape so we don't break older clients.
    """

    # New proof-bundle shape — all optional so the legacy shape can pass
    # through the same endpoint.
    proof_version: Optional[str] = None
    issued_at: Optional[int] = None
    expires_at: Optional[int] = None
    intent_hash: Optional[str] = None
    decision_hash: Optional[str] = None
    proof_hash: Optional[str] = None
    wallet: Optional[str] = None
    session_key_hash: Optional[str] = None
    decision: Optional[dict] = None
    public_key: Optional[str] = None

    # Common to both shapes.
    signature: Optional[str] = None

    # Legacy shape.
    payload: Optional[dict] = None

    model_config = {"extra": "allow"}


class ProofBundleVerifyResponse(BaseModel):
    valid: bool
    reason: Optional[str] = None
    proof_hash: Optional[str] = None
    expires_at: Optional[int] = None

