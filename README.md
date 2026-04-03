# PrivateGPT - Secure RAG-Based Document Intelligence

<div align="center">

**A complete RAG pipeline for private document Q&A.**  
No data leaves your machine unless you choose to deploy it that way.

`Python` `FastAPI` `Streamlit` `Next.js` `FAISS` `LangChain` `PyTorch`

</div>

---

## Quick Start

### 1. Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your environment file

```bash
copy .env.example .env
```

Choose an LLM provider in `.env`:

- `LLM_PROVIDER=llama_cpp` for local GGUF inference
- `LLM_PROVIDER=ollama` for Ollama-managed models
- `LLM_PROVIDER=huggingface` for Transformers-based local inference

If you use `llama_cpp`, put the `.gguf` model file in `models/` and update `LLM_MODEL_PATH`.

### 4. Initialize the database

```bash
python scripts/setup_db.py
```

### 5. Run the backend

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Run the ingestion worker

```bash
python scripts/run_worker.py
```

Queued documents are recovered from the database on startup, so uploads survive service restarts.

### 7. Run the Streamlit MVP

```bash
streamlit run streamlit_app/app.py
```

### 8. Run the Next.js SaaS frontend scaffold

```bash
cd frontend
npm install
npm run dev
```

The frontend targets `http://localhost:8000` by default. Override it with `NEXT_PUBLIC_API_BASE_URL`.

## Verification

### Local verification on Windows

Run:

```powershell
.\scripts\verify.ps1
```

This script exists specifically to solve the Windows Store Python limitation that can make
`python` or `py` unusable from some shells. It:

- finds a real Python installation instead of the WindowsApps shim
- creates `.venv`
- installs `requirements-ci.txt`
- runs `pytest`

If it reports that no usable interpreter was found, install Python 3.11 or 3.12 from
python.org and disable the Windows App Execution Alias entries for `python` and `python3`.

### GitHub verification

Every push to `main` now triggers the workflow in [.github/workflows/ci.yml](/c:/Users/HP/OneDrive/Desktop/Projects/PrivateGPT/.github/workflows/ci.yml), which runs the test suite on GitHub Actions using Python 3.11.

---

## Features

- Private, local-first RAG pipeline for sensitive documents
- Multi-format ingestion for PDFs, Office docs, CSV, email, images, and text
- FAISS vector search with hierarchical chunking and reranking
- Multi-tenant isolation with role-based access control
- Query, upload, delete, and source-level audit logging
- Swappable local LLM providers for `llama_cpp`, `ollama`, and `huggingface`
- Async ingestion pipeline with encrypted file persistence
- Database-backed ingestion recovery for queued documents after restarts
- Streamlit MVP for rapid internal usage
- Next.js frontend scaffold for SaaS-style delivery
- Docker, docker-compose, and Alembic scaffolding for production hardening
- Local and GitHub-based verification workflows

---

## Architecture

```text
Upload -> Async Ingestion Queue -> Loader -> Chunker -> Embeddings -> FAISS
Query -> Embed -> Retrieve -> RBAC Filter -> Rerank -> Prompt -> LLM -> Cited Response
```

---

## Project Structure

```text
PrivateGPT/
|-- api/              # FastAPI backend
|-- config/           # Environment and settings
|-- core/             # Security, middleware, dependencies
|-- models/           # Database models and schemas
|-- services/         # RAG, auth, ingestion, analytics, vector store
|-- streamlit_app/    # Streamlit MVP frontend
|-- frontend/         # Next.js SaaS frontend scaffold
|-- alembic/          # Migration scaffold
|-- scripts/          # Setup and helper scripts
`-- data/             # Local runtime data (gitignored)
```

---

## Deployment Notes

`docker-compose.yml` includes:

- FastAPI API service
- Standalone ingestion worker
- Streamlit service
- PostgreSQL
- Redis

For lightweight local development, the default `.env.example` still uses SQLite.

---

## Security

- JWT authentication
- Tenant isolation
- Role-based access control
- Encryption at rest for uploaded files
- Audit trail for key user actions
- No mandatory third-party model API calls

---

## Notes

- Runtime verification depends on a working local Python interpreter in the environment.
- The Next.js app is intentionally scaffolded as a clean production base and can be extended page by page.
