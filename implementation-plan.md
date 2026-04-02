PrivateGPT: Secure RAG-Based Document Intelligence System
A complete, enterprise-grade RAG pipeline with multi-tenant isolation, RBAC, audit trails, async document ingestion, hierarchical chunking, cross-encoder reranking, swappable LLMs, and dual frontends (Streamlit MVP + Next.js SaaS).

User Review Required
IMPORTANT

Hardware Requirements: LLaMA-2 7B quantized (4-bit) requires ~4GB VRAM minimum. Do you have a CUDA-capable GPU available? If not, we can default to CPU-only mode with a smaller model (e.g., TinyLlama) or use Ollama for model serving.

IMPORTANT

HuggingFace Access: LLaMA-2 requires accepting Meta's license on HuggingFace. Do you have a HuggingFace token with access to meta-llama/Llama-2-7b-chat-hf? Alternatively, we can use GGUF models via llama-cpp-python which don't require HF access.

WARNING

Scope Prioritization: This is an enormous system. I recommend building in phases — starting with a fully working Streamlit MVP (Phases 1-4), then graduating to the enterprise SaaS layer (Phases 5-7). Should I proceed with this phased approach?


Project Structure
PrivateGPT/
├── .env.example                    # Environment variables template
├── .gitignore
├── README.md
├── requirements.txt
├── pyproject.toml
│
├── config/
│   ├── __init__.py
│   ├── settings.py                 # Pydantic Settings (all config)
│   └── logging_config.py           # Structured logging setup
│
├── core/
│   ├── __init__.py
│   ├── security.py                 # JWT, password hashing, encryption
│   ├── dependencies.py             # FastAPI dependency injection
│   ├── exceptions.py               # Custom exception classes
│   └── middleware.py               # Tenant context, audit logging middleware
│
├── models/
│   ├── __init__.py
│   ├── database.py                 # SQLAlchemy engine & session
│   ├── user.py                     # User, Role, Organization models
│   ├── document.py                 # Document, Chunk metadata models
│   ├── audit.py                    # AuditLog model
│   └── schemas.py                  # Pydantic request/response schemas
│
├── services/
│   ├── __init__.py
│   ├── auth_service.py             # Authentication & authorization
│   ├── document_service.py         # Document CRUD operations
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── loaders.py              # Format-specific document loaders
│   │   ├── chunker.py              # Hierarchical chunking strategy
│   │   ├── pipeline.py             # Async ingestion pipeline
│   │   └── processor.py            # Text cleaning & preprocessing
│   ├── embedding_service.py        # Embedding generation & caching
│   ├── vector_store.py             # FAISS index management (per-tenant)
│   ├── retrieval_service.py        # Hybrid retrieval + reranking
│   ├── llm_service.py              # LLM loading, inference, swapping
│   ├── rag_pipeline.py             # End-to-end RAG orchestration
│   └── analytics_service.py        # Usage analytics & metrics
│
├── api/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Login, register, token refresh
│   │   ├── documents.py            # Upload, list, delete documents
│   │   ├── query.py                # Chat/query endpoints + WebSocket
│   │   ├── admin.py                # Tenant management, user roles
│   │   └── analytics.py            # Usage metrics endpoints
│   └── websocket.py                # WebSocket streaming handler
│
├── streamlit_app/
│   ├── app.py                      # Main Streamlit application
│   ├── pages/
│   │   ├── 1_📄_Documents.py       # Document management page
│   │   ├── 2_💬_Chat.py            # Conversational Q&A page
│   │   ├── 3_⚙️_Settings.py       # Model & system settings
│   │   └── 4_📊_Analytics.py       # Usage dashboard
│   ├── components/
│   │   ├── sidebar.py              # Navigation sidebar
│   │   ├── chat_message.py         # Chat bubble with citations
│   │   └── document_card.py        # Document upload/status card
│   └── utils.py                    # Streamlit helpers
│
├── frontend/                       # Next.js SaaS frontend (Phase 6)
│   └── (created later)
│
├── data/                           # Local data directory (gitignored)
│   ├── faiss_indexes/              # Per-tenant FAISS indexes
│   ├── uploads/                    # Encrypted document uploads
│   └── cache/                      # Embedding cache
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_ingestion.py
│   ├── test_retrieval.py
│   ├── test_rag_pipeline.py
│   └── test_api.py
│
├── scripts/
│   ├── setup_db.py                 # Database initialization
│   ├── create_admin.py             # Create initial admin user
│   └── benchmark.py                # Performance benchmarking
│
└── alembic/                        # Database migrations
    ├── alembic.ini
    └── versions/
Proposed Changes — Phased Implementation
Phase 1: Foundation & Configuration
Sets up the project skeleton, dependencies, configuration system, and database models.

[NEW] 
requirements.txt
Core dependencies:

fastapi, uvicorn[standard], python-multipart — API layer
sqlalchemy, alembic, aiosqlite — Database ORM & migrations
langchain, langchain-community, langchain-huggingface — RAG orchestration
sentence-transformers — Embedding models
faiss-cpu — Vector similarity search
transformers, torch, accelerate, bitsandbytes — LLM inference
streamlit — MVP frontend
python-jose[cryptography], passlib[bcrypt] — Auth
pydantic-settings, python-dotenv — Configuration
pypdf, python-docx, openpyxl, python-pptx, pandas — Document loaders
pytesseract, Pillow — Image OCR
extract-msg — Email parsing
cryptography — File encryption
celery, redis — Async task queue (or asyncio + threading for simpler setup)
cross-encoder models via sentence-transformers — Reranking
[NEW] 
config/settings.py
Pydantic Settings class with:

LLM config (model name, quantization bits, temperature, max tokens)
Embedding config (model name, device, cache dir)
FAISS config (index type, nprobe)
Chunking config (chunk size, overlap, hierarchical settings)
Security config (JWT secret, token expiry, encryption key)
Storage paths (uploads, indexes, cache)
Multi-tenancy settings
[NEW] 
models/database.py
SQLAlchemy async engine setup with SQLite (dev) / PostgreSQL (prod).

[NEW] 
models/user.py
Organization — tenant entity with UUID, name, settings
User — user with email, hashed password, role, org FK
Role enum — ADMIN, MANAGER, ANALYST, VIEWER
[NEW] 
models/document.py
Document — file metadata, org FK, upload status, access level
DocumentChunk — chunk text, embedding ID, parent doc FK, chunk type (summary/detail)
[NEW] 
models/audit.py
AuditLog — user, action, query, response, chunks used, timestamp, org FK
Phase 2: Document Ingestion Pipeline
Builds the async document processing pipeline with format-specific loaders, hierarchical chunking, and embedding generation.

[NEW] 
services/ingestion/loaders.py
Format-specific loaders using a factory pattern:

Format	Library	Notes
PDF	pypdf + pdfplumber	Text + table extraction
Word (.docx)	python-docx	Paragraph & heading-aware
Excel (.xlsx)	openpyxl / pandas	Sheet-by-sheet, row context
PowerPoint (.pptx)	python-pptx	Slide-by-slide with notes
CSV	pandas	Column-aware chunking
Images	pytesseract + Pillow	OCR pipeline
Email (.msg/.eml)	extract-msg / email	Subject, body, attachments
Text (.txt/.md)	Built-in	Direct read
[NEW] 
services/ingestion/chunker.py
Hierarchical chunking strategy:

Summary chunks: LLM-generated or extractive summary of entire document → stored with chunk_type="summary"
Detail chunks: RecursiveCharacterTextSplitter with 1000 char chunks, 200 char overlap → chunk_type="detail"
Both types get separate embeddings in the same FAISS index with metadata tags
[NEW] 
services/ingestion/pipeline.py
Async ingestion pipeline:

Uses asyncio + concurrent.futures.ThreadPoolExecutor for background processing
Document queue with status tracking (QUEUED → PROCESSING → INDEXED → ERROR)
Selective re-indexing: on document update/delete, removes old embeddings by doc ID and re-indexes only affected chunks
Progress callbacks for frontend status updates
[NEW] 
services/embedding_service.py
Loads configurable SentenceTransformer model
Embedding cache using disk-backed dictionary (shelve/sqlite)
Batch encoding for efficiency
Swappable: supports domain-specific models (medical, legal)
[NEW] 
services/vector_store.py
Per-tenant FAISS index management:

Each organization gets its own FAISS index file
IndexIVFFlat for large-scale with IndexFlatL2 for small collections
Persistent save/load from disk
Add/remove vectors by document ID mapping
Metadata store (parallel array) mapping vector IDs to chunk metadata
Phase 3: RAG Pipeline & LLM Integration
Builds the retrieval → reranking → generation pipeline with swappable LLMs.

[NEW] 
services/llm_service.py
Swappable LLM loading:

LLMProvider base class with load(), generate(), stream() methods
HuggingFaceLLM — loads via transformers + bitsandbytes (4-bit NF4)
OllamaLLM — connects to local Ollama server
LlamaCppLLM — GGUF models via llama-cpp-python
Registry pattern: configure model name in settings, system loads the right provider
Supports: LLaMA-2, Mistral, Mixtral, any HF-compatible model
[NEW] 
services/retrieval_service.py
Multi-stage retrieval:

Query embedding → search FAISS for top-K candidates (K=20)
RBAC filtering → remove chunks user doesn't have permission for
Cross-encoder reranking → cross-encoder/ms-marco-MiniLM-L-6-v2 scores each (query, chunk) pair
Top-N selection → take top 5 most relevant chunks after reranking
Return chunks with source document metadata (filename, page, section)
[NEW] 
services/rag_pipeline.py
End-to-end orchestration via LangChain:

Custom RetrievalQA chain with prompt template
Prompt includes: system instruction, retrieved context with source citations, conversation history, user query
Streaming token generation for real-time UI updates
Audit logging: records query, retrieved chunks, generated response
Conversation memory: sliding window of last N exchanges
Phase 4: Streamlit MVP Frontend
Fully functional Streamlit application with document management, chat, and settings.

[NEW] 
streamlit_app/app.py
Main app entry with:

Login/authentication flow
Multi-page navigation
Session state management
Dark theme with custom CSS
[NEW] 
streamlit_app/pages/1_📄_Documents.py
Bulk file uploader (drag & drop, multiple formats)
Document list with status indicators (queued/processing/indexed/error)
Delete/re-index individual documents
Upload progress tracking
[NEW] 
streamlit_app/pages/2_💬_Chat.py
Conversational Q&A interface
Real-time streaming responses
Source citations with expandable document snippets
Follow-up question support with conversation history
"No context found" fallback handling
[NEW] 
streamlit_app/pages/3_⚙️_Settings.py
LLM model selection dropdown
Embedding model configuration
Chunking parameters
Temperature / max tokens sliders
Phase 5: FastAPI Backend & Security
Production API layer with JWT auth, RBAC, multi-tenant isolation, and audit trails.

[NEW] 
api/main.py
FastAPI application factory:

CORS middleware
Tenant context middleware (extracts org from JWT)
Exception handlers
Lifespan events (load models on startup)
[NEW] 
core/security.py
JWT token creation/validation with tenant_id and role claims
Password hashing with bcrypt
File encryption/decryption with Fernet (symmetric)
API key generation for programmatic access
[NEW] 
core/middleware.py
TenantMiddleware — extracts tenant from JWT, injects into request state
AuditMiddleware — logs every query with user, query, response, chunks, timestamp
RateLimitMiddleware — per-tenant rate limiting
[NEW] 
api/routes/auth.py
POST /auth/register — create org + admin user
POST /auth/login — returns JWT
POST /auth/refresh — token refresh
POST /auth/invite — invite user to org with role
[NEW] 
api/routes/documents.py
POST /documents/upload — multipart upload, queues for async ingestion
GET /documents — list documents for current tenant
DELETE /documents/{id} — delete + remove embeddings
GET /documents/{id}/status — ingestion status
[NEW] 
api/routes/query.py
POST /query — synchronous Q&A with citations
WebSocket /ws/query — streaming Q&A
Both enforce RBAC pre-retrieval filtering
[NEW] 
api/routes/admin.py
User management (list, update roles, deactivate)
Document access control management
Audit log viewer with filters
[NEW] 
api/routes/analytics.py
Query volume over time
Most queried documents
Failed query rate (no context found)
Per-tenant compute usage
Response latency metrics
Phase 6: Next.js SaaS Frontend (Future)
NOTE

This phase is planned but will be implemented after the core backend + Streamlit MVP are stable. The FastAPI backend from Phase 5 serves as the API for this frontend.

Next.js 14 with App Router
Shadcn/UI component library
Dark mode with glassmorphism design
Real-time chat via WebSocket
Document management dashboard
Admin panel with analytics
Usage-based billing integration ready
Phase 7: Production Hardening (Future)
Docker Compose deployment
HTTPS/TLS termination
Database migration to PostgreSQL
Redis for task queue (replacing asyncio)
Model download automation
Health checks and monitoring
Backup & restore procedures
Open Questions
IMPORTANT

GPU Availability: What GPU do you have? This determines whether we use 4-bit quantization, 8-bit, or CPU-only with a smaller model.
IMPORTANT

2. Model Access: Do you prefer HuggingFace models (requires token + GPU) or Ollama (simpler setup, manages models locally)?

IMPORTANT

3. Database: SQLite for development is fine, but should we plan for PostgreSQL from the start, or start simple?

WARNING

4. Scope: Should I build Phases 1-4 first (complete working system with Streamlit) and then add the enterprise features (Phases 5-7), or do you want a different ordering?

Verification Plan
Automated Tests
Unit tests: Document loaders, chunker, embedding service, vector store CRUD
Integration tests: Full RAG pipeline (ingest → query → response with citations)
API tests: Auth flow, document upload, query endpoints
Run with: pytest tests/ -v
Manual Verification
Upload sample documents (PDF, DOCX, CSV, image with text)
Verify chunking produces semantic chunks with proper overlap
Query documents and verify cited sources match actual content
Test RBAC: ensure restricted users can't access unauthorized documents
Test document deletion removes embeddings from FAISS index
Verify streaming responses work in Streamlit chat UI
Browser recording of complete user flow