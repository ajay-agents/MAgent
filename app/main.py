import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text

from app.config import settings
from app.db.session import Base, engine
from app.models import models  # noqa: F401 — registers models with Base metadata
from app.api.routes import auth, billing, campaigns, emails, mailbox, profile, unsubscribe
from app.core.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("apscheduler").setLevel(logging.WARNING)  # it logs every 60s run at INFO
logger = logging.getLogger("mailflow")

VERSION = "0.3.0"


def _migrate() -> None:
    """Create tables and add columns introduced after a database was first created.

    Lightweight stand-in for Alembic — only ever adds nullable columns and indexes.
    """
    Base.metadata.create_all(bind=engine)
    added_columns = {
        "scheduled_emails": {"deleted_at": "TIMESTAMP", "error_message": "VARCHAR(500)", "edited_at": "TIMESTAMP",
                             "campaign_id": "INTEGER", "campaign_recipient_id": "INTEGER", "step": "INTEGER DEFAULT 0",
                             "message_id": "VARCHAR(255)"},
        "mailbox_credentials": {"provider": "VARCHAR(20) DEFAULT 'app_password'"},
        "users": {"plan": "VARCHAR(20) DEFAULT 'free'", "plan_updated_at": "TIMESTAMP"},
        "sender_profiles": {"postal_address": "VARCHAR(300)"},
    }
    existing = inspect(engine)
    with engine.begin() as conn:
        for table, columns in added_columns.items():
            have = {c["name"] for c in existing.get_columns(table)}
            for name, ddl_type in columns.items():
                if name not in have:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}"))
                    logger.info("Added column %s.%s", table, name)
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_scheduled_emails_status ON scheduled_emails (status)"
        ))


@asynccontextmanager
async def lifespan(app: FastAPI):
    _migrate()
    configured = [n for n, k in (("OpenAI", settings.openai_api_key), ("Gemini", settings.gemini_api_key),
                                  ("Groq", settings.groq_api_key)) if k]
    logger.info("Starting MailFlow %s (%s); AI keys present: %s; mock fallback: %s",
                VERSION, settings.environment, ", ".join(configured) or "none", settings.ai_mock_fallback)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="MailFlow AI",
    version=VERSION,
    lifespan=lifespan,
    # Interactive API docs are handy locally but needless attack surface in production
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if settings.is_production:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    # Log the details server-side; never leak internals to the client
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


app.include_router(auth.router)
app.include_router(emails.router)
app.include_router(mailbox.router)
app.include_router(profile.router)
app.include_router(campaigns.router)
app.include_router(billing.router)
app.include_router(unsubscribe.router)
app.include_router(unsubscribe.public)


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check: database unreachable")
        return JSONResponse(status_code=503, content={"status": "error", "database": "unreachable"})
    return {"status": "ok", "version": VERSION}
