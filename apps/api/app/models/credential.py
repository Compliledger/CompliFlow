from pydantic import BaseModel
from typing import List


class CredentialIssueRequest(BaseModel):
    wallet: str
    session_key: str
    jurisdiction: str
    assets: List[str]
    max_notional: float


class CredentialVerifyRequest(BaseModel):
    credential: dict


class CredentialSpendRequest(BaseModel):
    credential_hash: str
    notional: float
    intent_hash: str
