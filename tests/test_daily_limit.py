from datetime import timedelta

import pytest

from app.config import settings
from app.core import scheduler
from app.db.session import SessionLocal
from app.models.models import ScheduledEmail, utcnow
from tests.conftest import GENERATE_PAYLOAD, signup_and_login


@pytest.fixture
def user(client, sent, monkeypatch):
    monkeypatch.setattr(settings, "daily_send_limit", 2)
    headers = signup_and_login(client)
    client.post("/api/mailbox", json={"gmail_address": "me@gmail.com", "app_password": "abcdefghijklmnop"},
                headers=headers)
    return headers


def _due_drafts(client, headers, n):
    ids = [client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers).json()["id"] for _ in range(n)]
    db = SessionLocal()
    for e in db.query(ScheduledEmail).filter(ScheduledEmail.id.in_(ids)):
        e.status, e.scheduled_at = "pending", utcnow() - timedelta(minutes=1)
    db.commit()
    db.close()
    return ids


def test_scheduler_holds_emails_over_the_daily_cap(client, user, sent):
    ids = _due_drafts(client, user, 3)
    scheduler._check_and_send_pending_emails()
    assert len(sent) == 2
    statuses = [client.get(f"/api/emails/{i}", headers=user).json()["status"] for i in ids]
    assert statuses.count("pending") == 1  # held, not failed


def test_held_email_goes_out_once_window_frees(client, user, sent):
    _due_drafts(client, user, 3)
    scheduler._check_and_send_pending_emails()
    db = SessionLocal()
    for e in db.query(ScheduledEmail).filter(ScheduledEmail.status == "sent"):
        e.sent_at = utcnow() - timedelta(hours=25)  # yesterday's sends age out of the window
    db.commit()
    db.close()
    scheduler._check_and_send_pending_emails()
    assert len(sent) == 3


def test_send_now_refused_at_cap(client, user, sent):
    for _ in range(2):
        email_id = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=user).json()["id"]
        assert client.post(f"/api/emails/{email_id}/send", headers=user).status_code == 200
    email_id = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=user).json()["id"]
    r = client.post(f"/api/emails/{email_id}/send", headers=user)
    assert r.status_code == 429 and "24 hours" in r.json()["detail"]
    assert client.get(f"/api/emails/{email_id}", headers=user).json()["status"] == "draft"


def test_failed_sends_dont_count(client, user, monkeypatch):
    import smtplib
    def fail(**_):
        raise smtplib.SMTPRecipientsRefused({})
    monkeypatch.setattr("app.core.delivery.send_email", fail)
    for _ in range(3):
        email_id = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=user).json()["id"]
        assert client.post(f"/api/emails/{email_id}/send", headers=user).status_code == 502  # not 429


def test_caps_are_per_user(client, user, sent):
    _due_drafts(client, user, 2)
    scheduler._check_and_send_pending_emails()
    other = signup_and_login(client, email="other@example.com")
    client.post("/api/mailbox", json={"gmail_address": "o@gmail.com", "app_password": "abcdefghijklmnop"}, headers=other)
    email_id = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=other).json()["id"]
    assert client.post(f"/api/emails/{email_id}/send", headers=other).status_code == 200


def test_billing_reports_daily_sends(client, user, sent):
    email_id = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=user).json()["id"]
    client.post(f"/api/emails/{email_id}/send", headers=user)
    usage = client.get("/api/billing", headers=user).json()["usage"]
    assert usage["emails_sent_24h"] == 1 and usage["daily_send_limit"] == 2
