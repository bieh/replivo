# Replivo

AI-powered email response platform for property managers (HOAs, condo associations). Upload governing documents, and Replivo answers tenant questions with verified citations.

## How It Works

1. Admin uploads CC&Rs/bylaws for a community
2. Tenant emails a question to the community inbox (e.g. "Can I paint my house blue?")
3. AI searches the documents, generates a draft reply with exact citations
4. If confident: queued as draft (or auto-sent). If uncertain: escalated to admin.
5. Admin reviews, approves/edits, and sends — all tracked in the portal.

**Core principle: "Not sure" is always acceptable. Wrong information is never acceptable.** The system is biased toward escalation.

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────┐
│  Tenant     │     │           Replivo                     │
│  (email)    │────▶│                                       │
│             │◀────│  Flask API          React Admin UI    │
└─────────────┘     │  ┌─────────┐       ┌──────────────┐  │
                    │  │ Webhook │       │ Dashboard    │  │
┌─────────────┐     │  │ or Poll │       │ Conversations│  │
│  AgentMail  │◀───▶│  └────┬────┘       │ Communities  │  │
│  REST API   │     │       │            │ Playground   │  │
└─────────────┘     │  ┌────▼────────┐   └──────────────┘  │
                    │  │ AI Pipeline │                      │
┌─────────────┐     │  │ Generate    │   ┌──────────────┐  │
│  OpenAI     │◀───▶│  │ Verify      │──▶│ PostgreSQL   │  │
│  GPT-5.2    │     │  │ Escalate    │   │ + pgvector   │  │
└─────────────┘     │  └─────────────┘   └──────────────┘  │
                    └──────────────────────────────────────┘
```

### AI Pipeline (per question)

1. **Retrieve** — Full document context (≤80k tokens) or hybrid RAG (vector + BM25 + Cohere rerank)
2. **Generate** — GPT-5.2 structured output with per-claim citations and source quotes
3. **Verify citations** — Deterministic fuzzy-match of quoted text against actual documents (no LLM)
4. **Verify (LLM)** — Conditional second pass for medium-confidence or flagged citations (~40% of queries)
5. **Escalation gate** — 8 deterministic rules; any trigger → `needs_human`

### Conversation Threading

Follow-up emails on the same thread are matched via `agentmail_thread_id`. The full conversation history is injected into the LLM context so the AI can reference prior Q&A.

### Email Integration (AgentMail REST API)

All email is handled via direct REST calls to `https://api.agentmail.to/v0`:

- **Sending**: `POST /v0/inboxes/{inbox_id}/messages/send`
- **Listing** (poller): `GET /v0/inboxes/{inbox_id}/messages`
- **Reading**: `GET /v0/inboxes/{inbox_id}/messages/{message_id}`

Two intake modes:
- **Webhook** (production): AgentMail POSTs to `/api/webhooks/agentmail` on each inbound email
- **Polling** (development): Background thread polls every 10s — no public URL needed

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python / Flask |
| Frontend | React + TypeScript + Vite + Tailwind CSS v4 |
| Database | PostgreSQL + pgvector |
| ORM / Migrations | SQLAlchemy + Alembic |
| Email | AgentMail REST API |
| AI | OpenAI GPT-5.2 (structured output) |
| Embeddings | OpenAI text-embedding-3-small |
| Reranking | Cohere |
| Auth | Flask sessions + bcrypt |
| Hosting | Railway (Dockerfile) |

## Project Structure

```
replivo/
├── backend/
│   ├── app/
│   │   ├── __init__.py              # Flask app factory, serves frontend in prod
│   │   ├── config.py                # All configuration
│   │   ├── models/                  # SQLAlchemy models
│   │   ├── api/                     # Flask blueprints
│   │   │   ├── auth.py              # Login/logout/session
│   │   │   ├── communities.py       # CRUD
│   │   │   ├── conversations.py     # Review/approve/send
│   │   │   ├── dashboard.py         # Stats
│   │   │   ├── documents.py         # Upload/process
│   │   │   ├── playground.py        # Test questions
│   │   │   ├── tenants.py           # CRUD
│   │   │   ├── citations.py         # Public citation pages
│   │   │   └── webhooks.py          # AgentMail inbound
│   │   └── services/
│   │       ├── ai_service.py        # LLM prompt construction + calls
│   │       ├── pipeline.py          # Full orchestration: retrieve→generate→verify→escalate
│   │       ├── search_service.py    # Hybrid RAG (vector + BM25 + rerank)
│   │       ├── document_service.py  # PDF parsing, chunking, embedding
│   │       ├── email_service.py     # AgentMail REST send
│   │       ├── email_poller.py      # Background polling (dev mode)
│   │       ├── citation_verifier.py # Deterministic quote matching
│   │       └── embedding_service.py # OpenAI embeddings
│   ├── migrations/                  # Alembic
│   ├── requirements.txt
│   └── wsgi.py
├── frontend/
│   └── src/
│       ├── pages/                   # Dashboard, Communities, Conversations, Playground, etc.
│       ├── components/              # Layout, Markdown, StatusBadge
│       ├── api/client.ts            # Axios API client
│       └── types/index.ts
├── cli/                             # Dev/admin CLI tool
├── tests/                           # Thread handling + pipeline tests
├── samples/                         # Sample CC&R PDFs
├── Dockerfile                       # Multi-stage: Node (frontend) + Python (backend)
├── railway.toml                     # Railway deployment config
└── run.sh                           # Local dev: starts backend + frontend
```

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL with pgvector extension

### Setup

```bash
# Clone
git clone git@github.com:bieh/replivo.git
cd replivo

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Database
createdb replivo
cd backend && flask db upgrade && cd ..

# Environment
cp .env.example .env  # fill in API keys

# Seed data
python -m cli seed --with-documents

# Run
./run.sh  # starts Flask on :5000 + Vite on :5173
```

### Environment Variables

```bash
DATABASE_URL=postgresql://user@localhost/replivo
OPENAI_API_KEY=sk-...
AGENTMAIL_API_KEY=...
COHERE_API_KEY=...
FLASK_SECRET_KEY=change-me
FLASK_ENV=development
EMAIL_INTAKE_MODE=poll          # poll for dev, webhook for prod
FRONTEND_URL=http://localhost:5173
```

### CLI

```bash
python -m cli seed                    # Seed org, admin, communities, tenants
python -m cli seed --with-documents   # + ingest sample PDFs
python -m cli ask timber-ridge "Can I paint my house blue?"
python -m cli simulate-email --from carol@example.com --subject "Fence" --body "How tall?"
python -m cli test                    # Run grounding test suite
python -m cli test --verbose          # Show full AI responses
```

## Deployment (Railway)

The app deploys as a single Railway service using a multi-stage Dockerfile:
1. **Stage 1** (Node 20): Builds the React frontend → `frontend/dist/`
2. **Stage 2** (Python 3.12): Installs backend deps, copies frontend build, runs gunicorn

Flask serves both the API (`/api/*`) and the React SPA from the same process.

### Railway Setup

1. Create a new project on Railway
2. Add a PostgreSQL service (with pgvector — Railway supports it)
3. Connect the GitHub repo
4. Set environment variables:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Provided by Railway Postgres |
| `OPENAI_API_KEY` | Your key |
| `AGENTMAIL_API_KEY` | Your key |
| `COHERE_API_KEY` | Your key |
| `FLASK_SECRET_KEY` | Random string |
| `FLASK_ENV` | `production` |
| `EMAIL_INTAKE_MODE` | `webhook` |
| `FRONTEND_URL` | Your Railway public URL |
| `AGENTMAIL_WEBHOOK_SECRET` | From AgentMail dashboard (optional) |

5. Configure AgentMail webhook → `https://your-app.up.railway.app/api/webhooks/agentmail`
6. Add a Railway domain or custom domain
7. Deploy — Railway auto-builds on push to `main`

### DB Migrations

Migrations run automatically on deploy via the start command in `railway.toml`:
```
flask db upgrade && gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2
```

After first deploy, seed the database:
```bash
railway run python -m cli seed --with-documents
```

## API Overview

| Endpoint | Description |
|---|---|
| `POST /api/auth/login` | Login (username/password) |
| `GET /api/auth/me` | Current user |
| `GET /api/dashboard/stats` | Dashboard counts |
| `GET/POST /api/communities` | List/create communities |
| `GET/PUT/DELETE /api/communities/:id` | Community CRUD |
| `GET/POST /api/communities/:id/tenants` | Tenant management |
| `GET/POST /api/communities/:id/documents` | Document upload/list |
| `GET /api/conversations` | List (filterable by status/community) |
| `GET /api/conversations/:id` | Conversation + messages |
| `POST /api/conversations/:id/approve` | Approve AI draft → send |
| `POST /api/conversations/:id/edit-and-send` | Edit draft → send |
| `POST /api/conversations/:id/reply` | Manual reply |
| `POST /api/conversations/:id/close` | Close conversation |
| `POST /api/playground/ask` | Test questions against a community |
| `GET /api/citations/:token` | Public citation data |
| `POST /api/webhooks/agentmail` | Inbound email webhook |
