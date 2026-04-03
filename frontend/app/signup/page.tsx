"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";
import { signup } from "../../lib/api";

function validatePassword(password: string) {
  return password.length >= 8 && /[A-Z]/.test(password) && /\d/.test(password);
}

export default function SignupPage() {
  const router = useRouter();
  const [orgName, setOrgName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const passwordHint = useMemo(() => {
    if (!password) {
      return "Use 8+ characters with one uppercase letter and one number.";
    }
    return validatePassword(password)
      ? "Password strength looks good."
      : "Password must include 8+ characters, one uppercase letter, and one number.";
  }, [password]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!validatePassword(password)) {
      setError("Password must include 8+ characters, one uppercase letter, and one number.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Password confirmation does not match.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await signup({
        org_name: orgName,
        full_name: fullName,
        email,
        password,
      });
      localStorage.setItem("privategpt_token", result.access_token);
      localStorage.setItem("privategpt_user", JSON.stringify(result.user));
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create your account.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <div className="panel">
        <section className="hero">
          <div className="card">
            <span className="eyebrow">Tenant Isolated</span>
            <h1 className="headline">Spin up a private document workspace for your team.</h1>
            <p className="subcopy">
              Create an organization admin account, upload secure files, and expose the API to
              internal tools, Slack bots, or a production UI without leaking source data.
            </p>
          </div>

          <div className="card">
            <div className="authTabs">
              <Link href="/">Login</Link>
              <Link href="/signup" className="active">
                Sign Up
              </Link>
            </div>

            <h2>Create your organization</h2>
            <form onSubmit={handleSubmit}>
              <div className="field">
                <label htmlFor="orgName">Organization Name</label>
                <input
                  id="orgName"
                  value={orgName}
                  onChange={(event) => setOrgName(event.target.value)}
                  placeholder="Acme Legal LLP"
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="fullName">Admin Full Name</label>
                <input
                  id="fullName"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Priya Shah"
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="email">Admin Email</label>
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
                  placeholder="Choose a strong password"
                  required
                />
                <small className="helperText">{passwordHint}</small>
              </div>

              <div className="field">
                <label htmlFor="confirmPassword">Confirm Password</label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  placeholder="Re-enter password"
                  required
                />
              </div>

              {error ? <p className="errorText">{error}</p> : null}

              <div className="actions">
                <button className="buttonPrimary" type="submit" disabled={loading}>
                  {loading ? "Creating..." : "Create Workspace"}
                </button>
                <Link className="buttonGhost" href="/">
                  Back to Login
                </Link>
              </div>
            </form>
          </div>
        </section>
      </div>
    </main>
  );
}
