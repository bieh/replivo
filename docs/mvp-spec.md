# Replivo MVP Specification

## Overview

Replivo is an AI-powered email response platform for property managers (HOAs, condo associations). Property managers upload their governing documents (CC&Rs, bylaws, lease agreements), and when tenants email in with questions, the system searches the relevant documents and generates accurate replies with citations.

## Core User Flow

1. **Admin** logs in, creates a community, uploads governing documents
2. **Admin** adds tenants (name, email, unit) linked to that community
3. **Tenant** emails a question to the Replivo inbox (e.g. "Can I paint my front door red?")
4. **System** identifies the tenant by email, finds their community's documents, searches for relevant clauses
5. **System** generates a draft reply with citations to specific document sections
6. If confident answer found → queued as **draft** for admin review (auto-send is a future option)
7. If no reliable answer found → flagged as **needs human response**
8. **Admin** reviews drafts in the portal: approve, edit & send, or write their own reply
9. All conversations are tracked and visible in the admin portal

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python / Flask |
| **Frontend** | React (Vite + TypeScript) |
| **Database** | PostgreSQL (local dev, Railway for prod) |
| **ORM** | SQLAlchemy |
| **Migrations** | Alembic |
| **Email** | AgentMail (inbound webhooks + outbound API) |
| **AI / LLM** | OpenAI (GPT-5.2) |
| **Embeddings** | OpenAI text-embedding-3-small |
| **Vector Search** | pgvector (PostgreSQL extension) |
| **Document Parsing** | PyPDF2 / pdfplumber for PDF, plain text direct |
| **Auth** | Simple username/password, Flask sessions, bcrypt |
| **Hosting** | Railway (backend + Postgres + frontend) |

---

## Database Schema

Designed for future multi-tenancy. MVP seeds a single organization.

```
organizations
├── id (uuid, pk)
├── name (varchar)
├── slug (varchar, unique)
├── settings (jsonb)          -- tone preferences, auto-send config, etc.
├── created_at (timestamp)
└── updated_at (timestamp)

users (admin users)
├── id (uuid, pk)
├── organization_id (uuid, fk → organizations)
├── email (varchar, unique)
├── username (varchar, unique)
├── password_hash (varchar)
├── role (varchar)            -- 'owner', 'admin', 'viewer'
├── created_at (timestamp)
└── updated_at (timestamp)

communities
├── id (uuid, pk)
├── organization_id (uuid, fk → organizations)
├── name (varchar)            -- e.g. "Pinecrest HOA"
├── inbox_email (varchar)     -- AgentMail inbox address
├── agentmail_inbox_id (varchar)
├── settings (jsonb)
├── created_at (timestamp)
└── updated_at (timestamp)

tenants
├── id (uuid, pk)
├── community_id (uuid, fk → communities)
├── name (varchar)
├── email (varchar)
├── unit (varchar)            -- e.g. "10A", "Unit 205"
├── is_active (boolean, default true)
├── created_at (timestamp)
└── updated_at (timestamp)
│   unique(community_id, email)

documents
├── id (uuid, pk)
├── community_id (uuid, fk → communities)
├── filename (varchar)
├── file_type (varchar)       -- 'pdf', 'txt'
├── file_path (varchar)       -- storage path
├── file_size (integer)
├── total_pages (integer, nullable)
├── total_chunks (integer)
├── status (varchar)          -- 'processing', 'ready', 'error'
├── created_at (timestamp)
└── updated_at (timestamp)

document_chunks
├── id (uuid, pk)
├── document_id (uuid, fk → documents)
├── chunk_index (integer)
├── content (text)
├── page_number (integer, nullable)
├── token_count (integer)
├── embedding (vector(1536))  -- pgvector
├── created_at (timestamp)
│   index on embedding using ivfflat (vector_cosine_ops)

conversations
├── id (uuid, pk)
├── community_id (uuid, fk → communities)
├── tenant_id (uuid, fk → tenants, nullable)  -- null if unknown sender
├── agentmail_thread_id (varchar, nullable)
├── subject (varchar)
├── status (varchar)          -- 'pending_review', 'draft_ready', 'needs_human', 'auto_replied', 'replied', 'closed'
├── sender_email (varchar)
├── created_at (timestamp)
└── updated_at (timestamp)

messages
├── id (uuid, pk)
├── conversation_id (uuid, fk → conversations)
├── agentmail_message_id (varchar, nullable)
├── direction (varchar)       -- 'inbound', 'outbound'
├── from_email (varchar)
├── to_email (varchar)
├── subject (varchar)
├── body_text (text)
├── body_html (text, nullable)
├── citations (jsonb, nullable)  -- [{document_id, chunk_id, page, excerpt}]
├── is_ai_generated (boolean, default false)
├── sent_at (timestamp, nullable)
├── created_at (timestamp)
└── updated_at (timestamp)
```

### Indexes
- `document_chunks.embedding` — IVFFlat index for vector similarity search
- `tenants(community_id, email)` — unique, for fast tenant lookup on inbound email
- `conversations(community_id, status)` — for admin dashboard filtering
- `conversations(sender_email)` — for matching inbound emails

---

## AI Pipeline

### Core Philosophy

**"Not sure" is always acceptable. Wrong information is never acceptable.**

The system is biased toward escalation. If there's any doubt, flag for human review. A property manager would rather answer a question themselves than have the AI give a tenant incorrect information about their legal obligations.

### Document Ingestion (Structure-Aware)
1. Admin uploads PDF or .txt file for a community
2. Backend extracts text (pdfplumber for PDF, direct read for .txt)
3. Text is split into chunks **by section/article boundaries** (not fixed-size):
   - Each CC&R section (e.g., "Section 7.6 ANIMALS") = 1 chunk
   - Max 512 tokens per chunk; oversized sections split at paragraph
   - No overlap (sections are self-contained legal units)
   - Tiny sections (<50 tokens) merged with parent
4. Each chunk gets **hierarchical metadata**: article_number, article_title, section_group, section_number, page_number
5. Each chunk is embedded via OpenAI `text-embedding-3-small`
6. Each chunk gets a `tsvector` for BM25 full-text search
7. Full document text also stored separately (for full-context mode)
8. Document status set to `ready`

Three parsing strategies for different CC&R styles:
- `Section NNN.` pattern (Gleneagle style)
- Roman numeral articles with lettered subsections (Timber Ridge style)
- Numbered articles with decimal sections (Mission Street style: `7.6 ANIMALS.`)

### Context Strategy: Full vs RAG
1. Calculate total token count of all documents for the community
2. **If total ≤ 80,000 tokens** → "full context" mode: pass ALL document text to LLM (most accurate, eliminates retrieval errors)
3. **If total > 80,000 tokens** → "RAG" mode with hybrid retrieval

### RAG Retrieval (when needed)
1. **Query expansion** (rule-based, no LLM): synonym mapping for common HOA terms (pet→animal/dog/cat, fence→fencing/wall, etc.)
2. **Hybrid search**: pgvector cosine similarity + PostgreSQL BM25 (`tsvector`)
3. **Reciprocal Rank Fusion** (k=60): merge vector + BM25 rankings
4. **Cohere Rerank**: cross-encoder reranking of top 15 → return top 8
5. **Context assembly**: chunks ordered by document position (preserves logical flow)

### Response Generation (2-pass pipeline)

**LLM Call #1 — Generate (always runs):**
1. Inbound email arrives, tenant + community identified
2. Retrieve document context (full or RAG)
3. GPT-5.2 with **structured JSON output** (OpenAI `response_format` with strict schema)
4. System prompt enforces:
   - Every factual claim must include a citation with exact source quote
   - Never state anything not in the documents
   - If answer not in docs, say so — do NOT guess
   - Distinguish "explicitly prohibited" from "not addressed" (never say "since it's not mentioned, it's allowed")
   - Chain-of-thought reasoning (internal, not shown to tenant)
5. Output: `claims[]` with `source_quote`, `section_reference`, `confidence` per claim, plus `answer_type`, `overall_confidence`, `should_escalate`

**Deterministic Citation Verifier (between LLM calls, no LLM):**
- For each claim, fuzzy-match `source_quote` against actual document text
- Flag any quote that doesn't appear in the source (match threshold: 85%)
- This catches the LLM fabricating or misquoting document text

**LLM Call #2 — Verify (conditional, ~40% of queries):**
- Only fires when: unverified citations, MEDIUM confidence, or PARTIAL answer
- Focused re-check of flagged claims against source documents
- Can remove unsupported claims, downgrade confidence, trigger escalation
- Skipped entirely when Call #1 produces HIGH confidence + all citations verified

**Escalation Gate (deterministic, 8 rules — any = escalate):**
1. Model says `should_escalate: true`
2. `answer_type` is `NOT_IN_DOCUMENTS`
3. `overall_confidence` is `LOW`
4. `answer_type` is `REQUIRES_INTERPRETATION`
5. Any claim has unverified citation after verification pass
6. Any individual claim has `LOW` confidence
7. `answer_type` is `AMBIGUOUS`
8. Zero claims but non-empty answer (no citations backing it)

**Result:**
- All rules pass → `draft_ready`
- Any rule fires → `needs_human` (admin gets escalation package: question, AI's best attempt, relevant sections found, reasoning)

### Auto-Reply Mode (per community toggle)

Each community has an `auto_reply_enabled` setting:
- **ON** + `draft_ready` → AI sends the reply automatically via AgentMail. Status = `auto_replied`. Logged in conversations.
- **ON** + `needs_human` → queued for admin review (never auto-sends uncertain answers)
- **OFF** → everything goes to draft queue, admin reviews and sends manually

Demo communities seeded with auto-reply **ON**. Production default: **OFF**.

Toggle lives in Community Detail → Settings tab.

### Cost per Question
- Full context mode (most queries): ~$0.09 avg
- RAG mode: ~$0.04 avg
- At 1,000 emails/month: ~$40-90/month total AI costs

---

## Email Integration (AgentMail)

### Setup
- One AgentMail inbox per community (e.g. `pinecrest@agentmail.to`)
- MVP: single test inbox (`replivo@agentmail.to`)
- Two intake modes (same processing pipeline behind both):

#### Production: Webhooks
- Webhook registered pointing to `POST /api/webhooks/agentmail`
- Webhook verified via Svix signature
- Real-time push — email arrives, webhook fires, we process

#### Development: Polling
- Background thread polls AgentMail `messages.list()` on an interval (every 10s)
- Tracks last-seen message timestamp to avoid reprocessing
- No public URL needed — works on localhost
- Enabled when `FLASK_ENV=development` or `EMAIL_INTAKE_MODE=poll`

#### Intake mode selection
```python
# config.py
EMAIL_INTAKE_MODE = os.getenv("EMAIL_INTAKE_MODE", "poll" if FLASK_ENV == "development" else "webhook")
```

### Inbound Flow (shared pipeline)
```
Email arrives at AgentMail inbox
  → Intake layer receives it (webhook push OR poll pickup)
  → process_inbound_email(message) is called either way
  → Match sender email to tenant
  → Run AI pipeline
  → Store conversation + draft
```

### Outbound Flow
```
Admin approves/edits draft in portal
  → Backend calls AgentMail reply API
  → Message sent from community inbox
  → Status updated to 'replied'
```

### Webhook Verification
All inbound webhooks verified using Svix signature verification:
```python
from svix.webhooks import Webhook
wh = Webhook(secret)
wh.verify(payload, headers)  # raises on invalid
```

---

## API Endpoints

### Auth
```
POST /api/auth/login          — { username, password } → { token/session }
POST /api/auth/logout         — clear session
GET  /api/auth/me             — current user info
```

### Communities
```
GET    /api/communities                — list communities for org
POST   /api/communities               — create community
GET    /api/communities/:id            — get community details
PUT    /api/communities/:id            — update community
DELETE /api/communities/:id            — delete community
```

### Tenants
```
GET    /api/communities/:id/tenants         — list tenants
POST   /api/communities/:id/tenants         — add tenant
PUT    /api/communities/:id/tenants/:tid    — update tenant
DELETE /api/communities/:id/tenants/:tid    — remove tenant
```

### Documents
```
GET    /api/communities/:id/documents       — list documents
POST   /api/communities/:id/documents       — upload document (multipart)
GET    /api/communities/:id/documents/:did  — document details + chunk count
DELETE /api/communities/:id/documents/:did  — delete document + chunks
```

### Conversations
```
GET    /api/conversations                          — list all (filterable by status, community)
GET    /api/conversations/:id                      — get conversation + messages
POST   /api/conversations/:id/approve              — approve AI draft, send it
POST   /api/conversations/:id/edit-and-send        — edit draft body, then send
POST   /api/conversations/:id/reply                — write manual reply (for needs_human)
POST   /api/conversations/:id/close                — close without replying
```

### Webhooks (AgentMail callback)
```
POST   /api/webhooks/agentmail    — receives inbound email events
```

### Dashboard
```
GET    /api/dashboard/stats    — counts by status, recent activity
```

---

## Frontend Pages

### Auth
- **Login** — `/login`

### Dashboard
- **Home** — `/` — overview stats, recent conversations needing attention

### Communities
- **Community List** — `/communities`
- **Community Detail** — `/communities/:id` — tabs for tenants, documents, settings

### Tenants
- Managed within Community Detail page (inline table, add/edit modal)

### Documents
- Managed within Community Detail page (upload area, list with status indicators)

### Conversations
- **Conversation List** — `/conversations` — filterable by status, community
- **Conversation Detail** — `/conversations/:id` — full thread view, draft editor, approve/send actions

### Settings (stub)
- **Org Settings** — `/settings` — response tone selector (UI present but disabled for MVP, placeholder for 3-tone feature)

---

## MVP Scope Boundaries

### In Scope
- Single organization, seeded in DB ("Jason's Property Management")
- Multiple communities under that org (3 sample communities seeded)
- Admin auth (username/password, session-based)
- Community CRUD
- Tenant CRUD
- Document upload + processing (PDF, plain text)
- Hybrid RAG (full-context for small doc sets, embedding search for large)
- Inbound email via AgentMail webhook
- AI-generated draft responses with citations
- Admin review queue (approve / edit+send / manual reply)
- Outbound email via AgentMail
- Conversation tracking
- Basic dashboard stats
- CLI tool for dev/testing/admin
- Grounding test suite (42 test cases across 3 communities)

### Out of Scope (Future)
- Multi-org / multi-tenant SaaS (DB is designed for it, UI is not)
- Self-registration / sign-up flow
- Billing / payments / subscriptions
- Auto-send as org-wide default (currently per-community toggle)
- Multiple response tones (UI stub only)
- WhatsApp / SMS channels
- CRM integration / embeddable API
- Custom domains for email
- File storage service (MVP: local filesystem; future: S3)
- Tenant-facing portal / accounts
- Email threading beyond single Q&A (multi-turn conversations)

---

## CLI Tool

A command-line interface for development, testing, and admin tasks. Runs via `python -m cli` from the project root.

### Commands

```bash
# --- Setup & Seeding ---
cli seed                              # Create default org, admin user, sample communities + tenants
cli seed --with-documents             # Also ingest the sample CC&R PDFs from /samples/

# --- Document Management ---
cli ingest <community-slug> <file>    # Ingest a PDF/txt into a community
cli ingest timber-ridge samples/timber-ridge-ccr.pdf
cli communities                       # List all communities with doc/tenant counts
cli documents <community-slug>        # List documents + chunk counts for a community

# --- Ask Questions (core testing) ---
cli ask <community-slug> "question"   # Run the full AI pipeline and print the response
cli ask timber-ridge "Can I paint my house blue?"
cli ask --email carol@example.com "How tall can my fence be?"  # Simulate as specific tenant
cli ask --raw timber-ridge "question" # Show raw LLM prompt + response (debug mode)

# --- Email Simulation ---
cli simulate-email --from carol@example.com --to replivo@agentmail.to --subject "Fence question" --body "How tall can my fence be?"
                                      # Simulate full inbound email pipeline without AgentMail

# --- Test Suite ---
cli test                              # Run full grounding test suite
cli test --category answerable        # Only answerable questions
cli test --category unanswerable      # Only unanswerable (hallucination traps)
cli test --category cross_community   # Only cross-community isolation tests
cli test --community timber-ridge     # Only questions for one community
cli test --verbose                    # Show full AI responses

# --- Conversations ---
cli conversations                     # List recent conversations with status
cli conversation <id>                 # Show full conversation thread
```

### Test Output Format
```
Running 42 test cases...

ANSWERABLE TESTS:
  ✓ [mission-street] "Can I have a dog in my unit?" — cited Section 7.6 ✓
  ✓ [timber-ridge] "Can I paint my house bright blue?" — cited Article VIII.I ✓
  ✗ [gleneagle] "How many pets can I have?" — MISSING expected keyword "two"

UNANSWERABLE TESTS (hallucination traps):
  ✓ [mission-street] "What are the pool hours?" — correctly flagged as unanswerable ✓
  ✗ [timber-ridge] "What is the speed limit?" — HALLUCINATED an answer (said "25 mph")

CROSS-COMMUNITY ISOLATION:
  ✓ [timber-ridge] "Parking stacker rules?" — correctly flagged (Mission St concept) ✓
  ✗ [mission-street] "Can I keep horses?" — LEAKED Timber Ridge content

RESULTS: 38/42 passed (90.5%)
  Answerable:       25/27 (92.6%)
  Unanswerable:     10/11 (90.9%) ← CRITICAL: any failure here is a hallucination
  Cross-community:   3/4  (75.0%)
```

---

## Test Suite Design

### Grounding Principles

The #1 priority of Replivo is **never lie**. The test suite is designed to catch hallucination:

1. **Answerable tests** — questions whose answers ARE in the docs. Validates:
   - Response contains expected keywords from the actual document
   - Response cites the correct article/section
   - Response is marked `draft_ready` (not `needs_human`)

2. **Unanswerable tests** — questions whose answers are NOT in the docs. Validates:
   - AI explicitly says it cannot find the answer in the documents
   - Response is marked `needs_human`
   - Response does NOT contain fabricated information
   - These are the most critical tests — any failure is a hallucination bug

3. **Cross-community isolation tests** — questions about topics that exist in a DIFFERENT community's docs. Validates:
   - AI does not leak information from other communities
   - Each community's AI only sees its own documents

4. **Unknown sender tests** — emails from addresses not in the tenant database. Validates:
   - System flags as unknown sender
   - Does not attempt to answer

### Test Data

Three communities under one org ("Jason's Property Management"):

| Community | Document | Pages | Type |
|-----------|----------|-------|------|
| Mission Street Condos | `samples/mission-street-ccr.pdf` | ~38 | SF condo, mixed-use, parking stackers |
| Timber Ridge HOA | `samples/timber-ridge-ccr.pdf` | ~18 | Rural CO subdivision, horses, fire zones |
| Gleneagle Estates | `samples/gleneagle-ccr.pdf` | ~15 | CO suburban, strict architectural style |

Test fixtures defined in `tests/test_fixtures.py`.

---

## Project Structure

```
replivo/
├── docs/
│   ├── spec.pdf
│   └── mvp-spec.md
├── samples/                             — sample CC&R documents for testing
│   ├── mission-street-ccr.pdf
│   ├── timber-ridge-ccr.pdf
│   └── gleneagle-ccr.pdf
├── tests/
│   └── test_fixtures.py                 — test communities, tenants, questions
├── cli/                                 — CLI tool
│   ├── __init__.py
│   └── commands.py
├── backend/
│   ├── app/
│   │   ├── __init__.py          — Flask app factory
│   │   ├── config.py            — configuration
│   │   ├── extensions.py        — db, migrate, etc.
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── organization.py
│   │   │   ├── user.py
│   │   │   ├── community.py
│   │   │   ├── tenant.py
│   │   │   ├── document.py
│   │   │   ├── conversation.py
│   │   │   └── message.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── communities.py
│   │   │   ├── tenants.py
│   │   │   ├── documents.py
│   │   │   ├── conversations.py
│   │   │   ├── webhooks.py
│   │   │   └── dashboard.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ai_service.py       — LLM calls, prompt construction
│   │   │   ├── document_service.py  — parsing, chunking, embedding
│   │   │   ├── email_service.py     — AgentMail integration (send/receive)
│   │   │   ├── email_poller.py      — background polling for dev mode
│   │   │   └── search_service.py    — vector search + hybrid logic
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── text.py              — chunking, token counting
│   ├── migrations/                  — Alembic
│   ├── tests/
│   ├── requirements.txt
│   └── wsgi.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── api/                     — API client
│   │   ├── hooks/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── run.sh                               — start backend + frontend dev servers
├── deploy.sh                            — Railway deployment
├── .env
├── .gitignore
└── README.md
```

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/replivo

# AgentMail
AGENTMAIL_API_KEY=
AGENTMAIL_WEBHOOK_SECRET=

# OpenAI
OPENAI_API_KEY=

# Flask
FLASK_SECRET_KEY=
FLASK_ENV=development

# Email intake mode (auto-detected from FLASK_ENV if not set)
# EMAIL_INTAKE_MODE=poll    # 'poll' for dev (no public URL needed), 'webhook' for prod

# Frontend
VITE_API_URL=http://localhost:5000/api
```

---

## Development Milestones

### M1: Foundation
- Project scaffolding (Flask + React + CLI)
- Database models + migrations (multi-org/multi-community schema)
- Auth (login/logout/session)
- Seed script: "Jason's Property Management" org, admin user, 3 communities, sample tenants
- CLI framework (`cli seed`, `cli communities`)

### M2: Document Pipeline
- Document upload endpoint
- PDF/text parsing + chunking
- Embedding generation + storage (pgvector)
- Hybrid context detection (full-context vs RAG)
- CLI: `cli ingest`, `cli documents`

### M3: AI Response Engine
- System prompt construction with grounding instructions
- Full-context vs RAG retrieval
- Draft generation with citations
- Confidence/escalation detection ("answerable" vs "needs_human")
- CLI: `cli ask`

### M4: Test Suite
- Wire up `tests/test_fixtures.py` with CLI test runner
- Run answerable / unanswerable / cross-community / unknown-sender tests
- CLI: `cli test` with all flags
- Iterate on system prompt until hallucination rate is 0%

### M5: Email Integration
- AgentMail inbox setup
- Webhook endpoint + dev polling mode
- Outbound reply via AgentMail API
- Tenant identification from sender email
- CLI: `cli simulate-email`

### M6: Community & Tenant Management UI
- Community CRUD API + UI
- Tenant CRUD API + UI
- Document upload UI with status indicators

### M7: Conversation Management UI
- Conversation list + detail UI
- Draft review/approve/edit flow
- Manual reply for escalated conversations
- Dashboard stats

### M8: Polish & Deploy
- Error handling + edge cases
- Railway deployment config
- Environment variable management
- Response tone UI stub (disabled)
