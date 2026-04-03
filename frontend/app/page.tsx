"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { login } from "../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const result = await login(email, password);
      localStorage.setItem("privategpt_token", result.access_token);
      localStorage.setItem("privategpt_user", JSON.stringify(result.user));
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <div className="panel">
        <section className="hero">
          <div className="card">
            <span className="eyebrow">Private Deployment Ready</span>
            <h1 className="headline">Ask sensitive documents questions without sending data anywhere.</h1>
            <p className="subcopy">
              PrivateGPT combines FastAPI, FAISS, Sentence Transformers, and swappable local LLMs
              into a secure RAG stack built for legal, healthcare, finance, and internal knowledge
              systems.
            </p>

            <div className="stats">
              <div className="stat">
                <strong>FAISS</strong>
                Millisecond retrieval across tenant-isolated indexes.
              </div>
              <div className="stat">
                <strong>RBAC</strong>
                Role-filtered retrieval before generation runs.
              </div>
              <div className="stat">
                <strong>Audit</strong>
                Full trace of who asked what and which chunks answered it.
              </div>
            </div>
          </div>

          <div className="card">
            <div className="authTabs">
              <Link href="/" className="active">
                Login
              </Link>
              <Link href="/signup">Sign Up</Link>
            </div>

            <h2>Sign in to your secure workspace</h2>
            <p className="subcopy">
              Use the same backend credentials as the Streamlit client and FastAPI routes.
            </p>

            <form onSubmit={handleSubmit}>
              <div className="field">
                <label htmlFor="email">Work Email</label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="admin@company.com"
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  required
                />
              </div>

              {error ? <p className="errorText">{error}</p> : null}

              <div className="actions">
                <button className="buttonPrimary" type="submit" disabled={loading}>
                  {loading ? "Signing in..." : "Login"}
                </button>
                <Link className="buttonGhost" href="/signup">
                  Create Account
                </Link>
              </div>
            </form>
          </div>
        </section>
      </div>
    </main>
  );
}
