import { Link } from "react-router-dom";
import "../../styles/Register.css";

function RegisterLeftPanel() {
  return (
    <section className="register-left-panel" aria-label="About CareFlow">
      <div className="register-brand">
        <span className="register-brand-icon" aria-hidden="true">✚</span>
        <div><strong>CareFlow</strong><small>CLINICAL OPS PLATFORM</small></div>
      </div>
      <div className="register-intro">
        <span className="register-pill">Multi-Departmental Sync</span>
        <h2>Join cross-functional departments streamlining patient handoffs.</h2>
        <p>Coordinate hospital cases, track responsibilities, and keep teams connected in one workspace.</p>
        <div className="register-feature"><span aria-hidden="true">⇄</span><div><strong>Connected workflows</strong><small>Follow cases and tasks across departments.</small></div></div>
        <div className="register-feature"><span aria-hidden="true">✦</span><div><strong>Secure staff access</strong><small>New accounts require administrator approval.</small></div></div>
      </div>
      <p className="register-left-footer">● &nbsp; CareFlow · Hospital Operations Platform</p>
    </section>
  );
}

function RegisterRightPanel() {
  function handleSubmit(event) {
    event.preventDefault();
    alert("Registration API is not connected yet. We'll add it tomorrow.");
}

  return (
    <section className="register-right-panel">
      <header className="register-form-header">
        <h1>Create CareFlow Staff Account</h1>
        <p>Register for operational workflow access and floor shifts.</p>
      </header>
      <form className="register-form" onSubmit={handleSubmit}>
        <div className="register-field">
          <label htmlFor="register-name">FULL NAME</label>
          <input id="register-name" name="name" type="text" placeholder="e.g. Dr. Marcus Vance" autoComplete="name" required />
        </div>
        <div className="register-field">
          <label htmlFor="register-email">HOSPITAL WORK EMAIL</label>
          <input id="register-email" name="email" type="email" placeholder="e.g. m.vance@hospital.org" autoComplete="email" required />
        </div>
        <div className="register-field">
          <label htmlFor="register-department">PRIMARY DEPARTMENT</label>
          <select id="register-department" name="department" defaultValue="" required>
            <option value="" disabled>Select assigned hospital department</option>
            <option value="emergency">Emergency</option>
            <option value="radiology">Radiology</option>
            <option value="surgery">Surgery</option>
            <option value="nursing">Nursing</option>
            <option value="administration">Administration</option>
          </select>
        </div>
        <div className="register-field">
          <label htmlFor="register-password">CREATE PASSWORD</label>
          <input id="register-password" name="password" type="password" placeholder="Create a password" autoComplete="new-password" minLength={8} required />
          <div className="register-requirements" aria-label="Password requirements">
            <span className="register-requirements-title">SECURITY REQUIREMENTS</span>
            <div><span>○ 8+ characters</span><span>○ 1+ number</span><span>○ 1+ symbol</span></div>
          </div>
        </div>
        <div className="register-field">
          <label htmlFor="register-confirm">CONFIRM PASSWORD</label>
          <input id="register-confirm" name="confirmPassword" type="password" placeholder="Confirm your password" autoComplete="new-password" required />
        </div>
        <p className="register-info">New staff accounts start with pending status. A hospital administrator must approve access before you can sign in.</p>
        <button className="register-submit" type="submit">Complete Registration <span aria-hidden="true">→</span></button>
      </form>
      <footer className="register-right-footer">
        <p>Already have staff credentials? <Link to="/login">Sign In</Link></p>
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
          <div><strong>Registration Pending Verification</strong><p>New staff accounts require administrator approval before access is enabled.</p></div>
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
