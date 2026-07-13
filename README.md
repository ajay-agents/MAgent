# MailFlow AI

An AI-powered email outreach agent. Generate personalized emails with OpenAI GPT-4o-mini (or Gemini 2.0 Flash as fallback), schedule them, and send automatically via Gmail SMTP — all from a React dashboard.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.13) |
| Database | SQLite + SQLAlchemy 2.x |
| Auth | JWT (python-jose) + bcrypt |
| AI — Primary | OpenAI GPT-4o-mini |
| AI — Fallback | Google Gemini 2.0 Flash |
| Email sending | Gmail SMTP via smtplib |
| Scheduling | APScheduler (background, 60 s poll) |
| Encryption | Fernet (cryptography) for stored passwords |
| Frontend | React 19 + Vite 8 + Tailwind CSS v4 |

---

## Project Structure

```
MAgent/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, CORS, router registration
│   ├── config.py                # Settings loaded from .env (pydantic-settings)
│   ├── db/
│   │   └── session.py           # SQLAlchemy engine, session, Base
│   ├── models/
│   │   └── models.py            # User, ScheduledEmail, MailboxCredential
│   ├── schemas/
│   │   └── schemas.py           # Pydantic request/response models
│   ├── api/routes/
│   │   ├── auth.py              # /api/auth — signup, login, me
│   │   ├── emails.py            # /api/emails — generate, list, schedule, delete
│   │   └── mailbox.py           # /api/mailbox — Gmail credential CRUD
│   ├── prompts/                 # Per-purpose prompt files (.txt)
│   │   ├── cold_outreach.txt
│   │   ├── follow_up.txt
│   │   ├── job_application.txt
│   │   ├── networking.txt
│   │   ├── partnership.txt
│   │   └── thank_you.txt
│   └── core/
│       ├── security.py          # bcrypt hashing, JWT create/verify
│       ├── openai_client.py     # Prompt loading + OpenAI / Gemini generation
│       ├── encryption.py        # Fernet encrypt/decrypt for stored passwords
│       ├── smtp_sender.py       # Gmail SMTP via smtplib (port 465, SSL)
│       └── scheduler.py        # APScheduler — polls and fires pending emails
├── frontend/                    # React + Vite frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── AuthModal.jsx        # Login / Signup modal
│   │   │   ├── Dashboard.jsx        # Stats overview + quick actions
│   │   │   ├── CreateEmail.jsx      # AI email builder + schedule/send
│   │   │   ├── Drafts.jsx           # Browse and delete drafts
│   │   │   ├── ScheduledEmails.jsx  # Manage pending emails
│   │   │   ├── SentEmails.jsx       # Sent + failed history
│   │   │   └── Settings.jsx         # Gmail credentials + logout
│   │   ├── context/
│   │   │   ├── AuthContext.jsx      # JWT storage, login/logout helpers
│   │   │   └── ThemeContext.jsx     # Dark/light mode toggle
│   │   ├── components/
│   │   │   ├── ProtectedRoute.jsx   # Redirects unauthenticated users to /
│   │   │   ├── Sidebar.jsx
│   │   │   └── Navbar.jsx
│   │   └── services/
│   │       └── api.js               # Fetch wrapper with auto Bearer token
│   └── .env                         # VITE_API_BASE_URL=http://localhost:8000
├── mailflow.db                  # SQLite database (auto-created on first run)
├── requirements.txt
├── .env                         # Your secrets (not committed)
├── .env.example                 # Template for .env
└── start.bat                    # Windows launch shortcut
```

---

## Backend Setup

### 1. Create and activate virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If you get an execution policy error:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```env
OPENAI_API_KEY=sk-your-openai-key-here
GEMINI_API_KEY=your-gemini-key-here          # optional fallback
JWT_SECRET=change-this-to-a-random-secret
FERNET_KEY=your-fernet-key-here
```

**Generate a Fernet key** (run once, paste the output into `.env`):

```powershell
.\venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

| Variable | Where to get it |
|---|---|
| `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `GEMINI_API_KEY` | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) — free tier, used as fallback |
| `FERNET_KEY` | Generate with command above |
| `JWT_SECRET` | Any long random string |

### 4. Start the backend

```powershell
.\start.bat
```

Or directly:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Backend: `http://127.0.0.1:8000`  
Swagger UI: `http://127.0.0.1:8000/docs`

---

## Frontend Setup

### 1. Install dependencies

```powershell
cd frontend
npm install
```

### 2. Configure API URL

`frontend/.env` is already set to point at the local backend:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Change this if your backend runs on a different port or host.

### 3. Start the dev server

```powershell
npm run dev
```

Frontend: `http://localhost:5173`

---

## Running the Full Stack

Open two terminals:

```powershell
# Terminal 1 — backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm run dev
```

Then open `http://localhost:5173`.

---

## Frontend Pages

| Page | Route | What it does |
|---|---|---|
| Landing | `/` | Marketing page with login/signup modal |
| Dashboard | `/dashboard` | Live stats (generated / sent / scheduled / failed) |
| Create Email | `/create-email` | AI builder — generate, schedule, or send now |
| Drafts | `/drafts` | Browse drafts, view full email, delete |
| Scheduled | `/scheduled-emails` | View pending queue, cancel or reschedule |
| Sent | `/sent-emails` | History of sent and failed emails |
| Settings | `/settings` | Gmail credentials, dark mode, logout |

---

## API Reference

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/signup` | — | Register a new user |
| POST | `/api/auth/login` | — | Login, returns JWT token |
| GET | `/api/auth/me` | JWT | Get current user info |

All protected endpoints require: `Authorization: Bearer <token>`

---

### Mailbox Credentials

Gmail app passwords are Fernet-encrypted before being stored.

| Method | Path | Description |
|---|---|---|
| POST | `/api/mailbox` | Save (or replace) Gmail credentials |
| GET | `/api/mailbox` | Get current credential (password never returned) |
| DELETE | `/api/mailbox` | Remove credentials |

**How to get a Gmail App Password:**
1. Enable 2-Step Verification on your Google Account
2. Go to Google Account → Security → App Passwords
3. Create a new App Password — copy the 16-character code

```json
{
  "gmail_address": "you@gmail.com",
  "app_password": "abcd efgh ijkl mnop"
}
```

---

### Emails

| Method | Path | Description |
|---|---|---|
| POST | `/api/emails/generate` | Generate with AI — saves as draft |
| GET | `/api/emails` | List all emails (`?status=draft\|pending\|sent\|failed`) |
| GET | `/api/emails/{id}` | Full detail including email body |
| POST | `/api/emails/{id}/schedule` | Schedule a draft for a future time |
| DELETE | `/api/emails/{id}/schedule` | Cancel schedule — moves back to draft |
| DELETE | `/api/emails/{id}` | Delete a draft or failed email |

#### Generate request body

```json
{
  "purpose": "cold_outreach",
  "tone": "professional",
  "length": "medium",
  "sender_name": "Alice",
  "recipient_name": "Bob",
  "recipient_email": "bob@example.com",
  "context": "We met at DevConf 2025"
}
```

**`purpose`** — `cold_outreach` | `follow_up` | `job_application` | `networking` | `partnership` | `thank_you`  
**`tone`** — `professional` | `friendly` | `formal` | `casual` | `persuasive`  
**`length`** — `short` (< 100 words) | `medium` (150–200 words) | `long` (250–350 words)

#### Generate response

```json
{
  "id": 1,
  "subject": "Quick question about your onboarding flow",
  "body": "Hi Bob, ...",
  "ai_model": "gpt-4o-mini",
  "prompt_tokens": 412,
  "completion_tokens": 187,
  "total_tokens": 599,
  "estimated_cost_usd": 0.00018
}
```

The `id` is used for all subsequent operations.

#### Schedule request body

```json
{ "scheduled_at": "2026-07-15T09:00:00" }
```

The scheduler polls every 60 seconds and sends any email where `scheduled_at <= now (UTC)`.

#### Email status lifecycle

```
draft  →  pending  →  sent
               ↓
             failed
```

---

## AI Model Fallback

Every generation request tries **OpenAI GPT-4o-mini** first. On any failure it automatically falls back to **Google Gemini 2.0 Flash**. The `ai_model` field in the response tells you which was used.

| Model | Input | Output |
|---|---|---|
| GPT-4o-mini | $0.150 / 1M tokens | $0.600 / 1M tokens |
| Gemini 2.0 Flash | $0.10 / 1M tokens | $0.40 / 1M tokens |

Fallback is only active when `GEMINI_API_KEY` is set in `.env`.

---

## Development Phases

| Phase | Deliverable | Status |
|---|---|---|
| Week 1 | FastAPI + Auth + AI email generation + token tracking | ✅ Complete |
| Week 2 | Gmail SMTP + APScheduler + Gemini fallback + Fernet encryption | ✅ Complete |
| Week 3 | React + Vite frontend — full dashboard with live API integration | ✅ Complete |
| Week 4 | Deploy + first real users | 🔜 Next |
