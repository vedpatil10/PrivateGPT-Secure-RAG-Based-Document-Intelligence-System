# 🔒 PrivateGPT — Secure RAG-Based Document Intelligence

<div align="center">

**A complete RAG pipeline for private document Q&A.**  
No data leaves your machine. Ever.

`Python` `PyTorch` `LLaMA-2` `LangChain` `FAISS` `Streamlit` `FastAPI`

</div>

---

## 🚀 Quick Start

### 1. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Download a Model (pick one)

| Model | RAM Required | Quality | Download |
|-------|-------------|---------|----------|
| TinyLlama 1.1B Q4 | ~700MB | Good for testing | [HuggingFace](https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF) |
| Phi-2 Q4 | ~1.8GB | Better | [HuggingFace](https://huggingface.co/TheBloke/phi-2-GGUF) |
| Mistral 7B Q4 | ~4.4GB | Best | [HuggingFace](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF) |

Place the `.gguf` file in the `models/` directory and update `LLM_MODEL_PATH` in `.env`.

### 4. Initialize Database

```bash
python scripts/setup_db.py
```

Default credentials: `admin@privategpt.local` / `admin123!`

### 5. Run the App

**Streamlit UI (recommended for getting started):**
```bash
streamlit run streamlit_app/app.py
```

**FastAPI Backend:**
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📋 Features

- **🔐 100% Private** — All processing on-device, no cloud APIs
- **📄 Multi-Format** — PDF, Word, Excel, PowerPoint, CSV, images (OCR), emails, text
- **🧠 RAG Pipeline** — Retrieval-Augmented Generation with cited sources
- **🔍 Smart Retrieval** — FAISS vector search + cross-encoder reranking
- **✂️ Hierarchical Chunking** — Summary + detail chunks for better matches
- **🏢 Multi-Tenant** — Isolated document spaces per organization
- **🔑 RBAC** — Role-based access control (Admin, Manager, Analyst, Viewer)
- **📝 Audit Trail** — Full logging of queries, responses, and source chunks
- **🔄 Swappable LLMs** — LLaMA-2, Mistral, Mixtral, TinyLlama, Phi-2, etc.
- **⚡ Async Ingestion** — Background document processing pipeline
- **💬 Conversational** — Follow-up questions with conversation memory

---

## 🏗 Architecture

```
Query → Embed → FAISS Search → RBAC Filter → Cross-Encoder Rerank → LLM Generate → Cited Response
```

---

## 📁 Project Structure

```
PrivateGPT/
├── api/              # FastAPI backend
├── config/           # Settings & configuration
├── core/             # Security, middleware, DI
├── models/           # Database models & schemas
├── services/         # Business logic
│   ├── ingestion/    # Document loaders, chunkers
│   ├── embedding_service.py
│   ├── vector_store.py
│   ├── llm_service.py
│   ├── retrieval_service.py
│   └── rag_pipeline.py
├── streamlit_app/    # Streamlit frontend
├── scripts/          # Setup & utility scripts
└── data/             # Local data (gitignored)
```

---

## ⚙️ Configuration

All settings via `.env` file. See `.env.example` for all options.

Key settings for **8GB RAM** systems:
- `LLM_PROVIDER=llama_cpp` (CPU inference)
- `LLM_N_GPU_LAYERS=0` (pure CPU)
- `LLM_N_THREADS=4` (adjust to your CPU cores)
- `EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2` (lightweight)
- `ENABLE_RERANKING=true` (small overhead, big quality boost)

---

## 🔒 Security

- JWT authentication with role claims
- Per-tenant data isolation
- Pre-retrieval RBAC filtering
- File encryption at rest
- Full audit trail
- No external API calls

---

## 📄 License

Private — All rights reserved.
