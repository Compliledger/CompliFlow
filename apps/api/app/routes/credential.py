import threading
import time
import uuid

from fastapi import APIRouter, HTTPException

from app.core.crypto import (
    sha256_hex,
    canonical_json,
    sign_bytes,
    verify_signature,
    get_public_key_hex,
)
from app.models.credential import (
    CredentialIssueRequest,
    CredentialVerifyRequest,
    CredentialSpendRequest,
)
from app.services.policy_engine import PolicyEngine

router = APIRouter()

CREDENTIAL_EXPIRY_SECONDS = 3600

# In-memory stores for MVP
credentials_store: dict = {}
spend_log: dict = {}
_store_lock = threading.Lock()


@router.post("/issue")
async def issue_credential(req: CredentialIssueRequest):
    decision = PolicyEngine.evaluate_credential(
        jurisdiction=req.jurisdiction,
        assets=req.assets,
        max_notional=req.max_notional,
    )
    if decision["status"] == "FAIL":
        raise HTTPException(
            status_code=403,
            detail={"error": "Policy check failed", "reason": decision["reason"]},
        )

    now = int(time.time())
    credential = {
        "version": "1.0",
        "issued_at": now,
        "expires_at": now + CREDENTIAL_EXPIRY_SECONDS,
        "wallet": req.wallet,
        "session_key_hash": sha256_hex(req.session_key.encode()),
        "jurisdiction": req.jurisdiction,
        "asset_allowlist": req.assets,
        "max_notional": req.max_notional,
        "remaining_notional": req.max_notional,
        "nonce": str(uuid.uuid4()),
    }

    canonical = canonical_json(credential)
    credential_hash = sha256_hex(canonical)
    signature = sign_bytes(bytes.fromhex(credential_hash))

    credential_bundle = {
        "credential": credential,
        "credential_hash": credential_hash,
        "signature": signature,
        "public_key": get_public_key_hex(),
    }

    credentials_store[credential_hash] = credential_bundle
    return credential_bundle


@router.post("/verify")
async def verify_credential(req: CredentialVerifyRequest):
    bundle = req.credential
    signature = bundle.get("signature")
    credential_hash = bundle.get("credential_hash")
    cred_payload = bundle.get("credential")

    if not cred_payload or not credential_hash or not signature:
        return {"valid": False, "checks": {"hash_match": False, "signature_valid": False, "not_expired": False}}

    canonical = canonical_json(cred_payload)
    computed_hash = sha256_hex(canonical)
    hash_match = computed_hash == credential_hash

    sig_valid = verify_signature(bytes.fromhex(credential_hash), signature)

    now = int(time.time())
    not_expired = now < cred_payload.get("expires_at", 0)

    valid = hash_match and sig_valid and not_expired
    return {
        "valid": valid,
        "checks": {
            "hash_match": hash_match,
            "signature_valid": sig_valid,
            "not_expired": not_expired,
        },
    }


@router.post("/spend")
async def spend_credential(req: CredentialSpendRequest):
    with _store_lock:
        bundle = credentials_store.get(req.credential_hash)
        if not bundle:
            raise HTTPException(status_code=404, detail="Credential not found")

        credential = bundle["credential"]
        signature = bundle["signature"]
        credential_hash = bundle["credential_hash"]

        if not verify_signature(bytes.fromhex(credential_hash), signature):
            raise HTTPException(status_code=400, detail="Invalid credential signature")

        now = int(time.time())
        if now >= credential.get("expires_at", 0):
            raise HTTPException(status_code=400, detail="Credential expired")

        remaining = credential.get("remaining_notional", 0)
        if req.notional > remaining:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient notional: required {req.notional}, remaining {remaining}",
            )

        credential["remaining_notional"] = remaining - req.notional

        spend_log.setdefault(req.credential_hash, []).append(
            {"ts": now, "intent_hash": req.intent_hash, "notional": req.notional}
        )

        return {"ok": True, "remaining_notional": credential["remaining_notional"]}
