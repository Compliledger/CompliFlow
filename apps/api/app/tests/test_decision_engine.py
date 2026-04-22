"""Tests for the CompliFlow decision/policy engine.

Covers the three decision outcomes:
  * ALLOW                    — clean intent, no platform-imposed conditions
  * DENY                     — single rule violation and aggregated violations
  * ALLOW_WITH_CONDITIONS    — clean intent with active platform conditions
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.models.intent import TradeIntent
from app.services.decision import policy_engine as pe


def _make_intent(**overrides) -> TradeIntent:
    base = {
        "session_key": "sess_decision",
        "user_wallet": "0x" + "a" * 40,
        "side": "BUY",
        "amount": 10.0,
        "price": 2.0,
        "asset": "ytest.usd",
        "expires_at": int((datetime.utcnow() + timedelta(minutes=30)).timestamp()),
        "jurisdiction": "ALLOWED",
    }
    base.update(overrides)
    return TradeIntent(**base)


def test_allow_with_conditions_for_clean_intent():
    decision = pe.PolicyEngine.evaluate(_make_intent())

    assert decision["decision"] == pe.DECISION_ALLOW_WITH_CONDITIONS
    assert decision["reason_codes"] == []
    # Default rules carry both an asset allowlist and a max-notional cap, so
    # the conditions block must surface them.
    assert decision["conditions"]["max_notional"] is not None
    assert decision["conditions"]["allowed_assets"] is not None


def test_plain_allow_when_all_conditions_disabled(monkeypatch):
    monkeypatch.setattr(pe._rules, "MAX_ORDER_NOTIONAL", None, raising=True)
    monkeypatch.setattr(pe._rules, "ALLOWED_ASSETS", None, raising=True)

    intent = _make_intent(expires_at=0)  # no expires_at condition
    decision = pe.PolicyEngine.evaluate(intent)

    assert decision["decision"] == pe.DECISION_ALLOW
    assert decision["reason_codes"] == []
    assert all(v is None for v in decision["conditions"].values())


@pytest.mark.parametrize(
    "overrides,expected_code",
    [
        ({"amount": 0}, pe.REASON_AMOUNT_INVALID),
        ({"price": 0}, pe.REASON_PRICE_INVALID),
        ({"side": "HODL"}, pe.REASON_SIDE_INVALID),
        ({"jurisdiction": "BLOCKED_REGION"}, pe.REASON_JURISDICTION_BLOCKED),
        ({"asset": "doge"}, pe.REASON_ASSET_NOT_ALLOWED),
    ],
)
def test_deny_for_individual_violations(overrides, expected_code):
    decision = pe.PolicyEngine.evaluate(_make_intent(**overrides))
    assert decision["decision"] == pe.DECISION_DENY
    assert expected_code in decision["reason_codes"]


def test_deny_aggregates_multiple_violations():
    decision = pe.PolicyEngine.evaluate(
        _make_intent(amount=0, price=0, side="X", asset="doge")
    )
    assert decision["decision"] == pe.DECISION_DENY
    for code in (
        pe.REASON_AMOUNT_INVALID,
        pe.REASON_PRICE_INVALID,
        pe.REASON_SIDE_INVALID,
        pe.REASON_ASSET_NOT_ALLOWED,
    ):
        assert code in decision["reason_codes"]


def test_deny_when_session_invalid_uses_supplied_reason():
    decision = pe.PolicyEngine.evaluate(
        _make_intent(),
        session_valid=False,
        session_reason="session_expired",
    )
    assert decision["decision"] == pe.DECISION_DENY
    assert pe.REASON_SESSION_INVALID in decision["reason_codes"]
    assert decision["human_reason"] == "session_expired"


def test_deny_when_allowance_insufficient():
    decision = pe.PolicyEngine.evaluate(
        _make_intent(amount=100, price=10),  # notional 1000
        remaining_allowance=10,
    )
    assert decision["decision"] == pe.DECISION_DENY
    assert pe.REASON_ALLOWANCE_INSUFFICIENT in decision["reason_codes"]
