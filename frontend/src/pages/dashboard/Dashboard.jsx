
import { useState, useRef } from "react";
import { Link } from "react-router-dom";
import Sidebar from "../../components/common/Sidebar";
import Topbar from "../../components/common/Topbar";
import Notifications from "../../components/common/Notifications";
import StatCard from "../../components/common/StatCard";
import "../../styles/Dashboard.css";

export default function Dashboard() {
  const [showNotifications, setShowNotifications] = useState(false);
  const [notificationStatus, setNotificationStatus] = useState("loading");
  const [notificationRetry, setNotificationRetry] = useState(0);
  const [readStatus, setReadStatus] = useState({});

  const notificationButton = useRef(null);

  const isLoadingNotifications = notificationStatus === "loading";

  const isSavingNotification =
    Object.values(readStatus).includes("saving");

  // TODO: Add state for real dashboard statistics.
  // TODO: Add state for real attention and assigned tasks.
  // TODO: Add state for department workloads.
  // TODO: Add search state when real task data is available.
  // TODO: Retrieve authenticated user profile.

  // TODO: Fetch real dashboard data when backend APIs are ready.

  function retryNotifications() {
    setNotificationStatus("loading");
    setNotificationRetry((attempt) => attempt + 1);
  }

  return (
    <div className="cf-dashboard">

      <Sidebar />

      <div className="cf-page">

        <Topbar>
          <Notifications
            showNotifications={showNotifications}
            setShowNotifications={setShowNotifications}
            notificationButton={notificationButton}
            notificationStatus={notificationStatus}
            setNotificationStatus={setNotificationStatus}
            notificationRetry={notificationRetry}
            retryNotifications={retryNotifications}
            readStatus={readStatus}
            setReadStatus={setReadStatus}
          />
        </Topbar>

        <main className="cf-main">

          <section className="cf-hero">
            <div className="cf-hero-copy">
              <div className="cf-hero-eyebrow">
                <span>Shift Overview</span>
              </div>

              <h1>CareFlow Dashboard</h1>

              <p>
                Monitor hospital workflows, cases, tasks,
                and notifications.
              </p>
            </div>

            <div className="cf-hero-actions">
              <button
                type="button"
                className="cf-button cf-button-muted"
                disabled={
                  isLoadingNotifications ||
                  isSavingNotification
                }
                onClick={() => {
                  setShowNotifications(true);
                  retryNotifications();
                  notificationButton.current?.focus({
                    preventScroll: true,
                  });
                }}
              >
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  sync
                </span>
                Refresh Notifications
              </button>

              <Link
                to="/cases/new"
                className="cf-button cf-button-primary"
              >
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  add_circle
                </span>
                Initiate New Case
              </Link>
            </div>
          </section>

          {/* TODO: Replace unavailable values with real API data. */}
          <section className="cf-stats">
            <StatCard
              label="ACTIVE CASES"
              icon="folder_open"
              color="green"
              value="—"
              description="Data unavailable"
            />

            <StatCard
              label="PENDING TASKS"
              icon="pending_actions"
              color="beige"
              value="—"
              description="Data unavailable"
            />

            <StatCard
              label="BLOCKED / OVERDUE"
              icon="warning"
              color="amber"
              value="—"
              description="Data unavailable"
              warning
            />

            <StatCard
              label="COMPLETED TODAY"
              icon="task_alt"
              color="green"
              value="—"
              description="Data unavailable"
            />
          </section>

          <div className="cf-content-grid">

            <section className="cf-attention-section">
              <div className="cf-section-heading">
                <div className="cf-section-title">
                  <span className="material-symbols-outlined cf-amber-icon">
                    bolt
                  </span>
                  <h2>Tasks Needing Immediate Attention</h2>
                </div>
              </div>

              {/* TODO: Render real urgent tasks from Django. */}
              <p className="cf-task-search-empty">
                Task data unavailable.
              </p>

              <Link to="/my-tasks" className="cf-view-all">
                View All Tasks
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  arrow_forward
                </span>
              </Link>
            </section>

            <section className="cf-assigned-section">
              <div className="cf-section-heading">
                <div className="cf-section-title">
                  <span className="material-symbols-outlined cf-green-icon">
                    assignment_ind
                  </span>
                  <h2>Tasks I've Assigned</h2>
                </div>
              </div>

              {/* TODO: Render real assigned tasks from Django. */}
              <p className="cf-task-search-empty">
                Assigned task data unavailable.
              </p>

              <Link
                to="/my-tasks"
                className="cf-assigned-link"
              >
                View Task Directory
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  arrow_forward
                </span>
              </Link>
            </section>
          </div>

          <section className="cf-departments">
            <div className="cf-departments-heading">
              <div>
                <h2>Department Workload &amp; Handoff Pulse</h2>
                <p>
                  Active operational case balance across
                  downstream service points
                </p>
              </div>
            </div>

            {/* TODO: Render real department metrics from Django. */}
            <p className="cf-task-search-empty">
              Department workload data unavailable.
            </p>
          </section>

          <nav
            className="cf-footer-links cf-compact-legal"
            aria-label="Legal"
          >
            <Link to="/privacy">Privacy</Link>
            <span aria-hidden="true">•</span>
            <Link to="/terms">Terms</Link>
          </nav>
        </main>
      </div>
    </div>
  );
}
