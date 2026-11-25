import { Link, NavLink } from "react-router-dom";
import "../../styles/Common.css";

function navLinkClass({ isActive }) {
  return isActive ? "cf-nav-link active" : "cf-nav-link";
}

export default function Sidebar() {
  return (
    <aside className="cf-sidebar">
      <div>
        <div className="cf-brand">
          <div className="cf-brand-icon">
            <span className="material-symbols-outlined">
              local_hospital
            </span>
          </div>

          <div>
            <strong>CareFlow</strong>
            <small>WORKFLOW OPS</small>
          </div>
        </div>

        <div className="cf-nav-section">
          <p className="cf-nav-label">OPERATIONS</p>

          <nav className="cf-nav" aria-label="Operations">
            <NavLink
              to="/dashboard"
              className={navLinkClass}
            >
              <span
                className="material-symbols-outlined"
                aria-hidden="true"
              >
                dashboard
              </span>
              Dashboard
            </NavLink>

            <NavLink to="/cases" className={navLinkClass}>
              <span
                className="material-symbols-outlined"
                aria-hidden="true"
              >
                folder_managed
              </span>
              Cases
            </NavLink>

            <NavLink to="/my-tasks" className={navLinkClass}>
              <span
                className="material-symbols-outlined"
                aria-hidden="true"
              >
                checklist
              </span>
              My Tasks
            </NavLink>

            <NavLink to="/analytics" className={navLinkClass}>
              <span
                className="material-symbols-outlined"
                aria-hidden="true"
              >
                analytics
              </span>
              Analytics
            </NavLink>
          </nav>
        </div>

        <div className="cf-nav-section">
          <div className="cf-nav-heading">
            <p className="cf-nav-label">ADMINISTRATION</p>
          </div>

          <nav
            className="cf-nav"
            aria-label="Administration"
          >
            <NavLink to="/admin/users" className={navLinkClass}>
              <span
                className="material-symbols-outlined"
                aria-hidden="true"
              >
                group
              </span>
              Users
            </NavLink>

            <NavLink
              to="/admin/departments"
              className={navLinkClass}
            >
              <span
                className="material-symbols-outlined"
                aria-hidden="true"
              >
                domain
              </span>
              Departments
            </NavLink>
          </nav>
        </div>
      </div>

      <div className="cf-sidebar-footer">
        <div className="cf-footer-line">
          <span>Platform</span>
          <span className="cf-version">CareFlow</span>
        </div>

        <div className="cf-footer-links">
          <Link to="/privacy">Privacy</Link>
          <span aria-hidden="true">•</span>
          <Link to="/terms">Terms</Link>
        </div>
      </div>
    </aside>
  );
}
