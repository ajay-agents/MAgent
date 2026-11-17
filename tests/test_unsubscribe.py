import email as email_lib
from datetime import timedelta
from urllib.parse import urlparse

import pytest

from app.core import campaigns, scheduler, unsubscribe
from app.db.session import SessionLocal
from app.models.models import ScheduledEmail, User, utcnow
from tests.conftest import GENERATE_PAYLOAD, set_plan, signup_and_login

CAMPAIGN = {"name": "C", "purpose": "cold_outreach", "tone": "friendly", "length": "short", "sender_name": "Ajay"}


@pytest.fixture
def user(client, sent):
    headers = signup_and_login(client)
    set_plan("user@example.com", "pro")
    client.post("/api/mailbox", json={"gmail_address": "me@gmail.com", "app_password": "abcdefghijklmnop"},
                headers=headers)
    client.put("/api/profile", json={"full_name": "Ajay", "company": "Arivihan",
                                     "postal_address": "12 MG Road, Indore 452001, India"}, headers=headers)
    return headers


def _uid():
    db = SessionLocal()
    uid = db.query(User).filter_by(email="user@example.com").one().id
    db.close()
    return uid


def _launched_campaign(client, headers, csv="email,name\npriya@example.com,Priya\nrahul@example.com,Rahul\n",
                       followups=0):
    cid = client.post("/api/campaigns", json=CAMPAIGN, headers=headers).json()["id"]
    client.post(f"/api/campaigns/{cid}/recipients/csv", json={"csv": csv}, headers=headers)
    client.post(f"/api/campaigns/{cid}/generate", headers=headers)
    campaigns.run_worker_tick()
    r = client.post(f"/api/campaigns/{cid}/launch", json={"followup_count": followups}, headers=headers)
    assert r.status_code == 200, r.text
    db = SessionLocal()
    for e in db.query(ScheduledEmail).filter(ScheduledEmail.campaign_id == cid, ScheduledEmail.status == "pending"):
        e.scheduled_at = utcnow() - timedelta(seconds=1)
    db.commit()
    db.close()
    return cid


def _path(url):
    return urlparse(url).path


# ── Footer & headers ──────────────────────────────────────────────────────────

def test_campaign_emails_carry_unsubscribe_footer_and_headers(client, user, sent):
    _launched_campaign(client, user)
    scheduler._check_and_send_pending_emails()
    msg = sent[0]
    assert "Unsubscribe: http://localhost:8000/u/" in msg["body"]
    assert "12 MG Road, Indore" in msg["body"]
    assert msg["extra_headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert msg["extra_headers"]["List-Unsubscribe"].startswith("<http://localhost:8000/u/")


def test_footer_not_stored_in_draft(client, user, sent):
    cid = _launched_campaign(client, user)
    scheduler._check_and_send_pending_emails()
    db = SessionLocal()
    stored = db.query(ScheduledEmail).filter(ScheduledEmail.campaign_id == cid).first()
    assert "Unsubscribe:" not in stored.body
    db.close()


def test_one_off_emails_have_no_footer(client, user, sent):
    email_id = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=user).json()["id"]
    client.post(f"/api/emails/{email_id}/send", headers=user)
    assert "Unsubscribe:" not in sent[0]["body"]
    assert sent[0]["extra_headers"] is None


def test_footer_headers_build_valid_mime():
    from app.core.smtp_sender import build_message
    msg = build_message("me@gmail.com", "a@b.com", "Hi", "Body",
                        extra_headers={"List-Unsubscribe": "<https://x/u/abc>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"})
    parsed = email_lib.message_from_bytes(msg.as_bytes())
    assert parsed["List-Unsubscribe"] == "<https://x/u/abc>"


# ── Public unsubscribe page ───────────────────────────────────────────────────

def test_get_only_confirms_post_unsubscribes(client, user):
    url = unsubscribe.unsubscribe_url(_uid(), "priya@example.com")
    page = client.get(_path(url))
    assert page.status_code == 200 and "Unsubscribe?" in page.text and "Ajay (Arivihan)" in page.text
    assert client.get("/api/suppressions", headers=user).json() == []  # a link scanner opening it changes nothing

    done = client.post(_path(url))
    assert "You're unsubscribed" in done.text
    assert client.get("/api/suppressions", headers=user).json()[0]["email"] == "priya@example.com"
    assert "already unsubscribed" in client.get(_path(url)).text


def test_one_click_post_from_mail_client(client, user):
    url = unsubscribe.unsubscribe_url(_uid(), "priya@example.com")
    r = client.post(_path(url), data={"List-Unsubscribe": "One-Click"})
    assert r.status_code == 200
    assert len(client.get("/api/suppressions", headers=user).json()) == 1


def test_tampered_token_rejected(client, user):
    url = unsubscribe.unsubscribe_url(_uid(), "priya@example.com")
    assert client.get(_path(url)[:-3] + "xyz").status_code == 404
    assert client.post(_path(url)[:-3] + "xyz").status_code == 404
    assert client.get("/api/suppressions", headers=user).json() == []


def test_login_token_is_not_an_unsubscribe_token(client, user):
    token = user["Authorization"].split()[1]
    assert client.post(f"/u/{token}").status_code == 404


# ── Enforcement ───────────────────────────────────────────────────────────────

def test_unsubscribe_stops_pending_campaign_emails(client, user, sent):
    cid = _launched_campaign(client, user, followups=2)
    client.post(_path(unsubscribe.unsubscribe_url(_uid(), "priya@example.com")))
    scheduler._check_and_send_pending_emails()
    assert [s["to_email"] for s in sent] == ["rahul@example.com"]
    recips = client.get(f"/api/campaigns/{cid}/recipients", headers=user).json()
    assert recips[0]["status"] == "unsubscribed" and recips[0]["emails"] == []
    assert client.get(f"/api/campaigns/{cid}", headers=user).json()["stats"]["unsubscribed"] == 1


def test_unsubscribe_after_first_email_stops_followups(client, user, sent):
    cid = _launched_campaign(client, user, followups=2)
    scheduler._check_and_send_pending_emails()
    campaigns.run_worker_tick()  # writes follow-ups
    client.post(_path(unsubscribe.unsubscribe_url(_uid(), "priya@example.com")))
    campaigns.run_worker_tick()
    priya = client.get(f"/api/campaigns/{cid}/recipients", headers=user).json()[0]
    assert priya["status"] == "unsubscribed"
    assert [e["step"] for e in priya["emails"]] == [0]


def test_send_time_check_catches_already_claimed_emails(client, user, sent):
    """Even if something slips past (e.g. queued elsewhere), the send-time check blocks it."""
    _launched_campaign(client, user)
    db = SessionLocal()
    from app.models.models import Suppression
    db.add(Suppression(user_id=_uid(), email="priya@example.com", reason="manual"))  # bypass suppress() cleanup
    db.commit()
    db.close()
    scheduler._check_and_send_pending_emails()
    assert [s["to_email"] for s in sent] == ["rahul@example.com"]


def test_csv_import_skips_suppressed(client, user):
    client.post("/api/suppressions", json={"email": "Priya@Example.com"}, headers=user)
    cid = client.post("/api/campaigns", json=CAMPAIGN, headers=user).json()["id"]
    r = client.post(f"/api/campaigns/{cid}/recipients/csv",
                    json={"csv": "email\npriya@example.com\nrahul@example.com\n"}, headers=user).json()
    assert r["added"] == 1
    assert "do-not-contact" in r["skipped"][0]["reason"]


def test_send_now_blocked_for_suppressed(client, user, sent):
    client.post("/api/suppressions", json={"email": "priya@example.com"}, headers=user)
    email_id = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=user).json()["id"]
    r = client.post(f"/api/emails/{email_id}/send", headers=user)
    assert r.status_code == 400 and "do-not-contact" in r.json()["detail"]
    assert sent == []


def test_lists_are_per_sender(client, user):
    client.post("/api/suppressions", json={"email": "priya@example.com"}, headers=user)
    other = signup_and_login(client, email="other@example.com")
    assert client.get("/api/suppressions", headers=other).json() == []


def test_remove_from_list(client, user):
    client.post("/api/suppressions", json={"email": "priya@example.com"}, headers=user)
    assert client.delete("/api/suppressions/priya@example.com", headers=user).status_code == 204
    assert client.get("/api/suppressions", headers=user).json() == []
    assert client.delete("/api/suppressions/priya@example.com", headers=user).status_code == 404


def test_links_survive_jwt_secret_rotation(client, user, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "link_signing_secret", "s" * 40)
    url = unsubscribe.unsubscribe_url(_uid(), "priya@example.com")
    monkeypatch.setattr(settings, "jwt_secret", "rotated-" + "x" * 40)
    assert "Unsubscribe?" in client.get(_path(url)).text
