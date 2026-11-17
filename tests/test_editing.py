import pytest

from app.core import openai_client
from tests.conftest import GENERATE_PAYLOAD, signup_and_login


def _draft(client, headers):
    r = client.post("/api/emails/generate", json=GENERATE_PAYLOAD, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture
def prompts(monkeypatch):
    """Capture the user prompt sent to the AI and return a canned result."""
    seen = []

    def fake_provider(prompt, user_prompt):
        seen.append(user_prompt)
        return {"subject": f"Subject v{len(seen)}", "body": f"Body v{len(seen)}", "ai_model": "fake",
                "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "estimated_cost_usd": 0.001}

    monkeypatch.setattr(openai_client.settings, "groq_api_key", "fake-key")
    monkeypatch.setattr(openai_client, "_generate_with_groq", fake_provider)
    return seen


# ── Sender profile ────────────────────────────────────────────────────────────

def test_profile_defaults_to_empty(client):
    headers = signup_and_login(client)
    r = client.get("/api/profile", headers=headers)
    assert r.status_code == 200
    assert r.json()["full_name"] is None


def test_profile_save_and_blank_fields_cleared(client):
    headers = signup_and_login(client)
    r = client.put("/api/profile", json={"full_name": "  Ajay Rajput ", "company": "Arivihan", "role": "  "},
                   headers=headers)
    assert r.status_code == 200
    assert r.json()["full_name"] == "Ajay Rajput"
    assert r.json()["role"] is None
    r = client.put("/api/profile", json={"full_name": "Ajay"}, headers=headers)
    assert client.get("/api/profile", headers=headers).json()["company"] is None  # PUT replaces


def test_profile_is_included_in_prompt(client, prompts):
    headers = signup_and_login(client)
    client.put("/api/profile", json={"company": "Arivihan", "about": "AI tutoring for students",
                                     "signature": "Ajay Rajput\nFounder, Arivihan"}, headers=headers)
    _draft(client, headers)
    assert "Sender company: Arivihan" in prompts[0]
    assert "AI tutoring for students" in prompts[0]
    assert "Founder, Arivihan" in prompts[0]


# ── Manual edits ──────────────────────────────────────────────────────────────

def test_edit_draft(client):
    headers = signup_and_login(client)
    email_id = _draft(client, headers)
    r = client.patch(f"/api/emails/{email_id}", json={"subject": "My subject", "body": "My body"}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["subject"] == "My subject"
    assert r.json()["edited_at"].endswith("Z")
    assert client.get(f"/api/emails/{email_id}", headers=headers).json()["body"] == "My body"


def test_edit_rejects_empty_subject(client):
    headers = signup_and_login(client)
    email_id = _draft(client, headers)
    assert client.patch(f"/api/emails/{email_id}", json={"subject": ""}, headers=headers).status_code == 422


def test_cannot_edit_sent_email(client, sent):
    headers = signup_and_login(client)
    client.post("/api/mailbox", json={"gmail_address": "me@gmail.com", "app_password": "abcdefghijklmnop"},
                headers=headers)
    email_id = _draft(client, headers)
    client.post(f"/api/emails/{email_id}/send", headers=headers)
    r = client.patch(f"/api/emails/{email_id}", json={"body": "changed"}, headers=headers)
    assert r.status_code == 400


def test_cannot_edit_someone_elses_email(client):
    a = signup_and_login(client, email="a@example.com")
    b = signup_and_login(client, email="b@example.com")
    email_id = _draft(client, a)
    assert client.patch(f"/api/emails/{email_id}", json={"body": "x"}, headers=b).status_code == 404


# ── Regenerate / refine ───────────────────────────────────────────────────────

def test_regenerate_fresh_updates_same_draft_and_accumulates_cost(client, prompts):
    headers = signup_and_login(client)
    email_id = _draft(client, headers)
    r = client.post(f"/api/emails/{email_id}/regenerate", json={}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == email_id and body["subject"] == "Subject v2"
    assert body["total_tokens"] == 30
    assert body["estimated_cost_usd"] == pytest.approx(0.002)
    assert "current draft" not in prompts[1]  # fresh take, not a revision
    assert len(client.get("/api/emails", headers=headers).json()) == 1  # no extra drafts


def test_refine_sends_current_draft_including_manual_edits(client, prompts):
    headers = signup_and_login(client)
    email_id = _draft(client, headers)
    client.patch(f"/api/emails/{email_id}", json={"body": "Hand-written line about our pilot"}, headers=headers)
    r = client.post(f"/api/emails/{email_id}/regenerate",
                    json={"refinement": "shorter", "instruction": "Mention the Tuesday demo"}, headers=headers)
    assert r.status_code == 200, r.text
    assert "Hand-written line about our pilot" in prompts[1]
    assert openai_client.REFINEMENT_INSTRUCTIONS["shorter"] in prompts[1]
    assert "Mention the Tuesday demo" in prompts[1]


def test_refine_rejects_unknown_refinement(client):
    headers = signup_and_login(client)
    email_id = _draft(client, headers)
    r = client.post(f"/api/emails/{email_id}/regenerate", json={"refinement": "funnier"}, headers=headers)
    assert r.status_code == 422


def test_regenerate_503_when_ai_down(client, monkeypatch):
    headers = signup_and_login(client)
    email_id = _draft(client, headers)
    monkeypatch.setattr(openai_client.settings, "ai_mock_fallback", False)
    r = client.post(f"/api/emails/{email_id}/regenerate", json={"refinement": "warmer"}, headers=headers)
    assert r.status_code == 503
    assert client.get(f"/api/emails/{email_id}", headers=headers).json()["ai_model"] == "mock-test"  # unchanged
