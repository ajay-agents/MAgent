# MailFlow AI

An AI-powered email outreach SaaS. Write personalised emails with AI (OpenAI, Gemini or Groq), edit and refine them,
send or schedule them from your own Gmail, and run **campaigns**: a CSV of contacts, one personalised email each, with
automatic follow-ups in the same thread. It includes Free/Pro plans with usage limits, one-click unsubscribe and a
do-not-contact list, email verification and password reset, and a one-command production deployment.

## Features

- **AI email builder:** six purposes (cold outreach, follow-up, networking, …), tone and length controls, a sender profile fed into every prompt, inline editing, and one-click refine (shorter, warmer, more direct, …)
- **Gmail sending:** "Connect with Google" (OAuth, send-only permission) or a Gmail App Password; send now or schedule
- **Campaigns:** CSV import, background AI writing, staggered sending, threaded follow-ups, mark replied, pause/resume
- **Compliance:** unsubscribe link and one-click headers on every campaign email, a per-sender do-not-contact list, postal-address footer, and a per-user daily send cap under Gmail's limit
- **Accounts:** email verification, password reset and change password
- **Plans:** Free/Pro with atomic monthly AI-email metering; upgrades are manual until payments are added
- **Production-ready:** startup config guards, rate limiting, crash-safe sending, Docker Compose + Caddy with automatic HTTPS, 109 tests

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.13 (3.10+ required) |
| Database | SQLite + SQLAlchemy 2.x (Postgres-ready via `DATABASE_URL`) |
| Auth | JWT (PyJWT) + bcrypt; signed links for verification, password reset and unsubscribe |
| AI | OpenAI GPT-4o-mini → Google Gemini 2.0 Flash → Groq `openai/gpt-oss-120b` (first configured wins, falls back on failure) |
| Email sending | Gmail API (Google OAuth) or Gmail SMTP with an App Password |
| System email | Any SMTP provider (verification and password-reset emails) |
| Background jobs | APScheduler, in-process: send due emails every 60 s; campaign writing and follow-ups every 30 s |
| Encryption | Fernet (cryptography) for stored Gmail App Passwords and Google tokens |
| Frontend | React 19 + Vite 8 + Tailwind CSS v4 |
| Deployment | Docker Compose: FastAPI + Caddy (static frontend, reverse proxy, automatic HTTPS) |

---

## Project Structure

```
MAgent/
├── app/
│   ├── main.py                  # FastAPI app, lifespan (migrations + scheduler), middleware, routers
│   ├── config.py                # Settings from .env, with production safety checks
│   ├── cli.py                   # Admin commands: set-plan, show-user
│   ├── db/session.py            # SQLAlchemy engine (SQLite WAL), session, Base
│   ├── models/models.py         # User, ScheduledEmail, MailboxCredential, SenderProfile, Campaign,
│   │                            #   CampaignRecipient, UsageCounter, Suppression
│   ├── schemas/schemas.py       # Pydantic request/response models (UTC datetimes, input limits)
│   ├── api/routes/
│   │   ├── auth.py              # signup, login, me, verify email, forgot/reset/change password
│   │   ├── emails.py            # generate, edit, regenerate/refine, schedule, send, trash/restore
│   │   ├── campaigns.py         # campaigns: CSV import, generate, launch, pause/resume, recipients
│   │   ├── mailbox.py           # Gmail connection: Google OAuth flow or App Password
│   │   ├── profile.py           # sender profile
│   │   ├── billing.py           # plan, usage and limits
│   │   └── unsubscribe.py       # public /u/<token> pages + do-not-contact list API
│   ├── prompts/                 # One prompt file per purpose (instruction + few-shot example)
│   └── core/
│       ├── openai_client.py     # Prompt building, provider fallback, anti-fabrication rules
│       ├── campaigns.py         # CSV parsing, background writer, launch, follow-ups, replies
│       ├── delivery.py          # Atomic send claiming, daily cap, threading, compliance footer
│       ├── scheduler.py         # APScheduler jobs
│       ├── google_oauth.py      # OAuth + Gmail API sending
│       ├── smtp_sender.py       # MIME building + Gmail SMTP
│       ├── system_mail.py       # Transactional email (verification / reset)
│       ├── unsubscribe.py       # Signed unsubscribe links, footer, suppression list
│       ├── plans.py             # Plan limits and monthly usage metering
│       ├── account_tokens.py    # Verification and password-reset tokens
│       ├── rate_limit.py        # Per-IP sliding-window limiter
│       ├── security.py          # Password hashing, JWT, auth dependencies
│       └── encryption.py        # Fernet helpers
├── tests/                       # pytest suite (fake AI and Gmail, throwaway database)
├── frontend/
│   ├── Dockerfile               # Builds the app, serves it with Caddy
│   └── src/
│       ├── pages/               # Homepage, Dashboard, CreateEmail, Campaigns, CampaignDetail, Drafts,
│       │                        #   ScheduledEmails, SentEmails, DeletedEmails, Settings, AuthModal,
│       │                        #   VerifyEmail, ResetPassword, Legal (privacy + terms)
│       ├── components/          # Sidebar, Navbar, VerifyBanner, UpgradeModal, CampaignBits, ProtectedRoute
│       ├── context/             # AuthContext, ThemeContext
│       └── services/            # api.js (fetch wrapper), billing.js (shared plan/usage fetch)
├── deploy/Caddyfile             # Production routing + HTTPS
├── docker-compose.yml           # Production stack
├── Dockerfile                   # API image
├── requirements.txt / requirements-dev.txt
├── .env.example                 # Every setting, documented
└── start.bat                    # Windows shortcut to start the backend
```

---

## Local Development

### 1. Backend

Requires **Python 3.10 or newer**; 3.13 is recommended. On macOS with Homebrew: `brew install python@3.13`.

**macOS / Linux:**
```bash
python3.13 -m venv venv
venv/bin/pip install -r requirements-dev.txt
cp .env.example .env            # then edit it (see below)
venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements-dev.txt
copy .env.example .env
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000   # or .\start.bat
```
If PowerShell refuses to run scripts: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.

Backend: `http://localhost:8000` · API docs: `http://localhost:8000/docs` (development only)

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```
Frontend: `http://localhost:5173`. It calls the backend at `http://localhost:8000` by default. To point it elsewhere, set `VITE_API_BASE_URL` in `frontend/.env.local`. Production builds use the same origin.

### 3. Configure `.env`

`.env.example` lists and explains every setting. **Don't put comments on the same line as a value**; they become part of the value. For local development you only need:

| Variable | Notes |
|---|---|
| `GROQ_API_KEY` (or `OPENAI_API_KEY` / `GEMINI_API_KEY`) | At least one AI key. With none, the app returns a canned mock email (development only). Keys: [console.groq.com](https://console.groq.com/keys), [platform.openai.com](https://platform.openai.com/api-keys), [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `JWT_SECRET`, `LINK_SIGNING_SECRET` | Random strings: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `FERNET_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Changing it later makes saved Gmail credentials unreadable |

Everything else has working development defaults:
- Without `SMTP_*`, verification and password-reset links are printed in the backend log.
- Without `GOOGLE_CLIENT_*`, Settings offers only the App Password option.

Optional settings include `DAILY_SEND_LIMIT`, `SUPPORT_EMAIL`, `AI_TIMEOUT_SECONDS` and `RATE_LIMIT_*`.

### 4. Useful commands

```bash
venv/bin/python -m pytest                                      # run the tests
venv/bin/python -m app.cli set-plan you@example.com pro        # give an account Pro
cd frontend && npx eslint . && npm run build                   # lint and build the frontend
```

---

## Frontend Pages

| Page | Route | What it does |
|---|---|---|
| Landing | `/` | Marketing page, login/signup modal (with forgot password) |
| Dashboard | `/dashboard` | Stats: generated / sent / scheduled / failed |
| Create Email | `/create-email` | AI builder: generate, edit inline, refine, regenerate, schedule or send |
| Campaigns | `/campaigns`, `/campaigns/:id` | Create a campaign, import a CSV, write, review and edit, launch, follow-ups, mark replied |
| Drafts | `/drafts` | One-off drafts: view, edit, send, delete |
| Scheduled | `/scheduled-emails` | Pending emails: view, reschedule, unschedule, delete |
| Sent | `/sent-emails` | Sent and failed history, with failure reasons |
| Deleted | `/deleted-emails` | Trash: restore or delete permanently |
| Settings | `/settings` | Plan & usage, sender profile, do-not-contact list, Gmail connection, dark mode, change password |
| Verify email / Reset password | `/verify-email`, `/reset-password` | Targets of the emailed links |
| Privacy / Terms | `/privacy`, `/terms` | Draft legal pages (fill in placeholders in `Legal.jsx`) |

---

## API Reference

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/signup` | — | Register; sends a verification email |
| POST | `/api/auth/login` | — | Login, returns JWT token |
| GET | `/api/auth/me` | JWT | Current user, including `email_verified` |
| POST | `/api/auth/verify-email`, `/resend-verification`, `/forgot-password`, `/reset-password`, `/change-password` | varies | See [Accounts](#accounts-verification--passwords) |

Rate limits: 10 auth requests and 20 AI generations per minute per IP; endpoints that send email are limited to 5 per minute.

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
| GET | `/api/emails` | List emails. `?status=draft\|pending\|sent\|failed\|deleted`, `include_campaigns=false` hides campaign emails, `limit`/`offset` paginate |
| GET | `/api/emails/{id}` | Full detail including email body |
| PATCH | `/api/emails/{id}` | Edit `subject` and/or `body` (draft, failed or pending) |
| POST | `/api/emails/{id}/regenerate` | `{}` = fresh version from the original inputs; `{"refinement": "shorter\|longer\|warmer\|more_direct\|more_formal", "instruction": "..."}` = AI revises the current draft, including manual edits. Updates the same email; token and cost totals accumulate |
| POST | `/api/emails/{id}/schedule` | Schedule a draft for a future time |
| DELETE | `/api/emails/{id}/schedule` | Cancel schedule — moves back to draft |
| POST | `/api/emails/{id}/send` | Send now. 400 if no Gmail is connected or the recipient unsubscribed; 429 at the daily cap |
| DELETE | `/api/emails/{id}` | Move to trash (cancels a pending schedule) |
| POST | `/api/emails/{id}/restore` | Restore from trash as a draft |
| DELETE | `/api/emails/{id}/permanent` | Delete for good |

Generating, rewriting, scheduling and sending require a verified email (403 otherwise). AI calls count toward the plan's monthly quota (402 when it runs out).

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
| PUT | `/api/profile` | Save `full_name`, `role`, `company`, `about`, `signature`, `postal_address`. Replaces the whole profile; blank fields are cleared |

Every generation and refinement includes the profile in the prompt. The `about` field is the main guard against invented claims, because it gives the AI real facts about what the sender offers.

---

## AI Model Fallback

Each generation request tries the configured providers in order: **OpenAI GPT-4o-mini**, then **Google Gemini 2.0 Flash**, then **Groq `openai/gpt-oss-120b`** (free tier). A provider is skipped when its key is empty. The `ai_model` field in the response tells you which one was used.

If every provider fails, development mode returns a canned `mock-test` email. Production returns `503` instead, so users never get a fake email without knowing.

| Model | Input | Output |
|---|---|---|
| GPT-4o-mini | $0.150 / 1M tokens | $0.600 / 1M tokens |
| Gemini 2.0 Flash | $0.10 / 1M tokens | $0.40 / 1M tokens |
| Groq `openai/gpt-oss-120b` | Free tier: 8,000 tokens/min (~5 emails/min) shared by all users | Paid tiers available |

Groq runs with low reasoning effort (about 1,500 tokens per email). Every call has a timeout (`AI_TIMEOUT_SECONDS`, default 45 s). Campaign writing never falls back to the mock email: a rate-limited recipient stays queued and is retried.


---

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Tests use a throwaway SQLite database and never call real AI providers or Gmail.

---

## Production Deployment

MailFlow runs as two containers behind **one domain**: Caddy serves the React app, proxies `/api`, `/u` (unsubscribe) and `/health` to FastAPI, and obtains and renews HTTPS certificates automatically. Because everything is same-origin, there's no CORS setup, and links in emails use your own domain.

### 1. Server and DNS
Use any Linux VM with Docker (1 vCPU / 1 GB RAM is plenty to start). Open ports 80 and 443, and point your domain's DNS **A record** at the server.

### 2. Configure `.env` on the server
Copy `.env.example` to `.env` and set at least:

| Variable | Notes |
|---|---|
| `DOMAIN` | e.g. `mailflow.example.com`. The URLs and CORS are derived from it |
| `JWT_SECRET`, `LINK_SIGNING_SECRET` | Two **different** random strings, 32+ characters. Never rotate `LINK_SIGNING_SECRET` |
| `FERNET_KEY` | Generate once and **back it up**. Losing it makes stored Gmail credentials unreadable |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | For verification and password-reset emails, e.g. Amazon SES, Postmark, Brevo or Google Workspace SMTP |
| `GROQ_API_KEY` / `OPENAI_API_KEY` | At least one AI provider. The Groq free tier is ~5 emails/min for *all* users, so use a paid tier for real traffic |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Optional ("Connect with Google"). Add `https://<DOMAIN>/api/mailbox/google/callback` as a redirect URI on the OAuth client |
| `SUPPORT_EMAIL` | Shown on the upgrade screen |

`ENVIRONMENT=production` is set by the compose file. In production the app **refuses to start** if secrets are defaults, URLs aren't https, or SMTP is missing, and it lists every problem it finds.

### 3. Start it
```bash
docker compose up -d --build
docker compose logs -f api        # look for "Starting MailFlow ... (production)"
curl https://<DOMAIN>/health      # {"status":"ok",...}
```
Update to a new version with `git pull && docker compose up -d --build`. Database migrations run automatically at startup.

### 4. Make yourself Pro and check sending
```bash
docker compose exec api python -m app.cli set-plan you@example.com pro
```
Then sign up and verify your email. Connect Gmail and send a two-person test campaign to your own addresses. Check that the unsubscribe link works and that the follow-up threads correctly.

### Backups
All data lives in the SQLite database in the `api-data` volume. Back it up daily, and keep the backups off the server:
```bash
docker compose exec api python -c "import sqlite3; sqlite3.connect('/data/mailflow.db').backup(sqlite3.connect('/data/backup.db'))"
docker compose cp api:/data/backup.db ./mailflow-$(date +%F).db
```
Back up `.env` too (especially `FERNET_KEY` and `LINK_SIGNING_SECRET`), and store it somewhere safe and separate.

### Production behaviour
- `/docs`, `/redoc` and `/openapi.json` are disabled.
- When every AI provider fails, users get a `503` instead of a mock email.
- HSTS and other security headers are sent.

### Scaling limits
This setup is designed for **one server and one API worker**. The email scheduler, campaign worker and rate limiter run inside the process; sends are claimed atomically, so a second worker can't double-send, but each worker would run its own scheduler. To grow beyond one server:
- move to Postgres (`DATABASE_URL`, plus `psycopg[binary]`)
- move rate limiting to Redis
- adopt Alembic for schema changes; the built-in migration only adds columns

---

## Roadmap

| Status | Item |
|---|---|
| ✅ Done | Auth, AI generation with provider fallback, Gmail sending and scheduling, React dashboard |
| ✅ Done | Production hardening, editing and refine, sender profile, Connect with Google |
| ✅ Done | Campaigns with threaded follow-ups, Free/Pro plans, unsubscribe and do-not-contact |
| ✅ Done | Email verification, password reset, daily send cap, legal page drafts, Docker + Caddy deployment |
| 🔜 Next | First production deploy, Google OAuth verification, real-send test |
| Later | Online payments (Stripe or Razorpay), self-serve account deletion, automatic reply and bounce detection (needs Google's restricted `gmail.readonly` scope), analytics, Postgres + Redis for multiple servers |
