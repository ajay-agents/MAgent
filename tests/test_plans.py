import pytest

from app.core import campaigns, openai_client, plans
from app.db.session import SessionLocal
from app.models.models import UsageCounter
from tests.conftest import GENERATE_PAYLOAD, set_plan, signup_and_login

CAMPAIGN = {"name": "C", "purpose": "cold_outreach", "tone": "friendly", "length": "short", "sender_name": "Ajay"}


@pytest.fixture
def small_free_plan(monkeypatch):
    """Shrink the Free plan so tests don't need 50 generations."""
    monkeypatch.setitem(plans.PLANS, "free", plans.Plan("free", "Free", "Free", ai_emails_per_month=3,
                                                         campaign_recipients=2, followups=False))


def _set_used(user_email, n):
    from app.models.models import User
    db = SessionLocal()
    uid = db.query(User).filter_by(email=user_email).one().id
    plans._ensure_counter(db, uid, plans.current_period())
    db.query(UsageCounter).filter_by(user_id=uid, period=plans.current_period()).one().ai_emails = n
    db.commit()
    db.close()


def test_billing_overview(client):
    headers = signup_and_login(client)
    client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers)
    b = client.get("/api/billing", headers=headers).json()
    assert b["plan"]["id"] == "free"
    assert b["usage"]["ai_emails"] == 1
    assert b["usage"]["resets_at"].endswith("Z")
    assert [p["id"] for p in b["plans"]] == ["free", "pro"]
    assert b["checkout_available"] is False


def test_free_quota_blocks_generation_with_402(client, small_free_plan):
    headers = signup_and_login(client)
    for _ in range(3):
        assert client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers).status_code == 201
    r = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers)
    assert r.status_code == 402
    assert "Upgrade to Pro" in r.json()["detail"]


def test_rewrites_count_and_are_blocked_too(client, small_free_plan):
    headers = signup_and_login(client)
    email_id = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers).json()["id"]
    assert client.post(f"/api/emails/{email_id}/regenerate", json={"refinement": "shorter"}, headers=headers).status_code == 200
    assert client.post(f"/api/emails/{email_id}/regenerate", json={}, headers=headers).status_code == 200
    assert client.post(f"/api/emails/{email_id}/regenerate", json={}, headers=headers).status_code == 402


def test_failed_ai_call_is_refunded(client, monkeypatch):
    monkeypatch.setattr(openai_client.settings, "ai_mock_fallback", False)
    headers = signup_and_login(client)
    assert client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers).status_code == 503
    assert client.get("/api/billing", headers=headers).json()["usage"]["ai_emails"] == 0


def test_upgrading_lifts_the_limit(client, small_free_plan):
    headers = signup_and_login(client)
    _set_used("user@example.com", 3)
    assert client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers).status_code == 402
    set_plan("user@example.com", "pro")
    assert client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers).status_code == 201


def test_usage_is_per_month(client, small_free_plan):
    headers = signup_and_login(client)
    _set_used("user@example.com", 3)
    db = SessionLocal()
    db.query(UsageCounter).update({"period": "2000-01"})  # last month's usage
    db.commit()
    db.close()
    assert client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers).status_code == 201


# ── Campaign limits ───────────────────────────────────────────────────────────

def test_free_campaign_recipient_cap(client, small_free_plan):
    headers = signup_and_login(client)
    cid = client.post("/api/campaigns", json=CAMPAIGN, headers=headers).json()["id"]
    r = client.post(f"/api/campaigns/{cid}/recipients/csv",
                    json={"csv": "email\na@x.com\nb@x.com\nc@x.com\n"}, headers=headers).json()
    assert r["added"] == 2
    assert "Upgrade to Pro" in r["skipped"][-1]["reason"]


def test_campaign_generation_checks_remaining_quota_upfront(client, small_free_plan):
    headers = signup_and_login(client)
    _set_used("user@example.com", 2)
    cid = client.post("/api/campaigns", json=CAMPAIGN, headers=headers).json()["id"]
    client.post(f"/api/campaigns/{cid}/recipients/csv", json={"csv": "email\na@x.com\nb@x.com\n"}, headers=headers)
    r = client.post(f"/api/campaigns/{cid}/generate", headers=headers)
    assert r.status_code == 402
    assert "needs 2 AI emails but you have 1 left" in r.json()["detail"]


def test_worker_parks_recipients_when_quota_runs_out(client, small_free_plan):
    headers = signup_and_login(client)
    cid = client.post("/api/campaigns", json=CAMPAIGN, headers=headers).json()["id"]
    client.post(f"/api/campaigns/{cid}/recipients/csv", json={"csv": "email\na@x.com\nb@x.com\n"}, headers=headers)
    client.post(f"/api/campaigns/{cid}/generate", headers=headers)
    _set_used("user@example.com", 2)  # quota used elsewhere after queueing
    campaigns.run_worker_tick()
    recips = client.get(f"/api/campaigns/{cid}/recipients", headers=headers).json()
    assert [r["status"] for r in recips] == ["ready", "error"]
    assert "AI emails" in recips[1]["error_message"]


def test_followups_are_pro_only(client, sent, small_free_plan):
    headers = signup_and_login(client)
    client.post("/api/mailbox", json={"gmail_address": "me@gmail.com", "app_password": "abcdefghijklmnop"},
                headers=headers)
    cid = client.post("/api/campaigns", json=CAMPAIGN, headers=headers).json()["id"]
    client.post(f"/api/campaigns/{cid}/recipients/csv", json={"csv": "email\na@x.com\n"}, headers=headers)
    client.post(f"/api/campaigns/{cid}/generate", headers=headers)
    campaigns.run_worker_tick()
    r = client.post(f"/api/campaigns/{cid}/launch", json={"followup_count": 1}, headers=headers)
    assert r.status_code == 402
    assert client.post(f"/api/campaigns/{cid}/launch", json={"followup_count": 0}, headers=headers).status_code == 200


# ── Admin CLI ─────────────────────────────────────────────────────────────────

def test_cli_set_plan(client, capsys):
    from app import cli
    signup_and_login(client)
    cli.set_plan("USER@example.com", "pro")
    assert "free -> pro" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.set_plan("nobody@example.com", "pro")
