
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { registerUser, getDepartments, getRoles } from "../../api/auth";
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

  const [roles, setRoles] = useState([]);
  const [rolesLoading, setRolesLoading] = useState(true);
  const [rolesError, setRolesError] = useState(false);

  const [departments, setDepartments] = useState([]);
  const [departmentsLoading, setDepartmentsLoading] = useState(true);
  const [departmentsError, setDepartmentsError] = useState(false);

  useEffect(() => {
    async function loadRoles() {
      try {
        const data = await getRoles();
        if (!Array.isArray(data)) {
          throw new Error("Expected a list of roles.");
        }
        setRoles(data);
      } catch {
        setRolesError(true);
      } finally {
        setRolesLoading(false);
      }
    }

    loadRoles();
  }, []);

  useEffect(() => {
    async function loadDepartments() {
      try {
        const data = await getDepartments();

        const departmentList = Array.isArray(data)
          ? data
          : data.departments || [];

        setDepartments(
          departmentList.filter(
            (department) => department.is_active === true
          )
        );
      } catch (err) {
        setDepartmentsError(true);
        setError("Unable to load departments. Please try again later.");
      } finally {
        setDepartmentsLoading(false);
      }
    }

    loadDepartments();
  }, []);

  const hasLength = password.length >= 8;
  const hasNumber = /\d/.test(password);
  const hasSymbol = /[^a-zA-Z0-9\s]/.test(password);
  const rolesUnavailable = rolesLoading || rolesError || roles.length === 0;
  const departmentsUnavailable =
    departmentsLoading || departmentsError || departments.length === 0;

  async function handleSubmit(event) {
    event.preventDefault();

    if (loading || rolesUnavailable || departmentsUnavailable) {
      return;
    }

    setError("");
    setSuccess("");

    const form = event.currentTarget;
    const formData = new FormData(form);

    const name = formData.get("name").trim();
    const email = formData.get("email").trim();
    const confirmPassword = formData.get("confirmPassword");
    const roleId = Number(formData.get("role"));
    const departmentId = Number(formData.get("department"));

    if (!name) {
      setError("Please enter your full name.");
      return;
    }

    if (!roleId || !departmentId) {
      setError("Please select your role and department.");
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
      const data = await registerUser(
        name,
        email,
        password,
        roleId,
        departmentId
      );

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

      <form
        className="register-form"
        onSubmit={handleSubmit}
        aria-busy={loading}
      >
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

        {/* ROLE DROPDOWN */}
        <div className="register-field">
          <label htmlFor="register-role">ROLE</label>
          <select
            id="register-role"
            name="role"
            defaultValue=""
            required
            disabled={rolesUnavailable}
          >
            <option value="" disabled>
              {rolesLoading
                ? "Loading roles..."
                : rolesError
                  ? "Unable to load roles"
                  : roles.length === 0
                    ? "No roles available"
                    : "Select your role"}
            </option>
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>
        </div>

        {/* DEPARTMENT DROPDOWN */}
        <div className="register-field">
          <label htmlFor="register-department">DEPARTMENT</label>
          <select
            id="register-department"
            name="department"
            defaultValue=""
            required
            disabled={departmentsUnavailable}
          >
            <option value="" disabled>
              {departmentsLoading
                ? "Loading departments..."
                : departmentsError
                  ? "Unable to load departments"
                  : departments.length === 0
                    ? "No departments available"
                    : "Select your department"}
            </option>

            {departments.map((department) => (
              <option key={department.id} value={department.id}>
                {department.name}
              </option>
            ))}
          </select>
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

        {rolesError && (
          <p className="register-error" role="alert">
            Unable to load roles. Please try again later.
          </p>
        )}

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
          disabled={
            loading || rolesUnavailable || departmentsUnavailable
          }
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
