from datetime import datetime, timedelta, timezone

import pytest

from app.core import scheduler
from app.core.delivery import recover_interrupted_sends
from app.db.session import SessionLocal
from app.models.models import ScheduledEmail, utcnow
from tests.conftest import GENERATE_PAYLOAD, signup_and_login


def _draft(client, headers):
    r = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _add_mailbox(client, headers):
    r = client.post("/api/mailbox", json={"gmail_address": "me@gmail.com", "app_password": "abcd efgh ijkl mnop"},
                    headers=headers)
    assert r.status_code == 201, r.text


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_signup_login_me(client):
    headers = signup_and_login(client, email="Mixed@Example.com")
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "mixed@example.com"
    assert r.json()["created_at"].endswith("Z")


def test_duplicate_signup_is_case_insensitive(client):
    signup_and_login(client, email="a@example.com")
    r = client.post("/api/auth/signup", json={"email": "A@EXAMPLE.com", "password": "another-pass-1"})
    assert r.status_code == 400


@pytest.mark.parametrize("password", ["short", "x" * 73])
def test_signup_rejects_bad_passwords(client, password):
    r = client.post("/api/auth/signup", json={"email": "b@example.com", "password": password})
    assert r.status_code == 422


def test_login_wrong_password(client):
    signup_and_login(client)
    r = client.post("/api/auth/login", json={"email": "user@example.com", "password": "wrong-password"})
    assert r.status_code == 401


def test_invalid_token_rejected(client):
    r = client.get("/api/emails", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401


def test_auth_rate_limit(client):
    codes = [client.post("/api/auth/login", json={"email": "x@example.com", "password": "whatever-1"}).status_code
             for _ in range(12)]
    assert codes[-1] == 429
    assert codes.count(401) == 10


# ── Generation ────────────────────────────────────────────────────────────────

def test_generate_uses_mock_when_no_provider(client):
    headers = signup_and_login(client)
    r = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers)
    assert r.status_code == 201
    assert r.json()["ai_model"] == "mock-test"


def test_generate_returns_503_when_providers_fail_and_mock_disabled(client, monkeypatch):
    monkeypatch.setattr("app.core.openai_client.settings.ai_mock_fallback", False)
    headers = signup_and_login(client)
    r = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers)
    assert r.status_code == 503


@pytest.mark.parametrize("field,value", [("purpose", "spam"), ("sender_name", ""), ("context", "x" * 2001)])
def test_generate_validates_input(client, field, value):
    headers = signup_and_login(client)
    r = client.post("/api/emails/generate", json={**GENERATE_PAYLOAD, field: value}, headers=headers)
    assert r.status_code == 422


def test_users_cannot_see_each_others_emails(client):
    a = signup_and_login(client, email="a@example.com")
    b = signup_and_login(client, email="b@example.com")
    email_id = _draft(client, a)
    assert client.get(f"/api/emails/{email_id}", headers=b).status_code == 404
    assert client.get("/api/emails", headers=b).json() == []


# ── Mailbox ───────────────────────────────────────────────────────────────────

def test_mailbox_rejects_wrong_length_app_password(client, sent):
    headers = signup_and_login(client)
    r = client.post("/api/mailbox", json={"gmail_address": "me@gmail.com", "app_password": "short"}, headers=headers)
    assert r.status_code == 422


def test_mailbox_rejects_credentials_gmail_refuses(client, monkeypatch):
    import smtplib

    def refuse(*_):
        raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    monkeypatch.setattr("app.api.routes.mailbox.verify_login", refuse)
    headers = signup_and_login(client)
    r = client.post("/api/mailbox", json={"gmail_address": "me@gmail.com", "app_password": "abcdefghijklmnop"},
                    headers=headers)
    assert r.status_code == 400


# ── Scheduling & sending ──────────────────────────────────────────────────────

def test_schedule_converts_timezone_to_utc(client):
    headers = signup_and_login(client)
    email_id = _draft(client, headers)
    ist = timezone(timedelta(hours=5, minutes=30))
    local = (datetime.now(ist) + timedelta(hours=2)).replace(microsecond=0)
    r = client.post(f"/api/emails/{email_id}/schedule", json={"scheduled_at": local.isoformat()}, headers=headers)
    assert r.status_code == 200, r.text
    returned = datetime.fromisoformat(r.json()["scheduled_at"].replace("Z", "+00:00"))
    assert returned == local


def test_schedule_rejects_past_time(client):
    headers = signup_and_login(client)
    email_id = _draft(client, headers)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    r = client.post(f"/api/emails/{email_id}/schedule", json={"scheduled_at": past}, headers=headers)
    assert r.status_code == 422


def test_send_now(client, sent):
    headers = signup_and_login(client)
    _add_mailbox(client, headers)
    email_id = _draft(client, headers)
    r = client.post(f"/api/emails/{email_id}/send", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "sent"
    assert len(sent) == 1 and sent[0]["app_password"] == "abcdefghijklmnop"
    # Sending again is refused
    assert client.post(f"/api/emails/{email_id}/send", headers=headers).status_code == 400


def test_send_now_without_mailbox(client):
    headers = signup_and_login(client)
    email_id = _draft(client, headers)
    r = client.post(f"/api/emails/{email_id}/send", headers=headers)
    assert r.status_code == 400


def test_send_failure_records_friendly_error(client, monkeypatch, sent):
    import smtplib

    def fail(**_):
        raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    headers = signup_and_login(client)
    _add_mailbox(client, headers)
    monkeypatch.setattr("app.core.delivery.send_email", fail)
    email_id = _draft(client, headers)
    r = client.post(f"/api/emails/{email_id}/send", headers=headers)
    assert r.status_code == 502
    assert "App Password" in r.json()["detail"]
    email = client.get(f"/api/emails/{email_id}", headers=headers).json()
    assert email["status"] == "failed" and "App Password" in email["error_message"]


def _make_due(email_id):
    db = SessionLocal()
    db.get(ScheduledEmail, email_id).scheduled_at = utcnow() - timedelta(seconds=1)
    db.commit()
    db.close()


def test_scheduler_sends_due_email_exactly_once(client, sent):
    headers = signup_and_login(client)
    _add_mailbox(client, headers)
    email_id = _draft(client, headers)
    soon = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    client.post(f"/api/emails/{email_id}/schedule", json={"scheduled_at": soon}, headers=headers)
    _make_due(email_id)

    scheduler._check_and_send_pending_emails()
    scheduler._check_and_send_pending_emails()  # second run must not resend

    assert len(sent) == 1
    assert client.get(f"/api/emails/{email_id}", headers=headers).json()["status"] == "sent"


def test_scheduler_skips_email_claimed_elsewhere(client, sent):
    headers = signup_and_login(client)
    _add_mailbox(client, headers)
    email_id = _draft(client, headers)
    soon = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    client.post(f"/api/emails/{email_id}/schedule", json={"scheduled_at": soon}, headers=headers)
    _make_due(email_id)
    db = SessionLocal()
    db.get(ScheduledEmail, email_id).status = "sending"  # e.g. "Send now" in progress
    db.commit()
    db.close()

    scheduler._check_and_send_pending_emails()
    assert sent == []


def test_interrupted_send_is_marked_failed_on_startup(client):
    headers = signup_and_login(client)
    email_id = _draft(client, headers)
    db = SessionLocal()
    db.get(ScheduledEmail, email_id).status = "sending"
    db.commit()
    db.close()

    db = SessionLocal()
    assert recover_interrupted_sends(db) == 1  # runs at startup
    db.close()
    email = client.get(f"/api/emails/{email_id}", headers=headers).json()
    assert email["status"] == "failed"
    assert "interrupted" in email["error_message"]


def test_delete_restore_permanent(client):
    headers = signup_and_login(client)
    email_id = _draft(client, headers)
    assert client.delete(f"/api/emails/{email_id}", headers=headers).json()["status"] == "deleted"
    assert client.post(f"/api/emails/{email_id}/restore", headers=headers).json()["status"] == "draft"
    assert client.delete(f"/api/emails/{email_id}/permanent", headers=headers).status_code == 204
    assert client.get(f"/api/emails/{email_id}", headers=headers).status_code == 404
