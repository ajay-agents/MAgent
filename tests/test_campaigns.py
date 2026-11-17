from datetime import datetime, timedelta, timezone

import pytest

from app.core import campaigns, openai_client, scheduler
from app.db.session import SessionLocal
from app.models.models import ScheduledEmail, utcnow
from tests.conftest import set_plan, signup_and_login

CSV = """Email,First Name,Last Name,Company,Title,Notes
priya@example.com,Priya,Shah,FinCo,Head of Data,Launched a fraud API
rahul@example.com,Rahul,,TeachTube,,Runs a JEE YouTube channel
"""

CAMPAIGN = {"name": "Q4 outreach", "purpose": "cold_outreach", "tone": "friendly", "length": "short",
            "sender_name": "Ajay", "context": "We build an AI study assistant."}


@pytest.fixture
def user(client, sent):
    """A Pro user with Gmail connected — these tests exercise campaign mechanics, not plan limits."""
    headers = signup_and_login(client)
    set_plan("user@example.com", "pro")
    client.post("/api/mailbox", json={"gmail_address": "me@gmail.com", "app_password": "abcdefghijklmnop"},
                headers=headers)
    return headers


def _campaign(client, headers, csv=CSV):
    cid = client.post("/api/campaigns", json=CAMPAIGN, headers=headers).json()["id"]
    r = client.post(f"/api/campaigns/{cid}/recipients/csv", json={"csv": csv}, headers=headers)
    assert r.status_code == 200, r.text
    return cid


def _generated(client, headers, csv=CSV):
    cid = _campaign(client, headers, csv)
    assert client.post(f"/api/campaigns/{cid}/generate", headers=headers).status_code == 200
    campaigns.run_worker_tick()
    return cid


def _recipients(client, headers, cid):
    return client.get(f"/api/campaigns/{cid}/recipients", headers=headers).json()


def _make_all_due(cid):
    db = SessionLocal()
    for e in db.query(ScheduledEmail).filter(ScheduledEmail.campaign_id == cid, ScheduledEmail.status == "pending"):
        e.scheduled_at = utcnow() - timedelta(seconds=1)
    db.commit()
    db.close()


# ── CSV parsing ───────────────────────────────────────────────────────────────

def test_parse_csv_maps_common_headers():
    rows, skipped = campaigns.parse_csv(CSV)
    assert skipped == []
    assert rows[0] == {"email": "priya@example.com", "name": "Priya Shah", "company": "FinCo",
                       "notes": "Role: Head of Data; Launched a fraud API"}
    assert rows[1]["name"] == "Rahul"


def test_parse_csv_semicolons_bom_invalid_and_duplicates():
    text = "﻿e-mail;name\nA@Example.com;Ann\nnot-an-email;Bob\na@example.com;Ann again\n\n"
    rows, skipped = campaigns.parse_csv(text)
    assert [r["email"] for r in rows] == ["a@example.com"]
    assert [s["row"] for s in skipped] == [3, 4]


def test_parse_csv_requires_email_column():
    with pytest.raises(ValueError, match="email"):
        campaigns.parse_csv("name,company\nAnn,Acme\n")


def test_name_falls_back_to_email():
    rows, _ = campaigns.parse_csv("email\njohn.doe@example.com\n")
    assert rows[0]["name"] == "John Doe"


# ── Setup & generation ────────────────────────────────────────────────────────

def test_import_reports_skips_and_dedupes_across_uploads(client, user):
    cid = _campaign(client, user)
    r = client.post(f"/api/campaigns/{cid}/recipients/csv",
                    json={"csv": "email\npriya@example.com\nbad\nnew@example.com\n"}, headers=user)
    assert r.json()["added"] == 1
    assert len(r.json()["skipped"]) == 2
    assert client.get(f"/api/campaigns/{cid}", headers=user).json()["stats"]["recipients"] == 3


def test_generation_personalises_each_email(client, user):
    cid = _generated(client, user)
    recips = _recipients(client, user, cid)
    assert [r["status"] for r in recips] == ["ready", "ready"]
    db = SessionLocal()
    priya = db.query(ScheduledEmail).filter(ScheduledEmail.campaign_recipient_id == recips[0]["id"]).one()
    assert "AI study assistant" in priya.context and "Launched a fraud API" in priya.context
    assert priya.status == "draft" and priya.step == 0
    db.close()


def test_rate_limited_generation_stays_queued_instead_of_mocking(client, user, monkeypatch):
    monkeypatch.setattr(openai_client.settings, "groq_api_key", "configured")
    def rate_limited(*a):
        raise RuntimeError("429")
    monkeypatch.setattr(openai_client, "_generate_with_groq", rate_limited)
    cid = _generated(client, user)
    assert {r["status"] for r in _recipients(client, user, cid)} == {"queued"}


def test_campaign_emails_hidden_from_drafts_page(client, user):
    _generated(client, user)
    assert client.get("/api/emails?status=draft&include_campaigns=false", headers=user).json() == []
    assert len(client.get("/api/emails?status=draft", headers=user).json()) == 2


# ── Launch, sending & follow-ups ──────────────────────────────────────────────

def test_launch_requires_gmail(client):
    headers = signup_and_login(client)
    cid = _generated(client, headers)
    r = client.post(f"/api/campaigns/{cid}/launch", json={}, headers=headers)
    assert r.status_code == 400 and "Gmail" in r.json()["detail"]


def test_launch_staggers_sends(client, user):
    cid = _generated(client, user)
    start = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(microsecond=0)
    r = client.post(f"/api/campaigns/{cid}/launch",
                    json={"start_at": start.isoformat(), "send_interval_minutes": 5}, headers=user)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "running"
    times = [datetime.fromisoformat(rec["emails"][0]["scheduled_at"].replace("Z", "+00:00"))
             for rec in _recipients(client, user, cid)]
    assert times == [start, start + timedelta(minutes=5)]
    # CSV import is locked once running
    assert client.post(f"/api/campaigns/{cid}/recipients/csv", json={"csv": CSV}, headers=user).status_code == 400


def test_full_sequence_with_threaded_followup(client, user, sent):
    cid = _generated(client, user)
    client.post(f"/api/campaigns/{cid}/launch", json={"followup_count": 1, "followup_delay_days": 3}, headers=user)
    _make_all_due(cid)
    scheduler._check_and_send_pending_emails()
    assert len(sent) == 2
    assert {r["status"] for r in _recipients(client, user, cid)} == {"contacted"}

    campaigns.run_worker_tick()  # writes the follow-ups
    recips = _recipients(client, user, cid)
    follow = recips[0]["emails"][1]
    assert follow["step"] == 1 and follow["status"] == "pending"
    assert follow["subject"] == "Re: " + recips[0]["emails"][0]["subject"]
    due = datetime.fromisoformat(follow["scheduled_at"].replace("Z", "+00:00"))
    assert timedelta(days=2, hours=23) < due - datetime.now(timezone.utc) <= timedelta(days=3)

    _make_all_due(cid)
    scheduler._check_and_send_pending_emails()
    assert len(sent) == 4
    first_ids = {s["message_id"] for s in sent[:2]}
    assert {s["in_reply_to"] for s in sent[2:]} == first_ids  # follow-ups reply in the same thread
    assert {r["status"] for r in _recipients(client, user, cid)} == {"completed"}

    campaigns.run_worker_tick()
    assert client.get(f"/api/campaigns/{cid}", headers=user).json()["status"] == "completed"


def test_mark_replied_stops_followups(client, user, sent):
    cid = _generated(client, user)
    client.post(f"/api/campaigns/{cid}/launch", json={"followup_count": 2}, headers=user)
    _make_all_due(cid)
    scheduler._check_and_send_pending_emails()
    campaigns.run_worker_tick()
    priya = _recipients(client, user, cid)[0]
    assert len(priya["emails"]) == 2

    r = client.post(f"/api/campaigns/{cid}/recipients/{priya['id']}/replied", headers=user)
    assert r.json()["status"] == "replied"
    priya = _recipients(client, user, cid)[0]
    assert [e["step"] for e in priya["emails"]] == [0]  # pending follow-up removed
    campaigns.run_worker_tick()
    assert [e["step"] for e in _recipients(client, user, cid)[0]["emails"]] == [0]  # and none regenerated


def test_pause_holds_sends_and_resume_respaces(client, user, sent):
    cid = _generated(client, user)
    client.post(f"/api/campaigns/{cid}/launch", json={"send_interval_minutes": 10}, headers=user)
    client.post(f"/api/campaigns/{cid}/pause", headers=user)
    _make_all_due(cid)
    scheduler._check_and_send_pending_emails()
    assert sent == []

    client.post(f"/api/campaigns/{cid}/resume", headers=user)
    scheduler._check_and_send_pending_emails()
    assert len(sent) == 1  # second one re-spaced 10 minutes out, not sent in a burst


def test_failed_send_marks_recipient(client, user, monkeypatch):
    import smtplib

    def fail(**_):
        raise smtplib.SMTPRecipientsRefused({})
    monkeypatch.setattr("app.core.delivery.send_email", fail)
    cid = _generated(client, user)
    client.post(f"/api/campaigns/{cid}/launch", json={"followup_count": 1}, headers=user)
    _make_all_due(cid)
    scheduler._check_and_send_pending_emails()
    recips = _recipients(client, user, cid)
    assert {r["status"] for r in recips} == {"failed"}
    assert "rejected" in recips[0]["error_message"]


# ── Removal & access ──────────────────────────────────────────────────────────

def test_delete_campaign_keeps_sent_history(client, user, sent):
    cid = _generated(client, user)
    client.post(f"/api/campaigns/{cid}/launch", json={"followup_count": 1}, headers=user)
    _make_all_due(cid)
    scheduler._check_and_send_pending_emails()
    campaigns.run_worker_tick()
    assert client.delete(f"/api/campaigns/{cid}", headers=user).status_code == 204
    statuses = sorted(e["status"] for e in client.get("/api/emails", headers=user).json())
    assert statuses == ["sent", "sent"]  # follow-ups that hadn't gone out were removed


def test_remove_recipient(client, user):
    cid = _generated(client, user)
    rid = _recipients(client, user, cid)[0]["id"]
    assert client.delete(f"/api/campaigns/{cid}/recipients/{rid}", headers=user).status_code == 204
    assert len(_recipients(client, user, cid)) == 1
    assert len(client.get("/api/emails", headers=user).json()) == 1


def test_other_users_cannot_touch_campaign(client, user):
    cid = _campaign(client, user)
    other = signup_and_login(client, email="other@example.com")
    assert client.get(f"/api/campaigns/{cid}", headers=other).status_code == 404
    assert client.get(f"/api/campaigns/{cid}/recipients", headers=other).status_code == 404
    assert client.get("/api/campaigns", headers=other).json() == []
