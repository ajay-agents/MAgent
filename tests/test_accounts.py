import re
from urllib.parse import parse_qs, urlparse

import pytest

from tests.conftest import GENERATE_PAYLOAD, signup_and_login


@pytest.fixture
def mails(monkeypatch):
    outbox = []
    monkeypatch.setattr("app.api.routes.auth.send_system_email", lambda to, subject, body: outbox.append(
        {"to": to, "subject": subject, "body": body}))
    return outbox


def _token(mail):
    url = re.search(r"https?://\S+", mail["body"]).group(0)
    return parse_qs(urlparse(url).query)["token"][0]


# ── Verification ──────────────────────────────────────────────────────────────

def test_signup_sends_verification_and_gates_ai(client, mails):
    headers = signup_and_login(client, verified=False)
    assert mails[0]["to"] == "user@example.com" and "/verify-email?token=" in mails[0]["body"]
    assert client.get("/api/auth/me", headers=headers).json()["email_verified"] is False
    r = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers)
    assert r.status_code == 403 and "verify your email" in r.json()["detail"]

    assert client.post("/api/auth/verify-email", json={"token": _token(mails[0])}).status_code == 200
    assert client.get("/api/auth/me", headers=headers).json()["email_verified"] is True
    assert client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers).status_code == 201


def test_unverified_can_still_browse_and_set_up(client, mails):
    headers = signup_and_login(client, verified=False)
    assert client.get("/api/emails", headers=headers).status_code == 200
    assert client.put("/api/profile", json={"full_name": "A"}, headers=headers).status_code == 200


def test_resend_verification(client, mails):
    headers = signup_and_login(client, verified=False)
    assert client.post("/api/auth/resend-verification", headers=headers).status_code == 202
    assert len(mails) == 2


def test_bad_verification_token(client, mails):
    signup_and_login(client, verified=False)
    assert client.post("/api/auth/verify-email", json={"token": "x" * 40}).status_code == 400


def test_reset_token_cannot_verify(client, mails):
    signup_and_login(client, verified=False)
    client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    reset_token = _token(mails[-1])
    assert client.post("/api/auth/verify-email", json={"token": reset_token}).status_code == 400


# ── Password reset ────────────────────────────────────────────────────────────

def test_forgot_password_does_not_reveal_accounts(client, mails):
    r1 = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    signup_and_login(client)
    mails.clear()
    r2 = client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    assert r1.status_code == r2.status_code == 202 and r1.json() == r2.json()
    assert len(mails) == 1


def test_reset_password_flow_and_single_use(client, mails):
    signup_and_login(client)
    client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    token = _token(mails[-1])
    r = client.post("/api/auth/reset-password", json={"token": token, "password": "brand-new-pass-9"})
    assert r.status_code == 200 and r.json()["access_token"]
    assert client.post("/api/auth/login", json={"email": "user@example.com", "password": "brand-new-pass-9"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "user@example.com", "password": "correct-horse-1"}).status_code == 401
    again = client.post("/api/auth/reset-password", json={"token": token, "password": "another-pass-77"})
    assert again.status_code == 400  # link already used


def test_reset_password_validates_length(client, mails):
    signup_and_login(client)
    client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    r = client.post("/api/auth/reset-password", json={"token": _token(mails[-1]), "password": "short"})
    assert r.status_code == 422


def test_login_token_is_not_a_reset_token(client, mails):
    headers = signup_and_login(client)
    token = headers["Authorization"].split()[1]
    assert client.post("/api/auth/reset-password", json={"token": token, "password": "brand-new-pass-9"}).status_code == 400


# ── Change password ───────────────────────────────────────────────────────────

def test_change_password(client):
    headers = signup_and_login(client)
    bad = client.post("/api/auth/change-password", json={"current_password": "wrong", "new_password": "brand-new-pass-9"},
                      headers=headers)
    assert bad.status_code == 400
    ok = client.post("/api/auth/change-password",
                     json={"current_password": "correct-horse-1", "new_password": "brand-new-pass-9"}, headers=headers)
    assert ok.status_code == 204
    assert client.post("/api/auth/login", json={"email": "user@example.com", "password": "brand-new-pass-9"}).status_code == 200


def test_dev_mode_logs_links_when_mail_not_configured(caplog):
    from app.core.system_mail import send_system_email
    send_system_email("a@example.com", "Hi", "Click https://example.com/x")
    assert "https://example.com/x" in caplog.text
