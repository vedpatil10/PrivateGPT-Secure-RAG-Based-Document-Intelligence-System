"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import {
  DocumentItem,
  QueryResponse,
  User,
  askQuestion,
  getCurrentUser,
  listDocuments,
  uploadDocument,
} from "../../lib/api";

export default function DashboardPage() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [question, setQuestion] = useState("");
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [submittingQuery, setSubmittingQuery] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    const storedToken = localStorage.getItem("privategpt_token");
    if (!storedToken) {
      window.location.href = "/";
      return;
    }

    setToken(storedToken);

    async function loadDashboard() {
      try {
        const [currentUser, docs] = await Promise.all([
          getCurrentUser(storedToken),
          listDocuments(storedToken),
        ]);
        setUser(currentUser);
        setDocuments(docs.documents);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load dashboard.");
      } finally {
        setLoadingDocs(false);
      }
    }

    void loadDashboard();
  }, []);

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !question.trim()) {
      return;
    }

    setSubmittingQuery(true);
    setError("");
    setMessage("");

    try {
      const result = await askQuestion(token, question, conversationId);
      setQueryResult(result);
      setConversationId(result.conversation_id);
      setMessage(`Answered in ${result.query_time_ms} ms`);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed.");
    } finally {
      setSubmittingQuery(false);
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    if (!token || !event.target.files?.[0]) {
      return;
    }

    setUploading(true);
    setError("");
    setMessage("");

    try {
      const uploaded = await uploadDocument(token, event.target.files[0]);
      setMessage(`Queued ${uploaded.filename} for ingestion.`);
      const docs = await listDocuments(token);
      setDocuments(docs.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  function handleLogout() {
    localStorage.removeItem("privategpt_token");
    localStorage.removeItem("privategpt_user");
    window.location.href = "/";
  }

  return (
    <main className="shell">
      <div className="panel">
        <section className="card">
          <div className="topbar">
            <div>
              <span className="eyebrow">Secure Dashboard</span>
              <h1 style={{ marginBottom: 10 }}>
                {user ? `Welcome back, ${user.full_name}` : "PrivateGPT Workspace"}
              </h1>
              <p className="subcopy">
                Manage tenant-isolated documents, run grounded RAG queries, and monitor source-cited
                answers from one interface.
              </p>
            </div>
            <div className="topbarActions">
              <Link className="buttonGhost" href="http://localhost:8501" target="_blank">
                Open Streamlit MVP
              </Link>
              <button className="buttonPrimary" type="button" onClick={handleLogout}>
                Logout
              </button>
            </div>
          </div>
        </section>

        <section className="dashboardGrid">
          <div className="grid">
            <div className="card">
              <h2>Document Space</h2>
              <p className="subcopy">
                Upload files into your tenant queue. The backend encrypts the file, processes it
                asynchronously, and makes it queryable once indexing completes.
              </p>

              <div className="actions">
                <label className="buttonPrimary fileButton">
                  {uploading ? "Uploading..." : "Upload Document"}
                  <input type="file" onChange={handleUpload} hidden />
                </label>
              </div>

              {loadingDocs ? <p className="helperText">Loading documents...</p> : null}

              <div className="list" style={{ marginTop: 18 }}>
                {documents.length ? (
                  documents.map((document) => (
                    <div className="row" key={document.id}>
                      <div>
                        <strong>{document.original_filename}</strong>
                        <p className="rowMeta">
                          {document.file_type.toUpperCase()} | {document.access_level} |{" "}
                          {document.chunk_count} chunks
                        </p>
                      </div>
                      <span className="tag">{document.status}</span>
                    </div>
                  ))
                ) : (
                  <p className="helperText">No documents uploaded yet.</p>
                )}
              </div>
            </div>

            <div className="card">
              <h2>Ask the Knowledge Base</h2>
              <form onSubmit={handleAsk}>
                <div className="field">
                  <label htmlFor="question">Question</label>
                  <input
                    id="question"
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="What does the board report say about Q4 risk exposure?"
                    required
                  />
                </div>
                <div className="actions">
                  <button className="buttonPrimary" type="submit" disabled={submittingQuery}>
                    {submittingQuery ? "Running..." : "Ask"}
                  </button>
                </div>
              </form>

              {message ? <p className="successText">{message}</p> : null}
              {error ? <p className="errorText">{error}</p> : null}

              {queryResult ? (
                <div className="responseCard">
                  <h3>Grounded Answer</h3>
                  <p className="responseText">{queryResult.answer}</p>

                  <h3>Sources</h3>
                  <div className="list">
                    {queryResult.sources.map((source, index) => (
                      <div className="row sourceRow" key={`${source.document_name}-${index}`}>
                        <div>
                          <strong>{source.document_name}</strong>
                          <p className="rowMeta">
                            Score {source.relevance_score.toFixed(2)}
                            {source.page_number ? ` | Page ${source.page_number}` : ""}
                            {source.section_title ? ` | ${source.section_title}` : ""}
                          </p>
                          <p className="snippet">{source.chunk_content}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>

          <aside className="grid">
            <div className="card">
              <h2>Workspace Snapshot</h2>
              <div className="stats">
                <div className="stat">
                  <strong>{documents.length}</strong>
                  Documents
                </div>
                <div className="stat">
                  <strong>{user?.role ?? "viewer"}</strong>
                  Role
                </div>
                <div className="stat">
                  <strong>{user?.is_active ? "Active" : "Pending"}</strong>
                  Status
                </div>
              </div>
            </div>

            <div className="card">
              <h2>Architecture Fit</h2>
              <p className="subcopy">
                This frontend is the production-oriented counterpart to the Streamlit MVP in your
                architecture. It talks directly to FastAPI so the same retrieval layer can later
                power SaaS dashboards, bots, and internal tools.
              </p>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
