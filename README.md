# MailFlow AI

An AI-powered email outreach agent. Generate personalized emails with OpenAI GPT-4o-mini, Gemini 2.0 Flash, or Groq (gpt-oss-120b), in fallback order, schedule them, and send automatically via Gmail SMTP — all from a React dashboard.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.13) |
| Database | SQLite + SQLAlchemy 2.x |
| Auth | JWT (PyJWT) + bcrypt; Google OAuth for Gmail |
| AI — Primary | OpenAI GPT-4o-mini |
| AI — Fallback | Google Gemini 2.0 Flash, then Groq `openai/gpt-oss-120b` |
| Email sending | Gmail API (Google OAuth) or Gmail SMTP with an App Password |
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

Copy `.env.example` to `.env` and fill in your values. **Don't put comments on the same line as a value**; they become part of the value.

```env
ENVIRONMENT=development
OPENAI_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=gsk_your-groq-key
JWT_SECRET=<random string, 32+ chars>
FERNET_KEY=<generated key>
CORS_ORIGINS=http://localhost:5173
```

Generate the secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"                               # JWT_SECRET
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # FERNET_KEY
```

The app refuses to start if `FERNET_KEY` is not a valid key. Changing `FERNET_KEY` later makes saved Gmail passwords unreadable, so users would need to re-enter them.

| Variable | Where to get it |
|---|---|
| `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `GEMINI_API_KEY` | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) — free tier, used as fallback |
| `FERNET_KEY` | Generate with command above |
| `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) |
| `JWT_SECRET` | Random string, 32+ characters |
| `ENVIRONMENT` | `production` enables startup safety checks (see Production Deployment) |
| `CORS_ORIGINS` | Comma-separated frontend URLs allowed to call the API |
| `AI_TIMEOUT_SECONDS` | Optional, default 45 |
| `RATE_LIMIT_AUTH_PER_MINUTE` / `RATE_LIMIT_GENERATE_PER_MINUTE` | Optional per-IP limits, default 10 / 20 |

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

Each user connects one Gmail account, in one of two ways:

- **Connect with Google (recommended):** OAuth with only the `gmail.send` permission. Emails go out through the Gmail API. Users never handle passwords, and they can revoke access from their Google account. This option is available when `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set.
- **App Password (fallback):** sends over SMTP. The password is checked against Gmail before it's saved.

Either way, the secret (refresh token or App Password) is Fernet-encrypted at rest.

| Method | Path | Description |
|---|---|---|
| GET | `/api/mailbox/options` | `{"google_oauth": bool, "app_password": true}`: which methods this server supports |
| GET | `/api/mailbox/google/authorize` | Returns `{"url"}` for Google's consent screen |
| GET | `/api/mailbox/google/callback` | Google redirects here; stores the account, then redirects to `FRONTEND_URL/settings?gmail=connected` (or `?gmail=error&reason=denied\|scope\|expired\|google\|invalid`) |
| POST | `/api/mailbox` | Save (or replace) an App Password credential |
| GET | `/api/mailbox` | Current account and its `provider` (`google` or `app_password`). Secrets are never returned |
| DELETE | `/api/mailbox` | Disconnect. For Google, this also revokes the grant |

#### Setting up "Connect with Google"

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project (or pick one) and **enable the Gmail API** (APIs & Services → Library → Gmail API).
2. **OAuth consent screen** (Google Auth Platform → Branding / Audience / Data access):
   - User type **External**; app name, support email and developer email.
   - Data access → Add scopes: `openid`, `.../auth/userinfo.email`, `.../auth/gmail.send`.
   - Audience → while the app is in **Testing**, add each Gmail address that will connect as a **test user** (up to 100).
3. **Clients → Create client → Web application**:
   - Authorized redirect URI: `http://localhost:8000/api/mailbox/google/callback` (add your production `https://.../api/mailbox/google/callback` too).
4. Put the client ID and secret in `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, then restart the backend.

**Before public launch:** `gmail.send` is a *sensitive* scope. In Testing mode only listed test users can connect, and refresh tokens **expire after 7 days**, after which users see "Reconnect Gmail". To lift both limits, publish the app and complete Google's verification. This needs a privacy policy, a homepage on a verified domain, and a demo video; it usually takes a few days to a few weeks. Reading replies later needs `gmail.readonly`, a *restricted* scope, which also requires a paid third-party security assessment.

**How to get a Gmail App Password (fallback):**
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
| PATCH | `/api/emails/{id}` | Edit `subject` and/or `body` (draft, failed or pending) |
| POST | `/api/emails/{id}/regenerate` | `{}` = fresh version from the original inputs; `{"refinement": "shorter\|longer\|warmer\|more_direct\|more_formal", "instruction": "..."}` = AI revises the current draft, including manual edits. Updates the same email; token and cost totals accumulate |
| POST | `/api/emails/{id}/schedule` | Schedule a draft for a future time |
| DELETE | `/api/emails/{id}/schedule` | Cancel schedule — moves back to draft |
| DELETE | `/api/emails/{id}` | Delete a draft or failed email |

### Campaigns

Send one message, personalised by AI for every contact in a CSV, with optional follow-ups in the same Gmail thread.

1. **Create** a campaign: purpose, tone, length, sender name and a shared pitch (`context`).
2. **Import a CSV.** An `email` column is required. Optional columns: `name` (or first/last name), `company`, `title`, `notes`. Header names are matched loosely; commas, semicolons and tabs all work. Invalid and duplicate rows are skipped and reported. The limit is 500 recipients per campaign.
3. **Write emails.** A background worker writes one email per recipient, about 4 every 30 seconds. On Groq's free tier, expect around 5 per minute. If the AI provider is rate-limited, recipients stay queued and are retried; they never get a canned fallback email. Each email can be reviewed, edited or rewritten.
4. **Launch.** Emails are scheduled `send_interval_minutes` apart, starting now or at a chosen time.
5. **Follow-ups** (0–3, `followup_delay_days` apart). After each send, the worker writes the next follow-up as a reply (`Re:` subject, `In-Reply-To`/`References` headers) and schedules it.
6. **Replies.** Marking a recipient as replied deletes their unsent follow-ups and stops the sequence. Replies are not detected automatically yet, because that needs the restricted `gmail.readonly` scope (see Google setup).

**Pausing:** a paused campaign holds all its sends. Resuming re-spaces any overdue emails so they don't go out in a burst. A campaign completes when nothing is left to write or send.

| Method | Path | Description |
|---|---|---|
| GET / POST | `/api/campaigns` | List (with stats) / create |
| GET / PUT / DELETE | `/api/campaigns/{id}` | Detail with stats / edit settings (draft only) / delete. Unsent emails are removed; sent emails stay |
| POST | `/api/campaigns/{id}/recipients/csv` | `{"csv": "<file text>"}` → `{"added", "skipped": [{"row", "reason"}]}` (draft only) |
| GET | `/api/campaigns/{id}/recipients` | Recipients with status and their emails (all steps) |
| DELETE | `/api/campaigns/{id}/recipients/{rid}` | Remove a recipient and their unsent emails |
| POST | `/api/campaigns/{id}/recipients/{rid}/replied` | Mark as replied and stop follow-ups |
| POST | `/api/campaigns/{id}/generate` | Queue AI writing for recipients without an email |
| POST | `/api/campaigns/{id}/launch` | `{start_at?, send_interval_minutes, followup_count, followup_delay_days}`. Requires a connected Gmail |
| POST | `/api/campaigns/{id}/pause` · `/resume` | Hold / continue sending |

Campaign emails also appear under Scheduled and Sent. `GET /api/emails?include_campaigns=false` hides them; the Drafts page uses this.

### Accounts: verification & passwords

- **Signup** sends a verification link (valid for 3 days). Unverified users can log in, browse and set up their profile, but AI writing, sending, scheduling and campaign launch return **403** until they verify. This stops fake signups from using AI quota or sending mail. Accounts created before this feature are treated as verified.
- **Forgot password** emails a reset link that is valid for 1 hour and works **once** (it's bound to the current password hash). The response is the same whether or not the account exists. Resetting also verifies the email.
- **Change password** is in Settings → Account.
- Links go to `FRONTEND_URL/verify-email` and `FRONTEND_URL/reset-password`. System emails use `SMTP_*`, which is required in production. In development, without SMTP, the emails and their links are written to the server log.

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/verify-email` | `{token}` |
| POST | `/api/auth/resend-verification` | Auth required; rate-limited |
| POST | `/api/auth/forgot-password` | `{email}` → always 202 |
| POST | `/api/auth/reset-password` | `{token, password}` → new access token |
| POST | `/api/auth/change-password` | `{current_password, new_password}` |

### Gmail daily send limit

Each user sends at most `DAILY_SEND_LIMIT` emails (default 400) per **rolling 24 hours**, safely under Gmail's ~500/day for personal accounts. Going over Gmail's limit gets the account temporarily blocked from sending. Due emails over the cap stay `pending` and go out as the window frees up. "Send now" returns **429** at the cap. Settings and the campaign launch dialog show how much is left.

### Unsubscribe & Do-Not-Contact

Required for cold email by law (CAN-SPAM, GDPR) and, since 2024, by Gmail and Yahoo for bulk senders.

- **Every campaign email** gets a footer with an unsubscribe link, plus the sender's postal address from the sender profile if one is set. It also gets `List-Unsubscribe` and `List-Unsubscribe-Post: List-Unsubscribe=One-Click` headers (RFC 8058), so mail apps show their own Unsubscribe button. The footer is added **at send time** and isn't stored in the draft, so editing an email can't remove it. One-off emails from the builder don't get a footer.
- **Links** point to `PUBLIC_API_URL/u/<signed token>` and never expire. Opening the link shows a confirmation page, and only a POST unsubscribes, because corporate mail scanners open links automatically. One-click POSTs from mail apps are accepted.
- **Unsubscribing** adds the address to that sender's do-not-contact list, marks matching campaign recipients `unsubscribed`, and deletes their unsent campaign emails.
- **Enforcement:** CSV imports skip listed addresses, "Send now" refuses them, and every send re-checks the list just before going out.
- **Manual list:** users can add addresses by hand or remove them in Settings → Do-not-contact list.

| Method | Path | Description |
|---|---|---|
| GET / POST | `/u/{token}` | Public confirmation page / unsubscribe (also handles RFC 8058 one-click) |
| GET / POST | `/api/suppressions` | The user's do-not-contact list / add `{"email"}` |
| DELETE | `/api/suppressions/{email}` | Remove an address |

### Plans & Usage

Plans are defined in `app/core/plans.py`; change limits there.

| | Free | Pro ($19/month) |
|---|---|---|
| AI emails per month | 50 | 2,000 |
| Recipients per campaign | 25 | 500 |
| Automatic follow-ups | No | Yes |

- **What counts as an AI email:** every AI write, meaning a new email, a rewrite or refinement, a campaign email or a follow-up. Usage is counted per calendar month (UTC).
- **How it's counted:** each write is reserved atomically before the AI call and refunded if the call fails, so concurrent requests can't go over the limit.
- **When a limit is hit:** the API returns **402** with a readable message, and the UI shows a "See plans" button.
- **Campaigns:** if a campaign needs more AI emails than the user has left, it is refused up front. If quota runs out mid-way, the affected recipients are marked "Write failed" with the reason, and follow-ups wait for the monthly reset.
- **Online payments aren't built yet.** The upgrade screen shows `SUPPORT_EMAIL` as the contact for upgrading. Change a user's plan by hand:

```bash
python -m app.cli set-plan someone@example.com pro
python -m app.cli show-user someone@example.com
```

A payment integration (Stripe or Razorpay) only needs to set `User.plan` from its webhook; every limit already reads from it.

| Method | Path | Description |
|---|---|---|
| GET | `/api/billing` | Current plan, this month's usage and reset date, all plans (for comparison), and `support_email` |

### Sender Profile

| Method | Path | Description |
|---|---|---|
| GET | `/api/profile` | Current profile (all fields `null` if not set up) |
| PUT | `/api/profile` | Save `full_name`, `role`, `company`, `about`, `signature`. Replaces the whole profile; blank fields are cleared |

Every generation and refinement includes the profile in the prompt. The `about` field is the main guard against invented claims, because it gives the AI real facts about what the sender offers.

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
{ "scheduled_at": "2026-07-15T09:00:00Z" }
```

Send a timezone-aware time (e.g. `toISOString()`); a naive time is treated as UTC. Times in the past or more than a year ahead are rejected. All datetimes in responses are UTC with a `Z` suffix.

The scheduler polls every 60 seconds and sends any email where `scheduled_at <= now (UTC)`. Each email is claimed atomically before sending, so it can't be sent twice even if "Send now" races the scheduler.

#### Email status lifecycle

```
draft  →  pending  →  sending  →  sent
                         ↓
                       failed   (error_message explains why; can be rescheduled or re-sent)
```

If the server stops mid-send, emails left in `sending` are marked `failed` at startup instead of being resent. Check the Gmail Sent folder before retrying them.

---

## AI Model Fallback

Each generation request tries the configured providers in order: **OpenAI GPT-4o-mini**, then **Google Gemini 2.0 Flash**, then **Groq `openai/gpt-oss-120b`** (free tier). A provider is skipped when its key is empty. The `ai_model` field in the response tells you which one was used.

If every provider fails, development mode returns a canned `mock-test` email. Production returns `503` instead, so users never get a fake email without knowing.

| Model | Input | Output |
|---|---|---|
| GPT-4o-mini | $0.150 / 1M tokens | $0.600 / 1M tokens |
| Gemini 2.0 Flash | $0.10 / 1M tokens | $0.40 / 1M tokens |


---

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Tests use a throwaway SQLite database and never call real AI providers or Gmail.

---

## Production Deployment

Set `ENVIRONMENT=production`. In production the app:

- refuses to start with the built-in dev `JWT_SECRET`/`FERNET_KEY`, a JWT secret under 32 chars, `CORS_ORIGINS=*`, or a non-https `PUBLIC_API_URL`
- disables `/docs`, `/redoc` and `/openapi.json`
- returns `503` instead of a mock email when all AI providers fail
- sends HSTS and other security headers

**Docker:**

```bash
docker build -t mailflow .
docker run -d -p 8000:8000 --env-file .env -e ENVIRONMENT=production \
  -e CORS_ORIGINS=https://app.example.com -v mailflow-data:/data mailflow
```

The SQLite database lives in the `/data` volume. Put the API behind an HTTPS reverse proxy (Caddy, nginx, or a platform load balancer). `GET /health` checks database connectivity and is used as the container healthcheck.

Run **one worker per deployment**. The email scheduler and the rate limiter run inside the process. Double-sends are still prevented with more workers, but each worker would run its own scheduler, and rate limits would apply per worker.

**Frontend:** build with the API URL baked in and serve `frontend/dist` from any static host:

```bash
cd frontend && VITE_API_BASE_URL=https://api.example.com npm run build
```

**Known limits:** SQLite suits a single server. For multiple instances, switch `DATABASE_URL` to Postgres (add `psycopg[binary]`) and move rate limiting to Redis. Schema changes use a small built-in migration that only adds columns; adopt Alembic before making larger changes.

---

## Development Phases

| Phase | Deliverable | Status |
|---|---|---|
| Week 1 | FastAPI + Auth + AI email generation + token tracking | ✅ Complete |
| Week 2 | Gmail SMTP + APScheduler + Gemini fallback + Fernet encryption | ✅ Complete |
| Week 3 | React + Vite frontend — full dashboard with live API integration | ✅ Complete |
| Week 4 | Deploy + first real users | 🔜 Next |
