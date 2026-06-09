# Job Agent MVP — Master Build Prompt
> Feed this entire file to Claude Code. It contains the full spec, folder structure, tech stack, and milestone-by-milestone build instructions for a 24/7 automated job application agent.

---

## Project Overview

Build a full-stack web application that automatically finds, tailors, and submits job applications on behalf of the user. The app runs locally on Windows and is accessed via a browser. The user brings their own AI API key (BYOK). All AI costs are paid by the user, not the operator.

**Target platform:** Web app (React + FastAPI), runs on Windows, accessed at `http://localhost:5173`
**Primary job market:** Australia (Seek, Indeed AU, LinkedIn AU, Jora)
**International:** Plugin stubs for LinkedIn Global, Indeed US/UK/CA/NZ, Glassdoor (toggle in settings, no active scraping logic required for MVP)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | Python 3.11+ + FastAPI + Uvicorn |
| Database | SQLite via SQLAlchemy (async) |
| Scraping & form-fill | Playwright (Python, headless Chromium) |
| Document parsing | python-docx (DOCX), PyMuPDF/fitz (PDF read), ReportLab (PDF write) |
| AI layer | openai Python SDK (OpenAI-compatible — works with Claude, Gemini, Ollama) |
| Scheduling | APScheduler (AsyncIOScheduler) |
| Notifications | smtplib (standard library SMTP) |
| Secrets | cryptography (Fernet) for API key encryption at rest |
| Dev tooling | concurrently (npm) to run both servers with one command |

---

## Folder Structure

```
job-agent/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── database.py              # SQLAlchemy async engine + session
│   ├── models.py                # All ORM models
│   ├── schemas.py               # Pydantic schemas
│   ├── config.py                # App config, encryption helpers
│   ├── scheduler.py             # APScheduler setup
│   ├── routers/
│   │   ├── profile.py           # Profile + document upload endpoints
│   │   ├── jobs.py              # Job listing endpoints
│   │   ├── applications.py      # Application queue + approval endpoints
│   │   ├── settings.py          # API key + provider settings endpoints
│   │   └── notifications.py     # Email digest endpoints
│   ├── scrapers/
│   │   ├── base.py              # Base scraper class
│   │   ├── seek.py              # Seek.com.au scraper
│   │   ├── indeed_au.py         # Indeed AU scraper
│   │   ├── linkedin_au.py       # LinkedIn AU scraper (session cookie auth)
│   │   ├── jora.py              # Jora.com.au scraper
│   │   └── plugins/
│   │       ├── linkedin_global.py   # Stub — not active in MVP
│   │       ├── indeed_intl.py       # Stub — not active in MVP
│   │       └── glassdoor.py         # Stub — not active in MVP
│   ├── services/
│   │   ├── ai_service.py        # BYOK AI wrapper (OpenAI-compatible)
│   │   ├── document_service.py  # Resume/cover letter parse + generate
│   │   ├── matching_service.py  # Job matching, blacklist/whitelist, salary filter
│   │   └── submission_service.py # Email + Seek + LinkedIn Easy Apply submission
│   └── uploads/                 # User-uploaded resumes and cover letters (gitignored)
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── api/
│   │   │   └── client.js        # Axios instance pointing to backend
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Job listings feed
│   │   │   ├── Queue.jsx        # Approval queue
│   │   │   ├── Log.jsx          # Submission log + tracker
│   │   │   ├── Profile.jsx      # Profile builder + document upload
│   │   │   └── Settings.jsx     # API keys, providers, scraper config
│   │   └── components/
│   │       ├── JobCard.jsx
│   │       ├── ApplicationCard.jsx
│   │       ├── DocumentUpload.jsx
│   │       ├── ApiKeyPanel.jsx
│   │       └── Sidebar.jsx
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
├── .env                         # Never commit — holds encryption salt
├── requirements.txt
├── package.json                 # Root — runs both servers via concurrently
└── README.md
```

---

## Database Schema (SQLite via SQLAlchemy)

### Table: `user_profile`
```
id              INTEGER PRIMARY KEY
name            TEXT
email           TEXT
phone           TEXT
location        TEXT
target_roles    TEXT (JSON array)
target_salary_min INTEGER (AUD)
target_salary_max INTEGER (AUD)
work_types      TEXT (JSON array: ["remote","hybrid","onsite"])
industries      TEXT (JSON array)
blacklist_keywords TEXT (JSON array)
whitelist_companies TEXT (JSON array)
tone_preference TEXT (default: "professional")  -- professional | conversational | technical
created_at      DATETIME
updated_at      DATETIME
```

### Table: `documents`
```
id              INTEGER PRIMARY KEY
type            TEXT  -- "resume" | "cover_letter"
filename        TEXT
filepath        TEXT  -- relative path under backend/uploads/
parsed_text     TEXT  -- extracted plain text for AI context
is_active       BOOLEAN (default true)
uploaded_at     DATETIME
```

### Table: `api_settings`
```
id              INTEGER PRIMARY KEY
provider        TEXT  -- "openai" | "anthropic" | "google" | "ollama" | "custom"
api_key_enc     TEXT  -- Fernet-encrypted key
base_url        TEXT  -- for Ollama/custom: e.g. http://localhost:11434/v1
model_name      TEXT  -- e.g. gpt-4o-mini, claude-sonnet-4-5, llama3
is_active       BOOLEAN
ai_scorer_enabled BOOLEAN (default false)
created_at      DATETIME
```

### Table: `scraper_config`
```
id              INTEGER PRIMARY KEY
source          TEXT  -- "seek" | "indeed_au" | "linkedin_au" | "jora" | plugin names
enabled         BOOLEAN
keywords        TEXT (JSON array)
location        TEXT
linkedin_session_cookie TEXT (encrypted) -- for LinkedIn AU
schedule_hours  INTEGER (default 2)
last_run        DATETIME
```

### Table: `job_listings`
```
id              INTEGER PRIMARY KEY
source          TEXT
external_id     TEXT (unique per source)
title           TEXT
company         TEXT
location        TEXT
work_type       TEXT
salary_text     TEXT
salary_min      INTEGER
salary_max      INTEGER
description     TEXT
url             TEXT
posted_at       DATETIME
scraped_at      DATETIME
match_score     REAL (nullable — only set if AI scorer enabled)
status          TEXT (default "new") -- "new" | "queued" | "skipped" | "applied"
```

### Table: `applications`
```
id              INTEGER PRIMARY KEY
job_id          INTEGER (FK -> job_listings)
cover_letter    TEXT (generated)
resume_version  TEXT (filepath of tailored resume PDF)
status          TEXT -- "pending" | "approved" | "rejected" | "submitted" | "failed"
submission_method TEXT -- "email" | "seek_form" | "linkedin_easy_apply"
submitted_at    DATETIME
created_at      DATETIME
notes           TEXT
```

---

## Milestone Build Instructions

### M1 — Project Scaffold & Database

1. Create the full folder structure above.
2. `requirements.txt`:
```
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
aiosqlite
python-multipart
python-dotenv
cryptography
openai
playwright
python-docx
pymupdf
reportlab
apscheduler
httpx
pydantic[email]
```
3. Root `package.json` with a `dev` script:
```json
{
  "name": "job-agent",
  "scripts": {
    "dev": "concurrently \"uvicorn backend.main:app --reload --port 8000\" \"npm run dev --prefix frontend\""
  },
  "devDependencies": {
    "concurrently": "^8.0.0"
  }
}
```
4. Frontend `package.json` with React 18, Vite, Tailwind, Axios, React Router v6, React Query.
5. `backend/database.py`: async SQLAlchemy engine pointing to `job_agent.db`. Include `Base`, `AsyncSession`, and `get_db` dependency.
6. `backend/models.py`: All five ORM models above.
7. `backend/main.py`: FastAPI app with CORS enabled for `http://localhost:5173`. Include lifespan event that runs `Base.metadata.create_all` on startup. Register all routers with `/api` prefix.
8. `backend/config.py`: Load `.env`, expose a `FernetEncryption` class with `encrypt(text)` and `decrypt(text)` methods using a key derived from `ENCRYPTION_KEY` env var. Generate a random key and write it to `.env` if not present.
9. Frontend: Basic React app with React Router. Sidebar with links to: Dashboard, Queue, Log, Profile, Settings. Each page renders a placeholder heading for now.
10. `vite.config.js`: Proxy `/api` to `http://localhost:8000`.

**Acceptance test:** `npm run dev` from root starts both servers. Browser at `http://localhost:5173` shows the sidebar and placeholder pages. FastAPI docs at `http://localhost:8000/docs`.

---

### M2 — Profile, Resume & Cover Letter Upload

**Backend:**

1. `routers/profile.py`:
   - `GET /api/profile` — return current profile
   - `PUT /api/profile` — upsert profile fields
   - `POST /api/documents/upload` — accept multipart file upload (PDF or DOCX), save to `backend/uploads/`, extract plain text, save `Document` record
   - `GET /api/documents` — list all documents
   - `DELETE /api/documents/{id}` — delete document record and file
   - `PUT /api/documents/{id}/activate` — set as active resume or active cover letter

2. `services/document_service.py`:
   - `parse_docx(filepath) -> str` — extract plain text using python-docx
   - `parse_pdf(filepath) -> str` — extract plain text using PyMuPDF (`fitz.open`)
   - `parse_document(filepath) -> str` — dispatcher by extension
   - `generate_tailored_resume_pdf(base_resume_text, jd_text, profile, ai_service) -> bytes` — call AI to inject JD keywords into resume, render to PDF via ReportLab
   - `generate_cover_letter(jd_text, profile, cover_letter_samples, ai_service) -> str` — call AI with profile + JD + uploaded cover letter examples as style reference

**Frontend:**

1. `pages/Profile.jsx`:
   - Form for all profile fields (name, email, phone, location, target roles multi-select, salary range, work type checkboxes, industries, tone preference radio)
   - Save button calls `PUT /api/profile`

2. `components/DocumentUpload.jsx`:
   - Drag-and-drop or click-to-upload area for PDF/DOCX
   - Shows uploaded documents list with type badge (Resume / Cover Letter), filename, upload date
   - Toggle to set active, delete button
   - Calls `POST /api/documents/upload` with `multipart/form-data`

**Acceptance test:** Upload a PDF resume. It appears in the list. Check the database — `parsed_text` column is populated with extracted text.

---

### M3 — BYOK API Settings Panel

**Backend:**

1. `routers/settings.py`:
   - `GET /api/settings/api` — return all API provider configs (keys redacted — return `"••••••••"` for `api_key_enc`)
   - `POST /api/settings/api` — create/update a provider config. Encrypt the key before storing.
   - `DELETE /api/settings/api/{id}` — remove a provider
   - `POST /api/settings/api/{id}/test` — send a minimal test completion request using the stored key. Return `{success: bool, message: str, latency_ms: int}`
   - `GET /api/settings/scrapers` — return all scraper configs
   - `PUT /api/settings/scrapers/{source}` — update scraper config (enabled, keywords, location, schedule)

2. `services/ai_service.py`:
   - `class AIService`: initialized with an `api_settings` record
   - Uses the `openai` SDK with `base_url` and `api_key` from settings (this makes it compatible with Claude via `https://api.anthropic.com/v1`, OpenAI, Gemini's OpenAI-compat endpoint, and Ollama at `http://localhost:11434/v1`)
   - `async def complete(system_prompt, user_prompt, max_tokens=2000) -> str`
   - `async def score_job(jd_text, profile_text) -> float` — returns 0.0–1.0. Only called if `ai_scorer_enabled=True`
   - Track token usage per call and accumulate in a session counter

**Frontend:**

1. `pages/Settings.jsx` — two sections:

   **AI Provider section:**
   - Provider dropdown: OpenAI / Anthropic (Claude) / Google Gemini / Ollama (local) / Custom
   - API key input (password field, masked)
   - Base URL field (shown only for Ollama/Custom)
   - Model name input with placeholder suggestions per provider:
     - OpenAI: `gpt-4o-mini`, `gpt-4o`
     - Anthropic: `claude-haiku-4-5`, `claude-sonnet-4-6`
     - Gemini: `gemini-1.5-flash`, `gemini-1.5-pro`
     - Ollama: `llama3`, `mistral`, `phi3`
   - "Test connection" button — shows latency and success/error inline
   - AI Scorer toggle (off by default) with tooltip: "When enabled, uses your API key to score each job listing. Costs tokens per listing."
   - Estimated token usage counter (session)

   **Scraper config section:**
   - Toggle cards for each AU source: Seek, Indeed AU, LinkedIn AU, Jora
   - Keywords input, location input, schedule frequency (hours) per scraper
   - LinkedIn session cookie field with help text: "Paste your LinkedIn `li_at` cookie value here. Found in browser DevTools → Application → Cookies → www.linkedin.com. This avoids bot detection by using your real session."
   - Plugin section (greyed out, labelled "Coming soon"): LinkedIn Global, Indeed International, Glassdoor

**Acceptance test:** Add an API key, hit test, see green checkmark and latency. The key is stored encrypted in SQLite (confirm raw DB value is not plaintext).

---

### M4 — Job Board Scrapers

**Backend:**

1. `scrapers/base.py` — `BaseScraper` abstract class:
```python
class BaseScraper:
    source_name: str
    async def scrape(self, keywords: list[str], location: str) -> list[dict]: ...
    async def deduplicate_and_save(self, listings: list[dict], db: AsyncSession): ...
    # deduplicate by (source, external_id). Skip listings older than 30 days.
    # Apply freshness filter: if listing already exists in DB, skip.
```

2. `scrapers/seek.py` — `SeekScraper(BaseScraper)`:
   - Use Playwright async API, headless Chromium
   - Navigate to `https://www.seek.com.au/jobs?keywords={kw}&location={loc}`
   - Wait for job card selector: `article[data-card-type="JobCard"]`
   - Extract: title, company, location, salary text, job URL, posted date, external_id (from URL or data attribute)
   - For each listing, navigate to detail page and extract full description
   - Implement rate limiting: random sleep 2–5 seconds between page loads
   - Implement randomised user-agent rotation (maintain a list of 5 real Chrome UA strings)

3. `scrapers/indeed_au.py` — `IndeedAUScraper(BaseScraper)`:
   - URL: `https://au.indeed.com/jobs?q={kw}&l={loc}`
   - Extract from job cards: title, company, location, salary, job key (for URL), snippet
   - Navigate to full job page for description
   - Same rate limiting and UA rotation as Seek

4. `scrapers/linkedin_au.py` — `LinkedInAUScraper(BaseScraper)`:
   - **Session cookie approach:** Load the `li_at` cookie from settings before navigating. This avoids login automation.
   - Set cookie: `context.add_cookies([{"name": "li_at", "value": cookie_val, "domain": ".linkedin.com", "path": "/"}])`
   - URL: `https://www.linkedin.com/jobs/search/?keywords={kw}&location={loc}&f_WT=2` (AU filter)
   - Extract job cards: title, company, location, job ID, URL
   - Navigate to each job detail page for description
   - Rate limit: 4–8 second random delay between requests (LinkedIn is aggressive)

5. `scrapers/jora.py` — `JoraScraper(BaseScraper)`:
   - URL: `https://au.jora.com/jobs?q={kw}&l={loc}`
   - Same extraction pattern as Seek

6. `scrapers/plugins/` — Three stub files, each with a class that raises `NotImplementedError("Plugin not active in MVP")` and logs a warning.

7. `scheduler.py`:
   - `AsyncIOScheduler` with a job per enabled scraper
   - Each scraper job reads its config from DB (keywords, location, schedule_hours)
   - Runs `scraper.scrape()` then `scraper.deduplicate_and_save()`
   - After saving, triggers matching pipeline (M5)
   - Scheduler starts on app startup via FastAPI lifespan

8. `routers/jobs.py`:
   - `GET /api/jobs` — paginated list of job listings. Filter params: `status`, `source`, `min_score`, `search`
   - `GET /api/jobs/{id}` — single listing detail
   - `PUT /api/jobs/{id}/skip` — mark as skipped
   - `POST /api/jobs/scrape-now` — trigger an immediate scrape run (for testing)

**Frontend:**

1. `pages/Dashboard.jsx`:
   - Job listings feed — cards showing: title, company, location, work type, salary, source badge, match score (if set), posted date
   - Filter bar: source, work type, min score slider
   - Search input
   - "Scrape now" button
   - Each card has: "Queue for application" button, "Skip" button, click to expand full description

2. `components/JobCard.jsx`: Reusable job card component.

**Acceptance test:** Hit "Scrape now". After ~30 seconds, job listings appear in the Dashboard. Duplicates are not re-inserted on a second scrape.

---

### M5 — Job Matching & Filtering

**Backend:**

1. `services/matching_service.py`:
   - `apply_blacklist(listing, profile) -> bool` — returns True if listing should be skipped (title or description contains any blacklist keyword)
   - `apply_whitelist(listing, profile) -> bool` — returns True if company is in whitelist (always surface regardless of other filters)
   - `apply_salary_filter(listing, profile) -> bool` — parse salary from `salary_text` using AU-aware regex (handles "$80k", "$80,000", "$80-90k pa", "80000-90000", hourly rates converted to annual). Skip listing if max salary is below `target_salary_min`. Pass listings with no salary listed (can't filter what isn't stated).
   - `async def run_matching_pipeline(listings, profile, ai_service=None) -> list` — applies blacklist → salary filter → optional AI scorer → sets `match_score` on listing record → updates status to `"queued"` for passing listings

2. Wire `run_matching_pipeline` into the scheduler so it runs automatically after each scrape.

3. `routers/jobs.py` additions:
   - `POST /api/jobs/{id}/queue` — manually queue a listing for application

**Frontend:**

1. Update `Dashboard.jsx`:
   - Show match score badge (colour-coded: green ≥70, amber 40–69, red <40, grey if not scored)
   - Blacklisted listings shown greyed out with "Filtered" label (not hidden — user can still see why)
   - Salary filter slider in filter bar

**Acceptance test:** Add "unpaid" to blacklist. Scrape. Any listing containing "unpaid" is greyed out. Add a salary floor. Listings below it are filtered. Enable AI scorer — listings get numeric scores.

---

### M6 — Application Generation & Approval Queue

**Backend:**

1. `services/document_service.py` additions:

   `generate_cover_letter(jd_text, profile, active_cover_letters, ai_service, tone) -> str`:
   - System prompt: "You are an expert job application writer. Write in {tone} style. Do not invent facts. Only use information from the candidate profile and their example cover letters."
   - Include: profile summary, target role, active cover letter samples as style reference, full JD text
   - Return the generated cover letter text

   `generate_tailored_resume_pdf(base_resume_text, jd_text, profile, ai_service) -> bytes`:
   - AI call: identify top 5 keywords from JD not present in resume. Suggest minimal wording adjustments to bullet points that naturally incorporate them. Never change job titles, dates, or employers.
   - Apply suggestions to resume text
   - Render to PDF via ReportLab with clean professional formatting
   - Return PDF bytes

2. `routers/applications.py`:
   - `POST /api/applications/generate/{job_id}` — generate cover letter + tailored resume for a job. Creates an `Application` record with `status="pending"`.
   - `GET /api/applications` — list all applications, filterable by status
   - `GET /api/applications/{id}` — single application detail
   - `PUT /api/applications/{id}/approve` — set status to "approved", trigger submission
   - `PUT /api/applications/{id}/reject` — set status to "rejected"
   - `PUT /api/applications/{id}` — update cover letter text (for inline editing)
   - `GET /api/applications/{id}/resume` — serve the tailored resume PDF

3. Auto-generation: after matching pipeline queues listings, auto-generate applications for all newly queued listings.

4. Auto-approve mode: if `auto_approve_threshold` is set in settings (default: disabled), automatically approve and submit applications with `match_score >= threshold`.

5. `routers/notifications.py`:
   - `POST /api/notifications/test` — send a test digest email
   - Daily digest: APScheduler job at 8am local time. Email summary: jobs found today, applications generated, approved, submitted, rejected.
   - SMTP config stored in `api_settings` table (add fields: `smtp_host`, `smtp_port`, `smtp_user`, `smtp_pass_enc`, `notify_email`)

**Frontend:**

1. `pages/Queue.jsx` — Approval queue:
   - List of pending applications
   - Each application shows: job title, company, match score, generated cover letter (editable textarea), tailored resume preview/download link
   - Action buttons: Approve (green), Reject (red), Edit (opens cover letter inline)
   - Auto-approve toggle in header with threshold slider (disabled by default)

2. `pages/Log.jsx` — Submission log:
   - Table: Company | Role | Date | Source | Status | Match Score | Actions
   - Status badges: Pending / Approved / Submitted / Rejected / Failed
   - Click row to expand application detail

3. Settings: add SMTP config section and daily digest toggle.

**Acceptance test:** Queue a job. Click "Generate application". Cover letter appears in Queue. Edit it. Click Approve. Status changes to "approved" in the log.

---

### M7 — Submission Engine

**Backend:**

1. `services/submission_service.py`:

   `async def submit_by_email(application, job, profile) -> bool`:
   - Compose email: To = email address extracted from JD (regex for mailto: or "apply to email@company.com" patterns), Subject = "Application for {role} — {name}", Body = cover letter text, Attachment = tailored resume PDF
   - Send via SMTP using profile's configured email credentials
   - On success: update `application.status = "submitted"`, set `submitted_at`

   `async def submit_seek(application, job, profile) -> bool`:
   - Playwright: navigate to job URL
   - Click "Apply" button (selector: `a[data-automation="job-detail-apply"]` or similar — implement selector fallback)
   - Fill form fields: name, email, phone, cover letter textarea, resume upload (use `input[type=file]` to upload the generated PDF)
   - Random delays between field fills (0.5–2 seconds, human-like)
   - Submit form
   - Detect success/failure from URL change or success message
   - On CAPTCHA detected (presence of iframe with `recaptcha` or `hcaptcha` in src): do NOT attempt to solve. Set `application.status = "failed"`, set `notes = "CAPTCHA encountered — manual submission required"`. Log and notify user.

   `async def submit_linkedin_easy_apply(application, job, profile) -> bool`:
   - Playwright with session cookie (same as scraper)
   - Navigate to job URL
   - Click "Easy Apply" button
   - Handle multi-step form: fill each step (contact info, resume upload, cover letter if prompted, screening questions — answer "Yes" to work authorization, leave others blank with a note)
   - Click Next/Submit through all steps
   - On CAPTCHA: same fallback as Seek — flag, do not attempt to solve

   `async def submit_application(application, job, profile) -> bool`:
   - Dispatcher: choose method based on `job.source` and available submission methods
   - Priority: Seek form if source=seek, LinkedIn Easy Apply if source=linkedin, email as fallback for all

2. Rate limiting across all submissions:
   - Max 10 submissions per hour (configurable in settings)
   - Minimum 3-minute gap between any two submissions
   - Random delay 30–120 seconds between submissions within the same source
   - Shuffle submission order

3. `routers/applications.py` additions:
   - `POST /api/applications/{id}/submit` — manually trigger submission for an approved application
   - `GET /api/applications/stats` — counts by status (for dashboard summary cards)

4. Plugin stubs for Workday and Greenhouse in `submission_service.py` — functions that raise `NotImplementedError` and log "Workday/Greenhouse plugin not active in MVP".

**Frontend:**

1. `Dashboard.jsx` — add summary stat cards at top: Jobs Found / In Queue / Submitted / Failed
2. `Queue.jsx` — after approval, show submission status inline (Submitting... / Submitted / Failed with reason)
3. `Log.jsx` — add "Retry" button for failed submissions. Add "Submit manually" for approved-but-not-submitted.
4. `Settings.jsx` — add submission settings: max per hour, min gap minutes, auto-submit toggle (submit immediately on approve, default off).

**Acceptance test:** Approve an application set to email submission. A correctly formatted email with resume attachment is sent. Seek submission: navigates to the listing, fills the form, uploads resume. CAPTCHA scenario: application is marked "failed" with a clear message rather than hanging or crashing.

---

## Key Implementation Notes

### LinkedIn session cookie approach
Do not automate LinkedIn login. Instead, instruct users to:
1. Log into LinkedIn in Chrome
2. Open DevTools (F12) → Application tab → Cookies → `www.linkedin.com`
3. Copy the value of the `li_at` cookie
4. Paste into the LinkedIn cookie field in Settings

This cookie is valid for weeks/months. The app stores it encrypted. Using a real user session bypasses most bot detection. Add a "Cookie expired?" warning if LinkedIn pages return a login redirect.

### Anti-bot measures
- All Playwright browsers: set realistic viewport (1920×1080), disable `navigator.webdriver` flag via `page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")`
- Rotate between 5 real Chrome user-agent strings stored in `scrapers/base.py`
- Random mouse movements before clicking (use `page.mouse.move()` with slight randomisation around the target element)
- Never run more than one Playwright browser instance simultaneously

### AI provider compatibility
The `openai` Python SDK supports any OpenAI-compatible endpoint via `base_url`. Configuration per provider:
- **OpenAI:** `base_url=None`, `api_key=key`
- **Anthropic (Claude):** `base_url="https://api.anthropic.com/v1"`, `api_key=key`, add header `"anthropic-version": "2023-06-01"` via `default_headers`
- **Google Gemini:** `base_url="https://generativelanguage.googleapis.com/v1beta/openai/"`, `api_key=key`
- **Ollama (local/free):** `base_url="http://localhost:11434/v1"`, `api_key="ollama"`
- **Custom:** user-supplied `base_url` and `api_key`

### File storage
- Uploaded files: `backend/uploads/resumes/` and `backend/uploads/cover_letters/`
- Generated tailored resumes: `backend/uploads/generated/{application_id}_resume.pdf`
- Add `backend/uploads/` to `.gitignore`

### Environment variables (`.env`)
```
ENCRYPTION_KEY=<auto-generated 32-byte Fernet key>
DATABASE_URL=sqlite+aiosqlite:///./job_agent.db
```

### CORS
FastAPI CORS middleware must allow: `http://localhost:5173`, methods `["*"]`, headers `["*"]`.

### Error handling
- All scraper failures: log error, continue with next listing (never crash the scheduler)
- All submission failures: set `application.status = "failed"`, store error in `notes`, never retry automatically without user action
- AI API failures: surface error message in the UI, do not silently skip generation

---

## First Run Setup Instructions (include in README.md)

```bash
# 1. Install Python deps
pip install -r requirements.txt
playwright install chromium

# 2. Install Node deps
npm install
cd frontend && npm install && cd ..

# 3. Start both servers
npm run dev

# 4. Open browser
# http://localhost:5173

# 5. Go to Settings:
#    - Add your AI API key (or set up Ollama for free local AI)
#    - Configure scraper keywords and location
#    - (Optional) Add LinkedIn li_at session cookie

# 6. Go to Profile:
#    - Fill in your details
#    - Upload your resume (PDF or DOCX)
#    - Upload 1–2 example cover letters

# 7. Hit "Scrape Now" on the Dashboard
#    - Jobs appear within ~60 seconds
#    - Review them, queue the ones you like
#    - Generated applications appear in the Queue
#    - Approve to submit
```

---

## What's Intentionally Out of Scope for MVP
- User authentication / multi-user support (single-user local app)
- Docker containerisation (add later)
- Cloud hosting / VPS deployment (add after MVP validation)
- Workday, Greenhouse, Lever form-filling (plugin stubs only)
- Glassdoor, LinkedIn Global, Indeed International scraping (toggle stubs only)
- Mobile app or PWA
- Resume builder from scratch (user must upload an existing resume)
