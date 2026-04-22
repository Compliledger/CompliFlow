"""Unit tests for the enriched CompliFlow policy engine."""

from datetime import datetime, timedelta

import pytest

from app.models.intent import TradeIntent
from app.services.decision import policy_engine as pe


def _make_intent(**overrides) -> TradeIntent:
    base = {
        "session_key": "sess_123",
        "user_wallet": "0x1111111111111111111111111111111111111111",
        "side": "BUY",
        "amount": 10.0,
        "price": 2.0,
        "asset": "ytest.usd",
        "expires_at": int((datetime.utcnow() + timedelta(minutes=30)).timestamp()),
        "jurisdiction": "ALLOWED",
    }
    base.update(overrides)
    return TradeIntent(**base)


def _assert_shape(decision: dict) -> None:
    assert set(decision.keys()) == {
        "decision",
        "reason_codes",
        "human_reason",
        "conditions",
        "policy_version",
    }
    assert decision["decision"] in (
        pe.DECISION_ALLOW,
        pe.DECISION_DENY,
        pe.DECISION_ALLOW_WITH_CONDITIONS,
    )
    assert isinstance(decision["reason_codes"], list)
    assert isinstance(decision["human_reason"], str) and decision["human_reason"]
    assert set(decision["conditions"].keys()) == {
        "max_notional",
        "valid_until",
        "allowed_assets",
        "allowed_counterparties",
    }
    assert decision["policy_version"]


class TestPolicyEngineAllow:
    def test_valid_intent_returns_allow_with_conditions(self):
        decision = pe.PolicyEngine.evaluate(_make_intent())
        _assert_shape(decision)
        # Default rules config has a max notional and an asset allowlist, so
        # we should land in ALLOW_WITH_CONDITIONS.
        assert decision["decision"] == pe.DECISION_ALLOW_WITH_CONDITIONS
        assert decision["reason_codes"] == []
        assert decision["conditions"]["max_notional"] is not None
        assert decision["conditions"]["valid_until"] is not None
        assert "ytest.usd" in decision["conditions"]["allowed_assets"]


class TestPolicyEngineDeny:
    @pytest.mark.parametrize(
        "overrides,expected_code",
        [
            ({"amount": 0}, pe.REASON_AMOUNT_INVALID),
            ({"amount": -1}, pe.REASON_AMOUNT_INVALID),
            ({"price": 0}, pe.REASON_PRICE_INVALID),
            ({"price": -5}, pe.REASON_PRICE_INVALID),
            ({"side": "HOLD"}, pe.REASON_SIDE_INVALID),
            ({"jurisdiction": "BLOCKED_REGION"}, pe.REASON_JURISDICTION_BLOCKED),
            ({"asset": "not_listed"}, pe.REASON_ASSET_NOT_ALLOWED),
        ],
    )
    def test_single_rule_deny(self, overrides, expected_code):
        decision = pe.PolicyEngine.evaluate(_make_intent(**overrides))
        _assert_shape(decision)
        assert decision["decision"] == pe.DECISION_DENY
        assert expected_code in decision["reason_codes"]

    def test_multiple_violations_listed(self):
        decision = pe.PolicyEngine.evaluate(
            _make_intent(amount=-1, price=-1, side="X", asset="nope")
        )
        assert decision["decision"] == pe.DECISION_DENY
        for code in (
            pe.REASON_AMOUNT_INVALID,
            pe.REASON_PRICE_INVALID,
            pe.REASON_SIDE_INVALID,
            pe.REASON_ASSET_NOT_ALLOWED,
        ):
            assert code in decision["reason_codes"]

    def test_session_invalid_uses_supplied_reason(self):
        decision = pe.PolicyEngine.evaluate(
            _make_intent(),
            session_valid=False,
            session_reason="session_expired",
        )
        assert decision["decision"] == pe.DECISION_DENY
        assert decision["reason_codes"] == [pe.REASON_SESSION_INVALID]
        assert decision["human_reason"] == "session_expired"

    def test_allowance_insufficient(self):
        decision = pe.PolicyEngine.evaluate(
            _make_intent(amount=100, price=10),  # notional 1000
            remaining_allowance=10.0,
        )
        assert decision["decision"] == pe.DECISION_DENY
        assert pe.REASON_ALLOWANCE_INSUFFICIENT in decision["reason_codes"]

    def test_max_order_size_exceeded(self, monkeypatch):
        monkeypatch.setattr(pe._rules, "MAX_ORDER_NOTIONAL", 100.0, raising=True)
        decision = pe.PolicyEngine.evaluate(_make_intent(amount=100, price=10))
        assert decision["decision"] == pe.DECISION_DENY
        assert pe.REASON_ORDER_SIZE_EXCEEDED in decision["reason_codes"]


class TestPolicyEngineConfig:
    def test_disable_allowlist(self, monkeypatch):
        monkeypatch.setattr(pe._rules, "ALLOWED_ASSETS", None, raising=True)
        decision = pe.PolicyEngine.evaluate(_make_intent(asset="anything"))
        assert decision["decision"] in (
            pe.DECISION_ALLOW,
            pe.DECISION_ALLOW_WITH_CONDITIONS,
        )

    def test_disable_max_notional(self, monkeypatch):
        monkeypatch.setattr(pe._rules, "MAX_ORDER_NOTIONAL", None, raising=True)
        decision = pe.PolicyEngine.evaluate(_make_intent(amount=10**9, price=10**9))
        assert decision["decision"] in (
            pe.DECISION_ALLOW,
            pe.DECISION_ALLOW_WITH_CONDITIONS,
        )
        assert decision["conditions"]["max_notional"] is None

    def test_legacy_import_still_works(self):
        from app.services.policy_engine import PolicyEngine as Legacy
        decision = Legacy.evaluate(_make_intent())
        _assert_shape(decision)
