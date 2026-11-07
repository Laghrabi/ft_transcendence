import "../../styles/Login.css";
import { useState } from "react";

function LeftPanel() {
  return (
    <section className="left-panel">
      <header className="brand">
        <span className="brand-icon" aria-hidden="true">✚</span>
        <div>
          <h1>CareFlow</h1>
          <p>HOSPITAL LOGISTICS</p>
        </div>
      </header>

      <div className="left-intro">
        <span className="staff-badge">STAFF PORTAL • OPS CENTRAL</span>
        <h2>
          Better coordination.
          <br />
          Smoother patient care.
        </h2>
        <p>
          CareFlow helps hospital teams coordinate cases, manage tasks,
          and track workflows across departments through one connected platform.
        </p>
      </div>

      <div className="feature-list">
        <div className="feature">
          <span className="feature-icon" aria-hidden="true">⇄</span>
          <div>
            <h3>Cross-department coordination</h3>
            <p>Keep hospital cases and workflows organized across departments.</p>
          </div>
        </div>

        <div className="feature">
          <span className="feature-icon" aria-hidden="true">⌁</span>
          <div>
            <h3>Task and case tracking</h3>
            <p>Help staff follow assigned tasks, case progress, and responsibilities.</p>
          </div>
        </div>

        <div className="feature">
          <span className="feature-icon" aria-hidden="true">◷</span>
          <div>
            <h3>Workflow visibility</h3>
            <p>Make task dependencies, progress, and potential delays easier to identify.</p>
          </div>
        </div>
      </div>

      <div className="left-footer">
        <span className="status-dot" aria-hidden="true" />
        CareFlow • Hospital Operations Platform
      </div>
    </section>
  );
}

function RightPanel() {
  //hook is a special fun react provides to giv components extra abilities

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  function handleSubmit(event) {
    event.preventDefault();
    // console.log("Login form submitted");
    setError(
      "Login is not available yet. Waiting for backend authentication."
    );
  }
  return (
    <section className="right-panel">
      <div className="right-content">
        <div className="welcome">
          <span className="eyebrow">SECURE STAFF ACCESS</span>
          <h1>Welcome back to CareFlow</h1>
          <p>Sign in with your hospital staff credentials.</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="email">Hospital / Work Email</label>
            <input
              type="email"
              id="email"
              name="email"
              placeholder="m.vance@hospital.careflow.org"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            {/* <p style={{ color: "red", fontSize: "20px" }}>You are typing: {email}</p> */}
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              placeholder="Enter your password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            {/* <p style={{ color: "red", fontSize: "20px" }}>You are typing: {password}</p> */}
          </div>

          <button className="sign-in-button" type="submit">
            Sign In to CareFlow <span aria-hidden="true">→</span>
          </button>
          {error && (
            <p className="login-error" role="alert">
              {error}
            </p>
          )}        
          </form>

        <p className="register-text">
          Don't have an account?{" "}
          <a href="/register">Register hospital staff</a>
        </p>
      </div>

      <footer className="right-footer">
        <p>
          Restricted hospital workflow system.
          <br />
          Authorized clinical &amp; ops personnel only.
        </p>
        <div>
          <a href="/privacy">Privacy Policy</a>
          <span aria-hidden="true">•</span>
          <a href="/terms">Terms of Service</a>
        </div>
      </footer>
    </section>
  );
}

function Login() {
  return (
    <main className="login-card">
      <LeftPanel />
      <RightPanel />
    </main>
  );
}

export default Login;