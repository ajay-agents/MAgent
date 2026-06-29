from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine, Base
from app.models import models  # noqa: F401 — registers models with Base metadata
from app.api.routes import auth, emails

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MailFlow AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server (Week 3)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(emails.router)


@app.get("/health")
def health():
    return {"status": "ok"}
