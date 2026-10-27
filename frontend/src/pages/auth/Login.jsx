function LeftPanel() {
  return (
    <section className="left-panel">
      <div>
        <h1>CareFlow</h1>
        <p>Hospital Workflow Coordination</p>
        <p>Staff Portal • Hospital Operations</p>
      </div>

      <div>
        <h2>
          Better coordination.
          <br />
          Smoother patient care.
        </h2>

        <p>
          CareFlow helps hospital teams coordinate cases,
          manage tasks, and track workflows across departments
          through one connected platform.
        </p>
      </div>

      <div>
        <div>
          <h3>Cross-department coordination</h3>
          <p>
            Keep hospital cases and workflows organized
            across departments.
          </p>
        </div>

        <div>
          <h3>Task and case tracking</h3>
          <p>
            Help staff follow assigned tasks,
            case progress, and responsibilities.
          </p>
        </div>

        <div>
          <h3>Workflow visibility</h3>
          <p>
            Make task dependencies, progress,
            and potential delays easier to identify.
          </p>
        </div>
      </div>

      <div>
        <p>CareFlow • Hospital Operations Platform</p>
      </div>
    </section>
  );
}

function RightPanel() {
  return (
    <section className="right-panel">
      <div>
        <h1>Welcome back to CareFlow</h1>
        <p>Sign in with your hospital staff credentials.</p>
      </div>

      <form>
        <div>
          <label htmlFor="email">Hospital / Work Email</label>
          <input
            type="email"
            id="email"
            name="email"
            placeholder="m.vance@hospital.careflow.org"
            autoComplete="email"
            required
          />
        </div>

        <div>
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            name="password"
            autoComplete="current-password"
            required
          />
        </div>

        <button type="submit">
          Sign In to CareFlow
        </button>
      </form>

      <div>
        <p>
          Don't have an account?{" "}
          <a href="/register">Register hospital staff</a>
        </p>
      </div>

      <footer>
        <p>
          Restricted hospital workflow system.
          Authorized clinical & ops personnel only.
        </p>

        <p>
          <a href="/privacy">Privacy Policy</a>
          {" • "}
          <a href="/terms">Terms of Service</a>
        </p>
      </footer>
    </section>
  );
}

function Login() {
  return (
    <main className="flex">
      <LeftPanel />
      <RightPanel />
    </main>
  );
}

export default Login;