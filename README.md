# MailFlow AI

An AI-powered scheduled email outreach agent. Generate personalized emails with OpenAI and schedule them to send automatically via Gmail SMTP.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Database | SQLite + SQLAlchemy |
| Auth | JWT (python-jose) |
| AI | OpenAI GPT-4o-mini |
| Email sending | Gmail SMTP (Week 2) |
| Scheduling | APScheduler (Week 2) |
| Frontend | React + Vite + Tailwind (Week 3) |

## Project Structure

```
MAgent/
├── app/
│   ├── main.py              # FastAPI app, middleware, router registration
│   ├── config.py            # Settings loaded from .env
│   ├── db/
│   │   └── session.py       # SQLAlchemy engine, session, Base
│   ├── models/
│   │   └── models.py        # User, ScheduledEmail, MailboxCredential
│   ├── schemas/
│   │   └── schemas.py       # Pydantic request/response models
│   ├── api/routes/
│   │   ├── auth.py          # /api/auth/signup, /login, /me
│   │   └── emails.py        # /api/emails/generate
│   └── core/
│       ├── security.py      # Password hashing, JWT, auth dependency
│       └── openai_client.py # Prompt templates + OpenAI call for 6 purposes
├── venv/                    # Virtual environment (not committed)
├── mailflow.db              # SQLite database (auto-created on first run)
├── requirements.txt
├── .env                     # Your secrets (not committed)
├── .env.example             # Template for .env
└── start.bat                # Windows launch shortcut
```

## Setup

### 1. Create and activate the virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```
OPENAI_API_KEY=sk-your-openai-key-here
JWT_SECRET=change-this-to-a-random-secret
```

### 4. Run the server

```powershell
.\start.bat
```

Or directly:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Server runs at `http://127.0.0.1:8000`  
Swagger UI at `http://127.0.0.1:8000/docs`

## API Endpoints

### Auth

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/signup` | Register a new user |
| POST | `/api/auth/login` | Login, returns JWT token |
| GET | `/api/auth/me` | Get current user (requires token) |

### Emails

| Method | Path | Description |
|---|---|---|
| POST | `/api/emails/generate` | Generate an email with AI |

#### Generate request body

```json
{
  "purpose": "cold_outreach",
  "tone": "professional",
  "length": "medium",
  "sender_name": "Alice",
  "recipient_name": "Bob",
  "recipient_email": "bob@example.com",
  "context": "We both attended the DevConf 2025 panel on AI tooling"
}
```

**purpose** — `cold_outreach` | `follow_up` | `job_application` | `networking` | `partnership` | `thank_you`  
**tone** — `professional` | `friendly` | `formal` | `casual` | `persuasive`  
**length** — `short` | `medium` | `long`

## Development Phases

| Week | Deliverable | Status |
|---|---|---|
| Week 1 | FastAPI + Auth + AI email generation | ✅ Complete |
| Week 2 | Gmail SMTP sending + APScheduler | 🔜 Next |
| Week 3 | React + Vite frontend | 🔜 |
| Week 4 | Deploy + first real users | 🔜 |
