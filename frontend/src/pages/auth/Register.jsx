
import { useState } from "react";
import { Link } from "react-router-dom";
import { registerUser } from "../../api/auth";
import "../../styles/Register.css";

function RegisterLeftPanel() {
  return (
    <section className="register-left-panel" aria-label="About CareFlow">
      <div className="register-brand">
        <span className="register-brand-icon" aria-hidden="true">
          ✚
        </span>
        <div>
          <strong>CareFlow</strong>
          <small>CLINICAL OPS PLATFORM</small>
        </div>
      </div>

      <div className="register-intro">
        <span className="register-pill">Multi-Departmental Sync</span>

        <h2>
          Join cross-functional departments streamlining patient handoffs.
        </h2>

        <p>
          Coordinate hospital cases, track responsibilities, and keep
          teams connected in one workspace.
        </p>

        <div className="register-feature">
          <span aria-hidden="true">⇄</span>
          <div>
            <strong>Connected workflows</strong>
            <small>Follow cases and tasks across departments.</small>
          </div>
        </div>

        <div className="register-feature">
          <span aria-hidden="true">✦</span>
          <div>
            <strong>Secure staff access</strong>
            <small>New accounts require administrator approval.</small>
          </div>
        </div>
      </div>

      <p className="register-left-footer">
        ● &nbsp; CareFlow · Hospital Operations Platform
      </p>
    </section>
  );
}

function RegisterRightPanel() {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const hasLength = password.length >= 8;
  const hasNumber = /\d/.test(password);
  const hasSymbol = /[^a-zA-Z0-9\s]/.test(password);

  async function handleSubmit(event) {
    event.preventDefault();
    if (loading) return;

    setError("");
    setSuccess("");

    const form = event.currentTarget;
    const formData = new FormData(form);

    const name = formData.get("name").trim();
    const email = formData.get("email").trim();
    const confirmPassword = formData.get("confirmPassword");

    if (!name) {
      setError("Please enter your full name.");
      return;
    }

    if (!hasLength || !hasNumber || !hasSymbol) {
      setError("Please meet all password requirements.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const data = await registerUser(name, email, password);

      setSuccess(
        data.message ||
          "Registration successful. Awaiting administrator approval."
      );

      form.reset();
      setPassword("");
    } catch (err) {
      setError(err.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="register-right-panel">
      <header className="register-form-header">
        <h1>Create CareFlow Staff Account</h1>
        <p>Register for operational workflow access and floor shifts.</p>
      </header>

      <form className="register-form" onSubmit={handleSubmit} aria-busy={loading}>
        <div className="register-field">
          <label htmlFor="register-name">FULL NAME</label>
          <input
            id="register-name"
            name="name"
            type="text"
            placeholder="e.g. Dr. Marcus Vance"
            autoComplete="name"
            required
          />
        </div>

        <div className="register-field">
          <label htmlFor="register-email">HOSPITAL WORK EMAIL</label>
          <input
            id="register-email"
            name="email"
            type="email"
            placeholder="e.g. m.vance@hospital.org"
            autoComplete="email"
            required
          />
        </div>

        <div className="register-field">
          <label htmlFor="register-password">CREATE PASSWORD</label>
          <input
            id="register-password"
            name="password"
            type="password"
            placeholder="Create a password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            required
          />

          <div
            className="register-requirements"
            aria-label="Password requirements"
          >
            <span className="register-requirements-title">
              SECURITY REQUIREMENTS
            </span>

            <div>
              <span className={hasLength ? "requirement-met" : ""}>
                {hasLength ? "✓" : "○"} 8+ characters
              </span>

              <span className={hasNumber ? "requirement-met" : ""}>
                {hasNumber ? "✓" : "○"} 1+ number
              </span>

              <span className={hasSymbol ? "requirement-met" : ""}>
                {hasSymbol ? "✓" : "○"} 1+ symbol
              </span>
            </div>
          </div>
        </div>

        <div className="register-field">
          <label htmlFor="register-confirm">CONFIRM PASSWORD</label>
          <input
            id="register-confirm"
            name="confirmPassword"
            type="password"
            placeholder="Confirm your password"
            autoComplete="new-password"
            required
          />
        </div>

        <p className="register-info">
          New staff accounts start with pending status. A hospital
          administrator must approve access before you can sign in.
        </p>

        {error && (
          <p className="register-error" role="alert">
            {error}
          </p>
        )}

        {success && (
          <p className="register-success" role="status">
            {success}
          </p>
        )}

        <button
          className="register-submit"
          type="submit"
          disabled={loading}
        >
          {loading ? "Creating account..." : "Complete Registration"}
          <span aria-hidden="true"> →</span>
        </button>
      </form>

      <footer className="register-right-footer">
        <p>
          Already have staff credentials? <Link to="/login">Sign In</Link>
        </p>
        <small>CareFlow · Hospital Operations Platform</small>
      </footer>
    </section>
  );
}

function Register() {
  return (
    <div className="register-page">
      <div className="register-shell">
        <aside className="register-notice">
          <span aria-hidden="true">✓</span>
          <div>
            <strong>Registration Pending Verification</strong>
            <p>
              New staff accounts require administrator approval
              before access is enabled.
            </p>
          </div>
        </aside>

        <main className="register-card">
          <RegisterLeftPanel />
          <RegisterRightPanel />
        </main>
      </div>
    </div>
  );
}

export default Register;
