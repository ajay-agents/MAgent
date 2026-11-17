import base64
import email
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.core import google_oauth
from tests.conftest import GENERATE_PAYLOAD, signup_and_login


@pytest.fixture
def google_enabled(monkeypatch):
    monkeypatch.setattr(google_oauth.settings, "google_client_id", "client-id")
    monkeypatch.setattr(google_oauth.settings, "google_client_secret", "client-secret")
    google_oauth._token_cache.clear()


@pytest.fixture
def exchange(monkeypatch):
    """Fake the code exchange; tests can tweak the returned grant."""
    grant = {"email": "me@gmail.com", "refresh_token": "refresh-1", "access_token": "access-1",
             "expires_in": 3600, "scopes": ["openid", "email", google_oauth.GMAIL_SEND_SCOPE]}
    monkeypatch.setattr(google_oauth, "exchange_code", lambda code: dict(grant))
    return grant


class FakeGoogle:
    """Stands in for httpx.post against Google's token, send and revoke endpoints."""

    def __init__(self):
        self.refresh_response = (200, {"access_token": "access-fresh", "expires_in": 3600})
        self.send_statuses = [200]
        self.sent, self.revoked, self.send_tokens = [], [], []

    def post(self, url, data=None, json=None, headers=None, timeout=None):
        req = httpx.Request("POST", url)
        if url == google_oauth.TOKEN_URL:
            status, body = self.refresh_response
            return httpx.Response(status, json=body, request=req)
        if url == google_oauth.REVOKE_URL:
            self.revoked.append(data["token"])
            return httpx.Response(200, request=req)
        if url == google_oauth.SEND_URL:
            self.send_tokens.append(headers["Authorization"])
            status = self.send_statuses.pop(0) if self.send_statuses else 200
            if status == 200:
                self.sent.append(email.message_from_bytes(base64.urlsafe_b64decode(json["raw"])))
            return httpx.Response(status, json={}, request=req)
        raise AssertionError(f"unexpected POST {url}")


@pytest.fixture
def fake_google(monkeypatch):
    fake = FakeGoogle()
    monkeypatch.setattr(google_oauth.httpx, "post", fake.post)
    return fake


def _connect(client, headers):
    url = client.get("/api/mailbox/google/authorize", headers=headers).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    return client.get("/api/mailbox/google/callback", params={"code": "abc", "state": state}, follow_redirects=False)


def _redirect_params(response):
    assert response.status_code == 302
    return parse_qs(urlparse(response.headers["location"]).query)


# ── Authorization flow ────────────────────────────────────────────────────────

def test_disabled_by_default(client):
    headers = signup_and_login(client)
    assert client.get("/api/mailbox/options").json()["google_oauth"] is False
    assert client.get("/api/mailbox/google/authorize", headers=headers).status_code == 404


def test_authorize_url(client, google_enabled):
    headers = signup_and_login(client)
    url = client.get("/api/mailbox/google/authorize", headers=headers).json()["url"]
    q = parse_qs(urlparse(url).query)
    assert url.startswith(google_oauth.AUTH_URL)
    assert q["client_id"] == ["client-id"]
    assert q["access_type"] == ["offline"]
    assert google_oauth.GMAIL_SEND_SCOPE in q["scope"][0]


def test_callback_connects_account(client, google_enabled, exchange):
    headers = signup_and_login(client)
    assert _redirect_params(_connect(client, headers))["gmail"] == ["connected"]
    cred = client.get("/api/mailbox", headers=headers).json()
    assert cred["gmail_address"] == "me@gmail.com"
    assert cred["provider"] == "google"


def test_callback_rejects_forged_state(client, google_enabled, exchange):
    signup_and_login(client)
    r = client.get("/api/mailbox/google/callback", params={"code": "abc", "state": "forged"}, follow_redirects=False)
    assert _redirect_params(r)["reason"] == ["expired"]


def test_callback_rejects_login_token_as_state(client, google_enabled, exchange):
    """A normal access token must not be accepted as OAuth state."""
    headers = signup_and_login(client)
    token = headers["Authorization"].split()[1]
    r = client.get("/api/mailbox/google/callback", params={"code": "abc", "state": token}, follow_redirects=False)
    assert _redirect_params(r)["reason"] == ["expired"]


def test_callback_user_denied(client, google_enabled):
    r = client.get("/api/mailbox/google/callback", params={"error": "access_denied"}, follow_redirects=False)
    assert _redirect_params(r) == {"gmail": ["error"], "reason": ["denied"]}


def test_callback_requires_send_permission(client, google_enabled, exchange, fake_google):
    headers = signup_and_login(client)
    exchange["scopes"] = ["openid", "email"]  # user unticked "Send email on your behalf"
    assert _redirect_params(_connect(client, headers))["reason"] == ["scope"]
    assert client.get("/api/mailbox", headers=headers).status_code == 404


# ── Sending through the Gmail API ─────────────────────────────────────────────

def _draft(client, headers):
    return client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers).json()["id"]


def test_send_via_gmail_api(client, google_enabled, exchange, fake_google):
    headers = signup_and_login(client)
    _connect(client, headers)
    email_id = _draft(client, headers)
    r = client.post(f"/api/emails/{email_id}/send", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "sent"
    msg = fake_google.sent[0]
    assert msg["To"] == "priya@example.com" and msg["From"] == "me@gmail.com"
    assert fake_google.send_tokens == ["Bearer access-1"]  # reused the token from the callback


def test_expired_access_token_is_refreshed_and_retried(client, google_enabled, exchange, fake_google):
    headers = signup_and_login(client)
    _connect(client, headers)
    fake_google.send_statuses = [401, 200]
    r = client.post(f"/api/emails/{_draft(client, headers)}/send", headers=headers)
    assert r.status_code == 200, r.text
    assert fake_google.send_tokens == ["Bearer access-1", "Bearer access-fresh"]


def test_revoked_access_asks_user_to_reconnect(client, google_enabled, exchange, fake_google):
    headers = signup_and_login(client)
    _connect(client, headers)
    google_oauth._token_cache.clear()
    fake_google.refresh_response = (400, {"error": "invalid_grant"})
    email_id = _draft(client, headers)
    r = client.post(f"/api/emails/{email_id}/send", headers=headers)
    assert r.status_code == 502
    assert "Reconnect Gmail" in r.json()["detail"]
    assert client.get(f"/api/emails/{email_id}", headers=headers).json()["status"] == "failed"


def test_disconnect_revokes_google_grant(client, google_enabled, exchange, fake_google):
    headers = signup_and_login(client)
    _connect(client, headers)
    assert client.delete("/api/mailbox", headers=headers).status_code == 204
    assert fake_google.revoked == ["refresh-1"]
    assert client.get("/api/mailbox", headers=headers).status_code == 404


def test_switching_to_app_password_revokes_google(client, google_enabled, exchange, fake_google, monkeypatch):
    monkeypatch.setattr("app.api.routes.mailbox.verify_login", lambda *a: None)
    headers = signup_and_login(client)
    _connect(client, headers)
    r = client.post("/api/mailbox", json={"gmail_address": "me@gmail.com", "app_password": "abcdefghijklmnop"},
                    headers=headers)
    assert r.json()["provider"] == "app_password"
    assert fake_google.revoked == ["refresh-1"]
