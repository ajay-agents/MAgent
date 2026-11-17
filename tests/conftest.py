import os
import tempfile

import pytest

# Configure before the app is imported. Real env vars take precedence over .env,
# so blanking the keys guarantees tests never call a real AI provider.
_db_dir = tempfile.mkdtemp()
os.environ.update({
    "ENVIRONMENT": "development",
    "DATABASE_URL": f"sqlite:///{_db_dir}/test.db",
    "OPENAI_API_KEY": "",
    "GEMINI_API_KEY": "",
    "GROQ_API_KEY": "",
    "AI_MOCK_FALLBACK": "true",
    "FERNET_KEY": "TCrC4ia8OmMdaOqI8B4-jsWcTQ_gmdf2artbFy5025g=",
    "JWT_SECRET": "test-secret-test-secret-test-secret",
    "LOG_LEVEL": "WARNING",
})

from fastapi.testclient import TestClient  # noqa: E402

from app.api.routes import auth as auth_routes, emails as email_routes  # noqa: E402
from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_state():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    auth_routes.auth_limiter.reset()
    email_routes.generate_limiter.reset()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sent(monkeypatch):
    """Capture outgoing emails instead of talking to Gmail."""
    outbox = []
    monkeypatch.setattr("app.core.delivery.send_email", lambda **kw: outbox.append(kw))
    monkeypatch.setattr("app.api.routes.mailbox.verify_login", lambda *a: None)
    return outbox


def signup_and_login(client, email="user@example.com", password="correct-horse-1"):
    r = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


GENERATE_PAYLOAD = {
    "purpose": "cold_outreach",
    "tone": "friendly",
    "length": "short",
    "sender_name": "Ajay",
    "recipient_name": "Priya",
    "recipient_email": "priya@example.com",
    "context": "Priya leads the data team at a fintech startup",
}


def set_plan(email: str, plan: str) -> None:
    from app.db.session import SessionLocal
    from app.models.models import User
    db = SessionLocal()
    db.query(User).filter(User.email == email).one().plan = plan
    db.commit()
    db.close()
