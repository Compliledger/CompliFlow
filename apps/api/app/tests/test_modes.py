"""Tests for the demo-mode vs enforcement-mode behavior of the API.

CompliFlow exposes two effective operating modes via its Yellow integration:

* **Enforcement mode** — the Yellow Network is reachable. The session
  preflight surfaces real Yellow data (``allowance_remaining``,
  ``expires_at``) and reports ``yellow_status == "available"``.

* **Demo / fallback mode** — the Yellow Network is unreachable. CompliFlow
  still validates the session locally so the rest of the lifecycle (intent
  evaluation, proof generation, audit logging) keeps working, but
  ``yellow_status`` is reported as ``"unavailable"`` and external Yellow
  fields are nulled out.

These tests pin both branches so future refactors don't silently break
the offline demo path.
"""

from __future__ import annotations


def test_enforcement_mode_surfaces_yellow_metadata(client, test_session, fake_yellow):
    response = client.post(
        "/v1/yellow/session/preflight",
        json={
            "session_key": test_session["session_key"],
            "wallet": test_session["wallet"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["yellow_status"] == "available"
    # When Yellow is reachable, expires_at + allowance_remaining come from it.
    assert body["expires_at"] is not None
    assert body["allowance_remaining"] is not None


def test_demo_mode_still_validates_session_locally(
    client, test_session, fake_yellow_unavailable
):
    response = client.post(
        "/v1/yellow/session/preflight",
        json={
            "session_key": test_session["session_key"],
            "wallet": test_session["wallet"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    # Local DB-backed session is valid even when Yellow is offline...
    assert body["valid"] is True
    # ...but the route is honest about Yellow being unreachable.
    assert body["yellow_status"] == "unavailable"
    assert body["expires_at"] is None
    assert body["allowance_remaining"] is None


def test_demo_mode_order_submit_fails_cleanly_without_yellow(
    client, test_intent, make_proof_bundle, fake_yellow_unavailable
):
    """Even in demo mode, a valid proof must not bypass an unreachable venue.

    The route surfaces a 500 with a structured error rather than silently
    pretending the order was placed.
    """
    bundle = make_proof_bundle(test_intent)
    response = client.post(
        "/v1/yellow/order/submit",
        json={"intent": test_intent, "receipt": {"proof_bundle": bundle}},
    )
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["error"] == "yellow_network_unavailable"


def test_intent_evaluation_works_in_both_modes(
    client, test_intent, fake_yellow_unavailable
):
    """Intent evaluation is purely local — Yellow availability must not gate it."""
    response = client.post("/v1/intent/evaluate", json=test_intent)
    assert response.status_code == 200
    body = response.json()
    assert body["payload"]["decision"]["decision"] in (
        "ALLOW",
        "ALLOW_WITH_CONDITIONS",
    )
    # Proof bundle is always issued, even in demo mode.
    assert "proof_bundle" in body
