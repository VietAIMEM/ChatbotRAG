# Chatbot RAG

I am using this project to implement a chatbot for postgraduate studies, but it is customizable; you can adjust the settings to tailor the Q&A functionality to your specific needs.

CI CD

A production-ready **RAG chatbot web application** for postgraduate (Thạc sĩ) information. Visitors chat without logging in and get answers **grounded only in documents uploaded by an administrator** — no free-form hallucination. An admin dashboard manages documents, LLM providers, RAG tuning, conversations, system logs and settings.

Built with **Next.js (App Router) + FastAPI + PostgreSQL + Qdrant**, orchestrated with **Docker Compose**.

---
## Review
<img width="1352" height="628" alt="image" src="https://github.com/user-attachments/assets/577c8b22-28eb-44ae-850c-cc2c39f6c79a" />
<img width="1356" height="284" alt="image" src="https://github.com/user-attachments/assets/09f604aa-f36a-4856-8734-de08f1c25461" />

---


## Features

**Public chat**
- SSE streaming chat (`POST /api/chat/stream`) with a `start / delta / done / error` event protocol.
- Conversation memory (last 8 messages), client-side conversation history stored in `localStorage`.
- **Domain gate** — questions unrelated to postgraduate education are politely rejected without touching RAG/LLM.
- **Query rewrite** (heuristic) for follow-up questions.
- Grounded answers cite the source documents (clickable citation links + source cards).

**Admin dashboard** (`/admin`)
- Dashboard with document/conversation/RAG activity statistics and recent logs.
- **Documents** — upload (PDF, DOC, DOCX, TXT, MD), metadata editing, replace/re-index/delete, activate/deactivate, search & status filter. Indexing runs in the background.
- **Automatic metadata extraction** — on file selection (or via "Re-extract Metadata") the backend analyzes the file deterministically (file metadata → filename → headings → regex year/version → language detection → category keywords) and optionally uses an LLM to fill gaps, returning per-field confidence (`POST /api/admin/documents/extract-metadata`, no save). Results populate the upload/edit form with confidence indicators (High / Medium / Review) for admin review; docs can be saved as **DRAFT** (no indexing) until reviewed, or "Save & Index" immediately. Categories, departments and programs are configurable under Settings → Metadata Extraction.
- **LLM Providers** — configure multiple chat-completion providers with priority-based fallback. API keys are encrypted (Fernet derived from `SECRET_KEY`) and never exposed.
- **RAG Settings** — embedding provider/model, reranker, chunk size/overlap, `top_k`/`final_k`, similarity threshold, query-rewrite and reranker toggles.
- **Conversations** — browse public conversations, view messages and their sources, delete.
- **System Logs** — searchable audit trail of RAG requests, latency, LLM provider/model used, errors.
- **Settings** — site/chatbot branding, chat rate limit, max upload size, and admin password change.

**RAG pipeline**
- Document ingestion: parse → clean → chunk → embed → upsert into Qdrant, with status tracking (`UPLOADING → PROCESSING → CHUNKING → EMBEDDING → INDEXING → INDEXED | FAILED`).
- Offline defaults: **local hash embedding** (768-dim) and **local lexical reranker** — no API key required to run out of the box.
- Optional external embeddings (`text-embedding-3-small`, `text-embedding-3-large`, `bge-m3`) and rerankers (cross-encoder, Cohere `rerank-v3.5`).
- Retrieval: vector search → threshold filter → lexical rerank → top-K selection → grounded prompt.

---

## Tech Stack

| Layer     | Technology                                                                 |
|-----------|----------------------------------------------------------------------------|
| Frontend  | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, lucide-react, react-markdown |
| Backend   | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2           |
| Vector DB | Qdrant (collection `postgraduate_documents`, 768-dim by default)           |
| Database  | PostgreSQL 16                                                              |
| Auth      | JWT (HttpOnly cookie `admin_token`), bcrypt password hashing               |
| Infra     | Docker Compose (frontend, backend, postgres, qdrant)                       |

---

## Prerequisites

- Docker 24+ with Docker Compose v2 (`docker compose`), or:
  - Node.js 20+ and npm for the frontend
  - Python 3.12+ and a virtualenv for the backend

---

## Quick Start (Docker)

1. Create the environment file:

   ```bash
   cp .env.example .env
   ```

2. **Set a strong `SECRET_KEY` and an initial `ADMIN_PASSWORD`** in `.env` (the first admin account is created automatically on startup).

3. Start the stack:

   ```bash
   docker compose up -d --build
   ```

4. Open the app:

   | Service                | URL                        |
   |------------------------|----------------------------|
   | Public chat            | http://localhost:3000      |
   | Admin dashboard        | http://localhost:3000/admin |
   | API docs (Swagger UI)  | http://localhost:8000/docs |
   | Qdrant dashboard       | http://localhost:6333/dashboard |

5. Log in to `/admin` with `ADMIN_USERNAME` / `ADMIN_PASSWORD`, then:
   - **Documents → Upload Document** to seed the knowledge base.
   - **LLM Providers → Add Provider** (or set `OPENROUTER_API_KEY`) so the assistant can generate answers.

Stop everything with `docker compose down` (add `-v` to also delete volumes).

---

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

# PostgreSQL and Qdrant must be running; set DATABASE_URL and QDRANT_URL in backend/.env
alembic upgrade head

# create the admin account (idempotent)
set ADMIN_PASSWORD=admin12345    # Windows   (Linux/macOS: export ADMIN_PASSWORD=admin12345)
python -m app.create_admin

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000  (proxies /api/* to http://localhost:8000)
```

---

## Environment Variables

All variables are documented in `.env.example`. Key ones:

| Variable                        | Default                              | Description                                                  |
|---------------------------------|--------------------------------------|--------------------------------------------------------------|
| `SECRET_KEY`                    | `change-me...`                       | JWT signing + Fernet encryption key. **Change in production.** |
| `POSTGRES_USER/PASSWORD/DB`     | `postgres` / `postgres` / `postgraduate_rag` | Postgres credentials.                            |
| `QDRANT_COLLECTION`             | `postgraduate_documents`             | Qdrant collection name.                                      |
| `INTERNAL_API_URL`              | `http://backend:8000`                | URL the Next.js server proxies `/api/*` to (Docker only).    |
| `ADMIN_USERNAME`                | `admin`                              | Initial admin username (bootstrap only).                     |
| `ADMIN_PASSWORD`                | *(empty)*                            | If set, creates/updates the admin account on backend startup. |
| `MAX_UPLOAD_SIZE_MB`            | `20`                                 | Max upload size.                                             |
| `CHAT_RATE_LIMIT_PER_MINUTE`    | `30`                                 | Public chat rate limit per IP.                               |
| `OPENROUTER_API_KEY`            | *(empty)*                            | Optional default OpenRouter key.                             |
| `EMBEDDING_MODEL`               | `hash-bge-m3-v1`                     | Default embedding model.                                     |
| `RERANKER_MODEL`                | `lexical`                            | Default reranker.                                            |

> RAG and security values are overridable at runtime from **Admin → RAG Settings** and **Admin → Settings** (stored in the database).

---

## LLM Providers

Chat generation requires at least one enabled LLM provider, configured under **Admin → LLM Providers**.

Supported provider types:

| Type                | Notes                                                        |
|---------------------|--------------------------------------------------------------|
| `openrouter`        | OpenRouter-compatible chat completions.                      |
| `openai_compatible` | Any OpenAI-compatible `/chat/completions` API.               |
| `opencode`          | Self-hosted OpenAI-compatible endpoint (e.g. an opencode gateway). |
| `custom`            | Fully custom base URL/model.                                 |

Providers are tried in ascending `priority` order; if one fails, the next enabled provider is used automatically (fallback chain). API keys are encrypted at rest and returned to the frontend only as a masked hint.

**Test a provider** with the *Test* button (calls `/api/admin/llm-providers/{id}/test`).

---

## RAG Configuration

| Setting                  | Default           | Notes                                        |
|--------------------------|-------------------|----------------------------------------------|
| Embedding provider       | `local`           | Offline hash embedding, no key needed.       |
| Embedding model          | `hash-bge-m3-v1`  | `text-embedding-3-small`, `text-embedding-3-large`, `bge-m3` via compatible API. |
| Reranker provider/model  | `local` / `lexical` | `cross-encoder/ms-marco-MiniLM-L-6-v2`, `rerank-v3.5`. |
| Chunk size / overlap     | `800` / `150`     | Tokens. `overlap < size`.                    |
| Top K / final K          | `10` / `5`        | `final_k <= top_k`.                          |
| Similarity threshold     | `0.35`            | Below this, chunks are discarded.            |
| Query rewrite / reranker | `on` / `on`       | Toggles.                                     |

> Changing embedding model/size requires **re-indexing** documents (Documents → re-index) — existing vectors are sized to the previous model.

---

## Document Ingestion

Supported formats: **`.pdf`, `.doc`, `.docx`, `.txt`, `.md`**. Unsupported types (`.pptx`, `.xlsx`, …) are rejected with a clear message.

- `.doc` files are converted via `antiword` (installed in the backend image).
- Uploads are stored under `storage/documents` (volume `document_storage`) and served via `/api/documents/{id}/download` and `/api/documents/{id}/view`.
- Indexing runs as an in-process background task. Document status is visible in the Documents table.
- *Replace* removes the old file, its vectors and records before indexing the new file.

---

## Testing

```bash
# Backend (uses an in-memory SQLite DB and mocks Qdrant)
cd backend
pytest -q          # 28 tests: auth, documents, chat SSE, RAG pipeline

# Frontend
cd frontend
npm run build      # type-check + production build
```

---

## Project Structure

```
project/
├─ docker-compose.yml          # frontend, backend, postgres, qdrant
├─ .env.example                # environment template
├─ backend/
│  ├─ app/
│  │  ├─ main.py               # FastAPI app + lifespan DB wait
│  │  ├─ api/                  # REST & admin routers, auth deps, rate limiting
│  │  ├─ core/                 # config, security (JWT/Fernet), database, logging
│  │  ├─ models/               # SQLAlchemy models (admin, document, conversation, llm, rag, system_log)
│  │  ├─ schemas/              # Pydantic schemas
│  │  ├─ services/             # chat, conversation, document, settings, llm gateway, logs
│  │  ├─ rag/                  # embeddings, rerankers, vector store, retrieval, prompts, pipeline
│  │  ├─ document_processing/  # parser, cleaner, chunker, indexer
│  │  └─ create_admin.py       # idempotent admin bootstrap
│  ├─ migrations/              # Alembic
│  ├─ tests/                   # pytest suite
│  └─ entrypoint.sh            # wait-for-db → migrate → bootstrap admin → uvicorn
└─ frontend/
   ├─ app/                     # public chat (/) + admin pages (/admin/*)
   ├─ components/              # ui primitives, chat, admin
   ├─ hooks/                   # use-chat (SSE), use-admin-auth
   ├─ lib/                     # api client, storage, utils
   └─ types/                   # shared TypeScript interfaces
```

---

## API Overview

Base path: `/api`

| Method | Path                              | Auth    | Description                          |
|--------|-----------------------------------|---------|--------------------------------------|
| POST   | `/chat/stream`                    | Public  | SSE chat turn (rate limited)         |
| GET    | `/public-settings`                | Public  | Site/chatbot name + welcome message  |
| GET    | `/conversations?client_id=`       | Public  | List own conversations               |
| GET    | `/conversations/{session_id}`     | Public  | Conversation detail (own)            |
| DELETE | `/conversations/{session_id}`     | Public  | Delete own conversation              |
| GET    | `/documents/{id}/download`        | Public  | Download original file               |
| GET    | `/documents/{id}/view`            | Public  | View original file                   |
| GET    | `/health`                         | Public  | Health check (db + qdrant)           |
| POST   | `/admin/auth/login`               | Admin   | Login (sets HttpOnly cookie)         |
| POST   | `/admin/auth/logout`              | Admin   | Logout                               |
| GET    | `/admin/auth/me`                  | Admin   | Current admin                        |
| POST   | `/admin/auth/change-password`     | Admin   | Change password                      |
| GET    | `/admin/dashboard/stats`          | Admin   | Dashboard statistics + recent logs   |
| GET/POST| `/admin/documents`               | Admin   | List / upload documents              |
| GET/PUT| `/admin/documents/{id}`           | Admin   | Get / update metadata                |
| POST   | `/admin/documents/{id}/replace`   | Admin   | Replace file & re-index              |
| POST   | `/admin/documents/{id}/reindex`   | Admin   | Re-run indexing                      |
| DELETE | `/admin/documents/{id}`           | Admin   | Delete document + vectors            |
| GET/POST| `/admin/llm-providers`           | Admin   | List / create providers              |
| PUT/DELETE| `/admin/llm-providers/{id}`    | Admin   | Update / delete provider             |
| POST   | `/admin/llm-providers/{id}/test`  | Admin   | Test provider connection             |
| GET/PUT| `/admin/rag/config`               | Admin   | Get / update RAG settings            |
| GET    | `/admin/rag/embedding-models`     | Admin   | Available embedding models           |
| GET    | `/admin/rag/reranker-models`      | Admin   | Available reranker models            |
| GET/DELETE| `/admin/conversations`         | Admin   | List / delete conversations          |
| GET    | `/admin/conversations/{session_id}`| Admin   | Conversation detail                  |
| GET    | `/admin/logs`                     | Admin   | Paginated system logs                |
| GET/PUT| `/admin/settings`                 | Admin   | General + security settings          |

Interactive docs at `http://localhost:8000/docs`.

---

## Troubleshooting

- **"No enabled LLM providers are configured"** appears in System Logs / chat fails → add an LLM provider under Admin → LLM Providers (or set `OPENROUTER_API_KEY`), then test it.
- **Frontend can't reach the API** → ensure the frontend container is built with `INTERNAL_API_URL=http://backend:8000` (default) and the backend container is healthy.
- **Chat answers are not grounded / "no information found"** → upload documents and confirm their status becomes `INDEXED`; lower the similarity threshold in RAG Settings if results are too strict.
- **Qdrant version warnings** → keep `qdrant-client>=1.13,<1.14` (requirements) in sync with the `qdrant/qdrant:v1.13.4` image.
- **Reset the stack** → `docker compose down -v` (removes DB, Qdrant and document volumes).



