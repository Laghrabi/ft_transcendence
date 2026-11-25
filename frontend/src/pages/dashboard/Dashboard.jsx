
import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { getNotifications,
  markNotificationRead,
} from "../../api/notifications";
import "../../styles/Dashboard.css";

export default function Dashboard() {
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [notificationStatus, setNotificationStatus] = useState("loading");
  const [notificationRetry, setNotificationRetry] = useState(0);
  const [readStatus, setReadStatus] = useState({});

  const notificationButton = useRef(null);

  const unreadCount = notifications.filter(
    (notification) => !notification.is_read
  ).length;

  const isLoadingNotifications = notificationStatus === "loading";

  const isSavingNotification =
    Object.values(readStatus).includes("saving");

  // TODO: Add state for real dashboard statistics.
  // TODO: Add state for real attention and assigned tasks.
  // TODO: Add state for department workloads.
  // TODO: Add search state when real task data is available.
  // TODO: Retrieve authenticated user profile.

  useEffect(() => {
    const controller = new AbortController();

    async function loadNotifications() {
      try {
        const data = await getNotifications({
          signal: controller.signal,
        });

        if (!controller.signal.aborted) {
          setNotifications(data.notifications);
          setNotificationStatus("ready");
        }
      } catch {
        if (!controller.signal.aborted) {
          setNotificationStatus("error");
        }
      }
    }

    loadNotifications();

    return () => controller.abort();
  }, [notificationRetry]);

  // TODO: Fetch real dashboard data when backend APIs are ready.

  function retryNotifications() {
    setNotificationStatus("loading");
    setNotificationRetry((attempt) => attempt + 1);
  }

  async function handleMarkAsRead(id, button) {
    if (
      isLoadingNotifications ||
      readStatus[id] === "saving"
    ) return;

    setReadStatus((current) => ({
      ...current,
      [id]: "saving",
    }));

    try {
      const updated = await markNotificationRead(id);

      if (document.activeElement === button) {
        button.closest("section")?.focus({
          preventScroll: true,
        });
      }

      setNotifications((current) =>
        current.map((notification) =>
          notification.id === id ? updated : notification
        )
      );

      setReadStatus((current) => {
        const next = { ...current };
        delete next[id];
        return next;
      });
    } catch {
      setReadStatus((current) => ({
        ...current,
        [id]: "error",
      }));
    }
  }

  return (
    <div className="cf-dashboard">

      {/* SIDEBAR */}
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
              <Link
                to="/dashboard"
                className="cf-nav-link active"
                aria-current="page"
              >
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  dashboard
                </span>
                Dashboard
              </Link>

              <Link to="/cases" className="cf-nav-link">
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  folder_managed
                </span>
                Cases
              </Link>

              <Link to="/my-tasks" className="cf-nav-link">
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  checklist
                </span>
                My Tasks
              </Link>

              <Link to="/analytics" className="cf-nav-link">
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  analytics
                </span>
                Analytics
              </Link>
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
              <Link to="/admin/users" className="cf-nav-link">
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  group
                </span>
                Users
              </Link>

              <Link
                to="/admin/departments"
                className="cf-nav-link"
              >
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  domain
                </span>
                Departments
              </Link>
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

      <div className="cf-page">

        {/* TOPBAR */}
        <header className="cf-topbar">

          {/* TODO: Enable search after integrating real task data. */}
          <div className="cf-search">
            <span
              className="material-symbols-outlined"
              aria-hidden="true"
            >
              search
            </span>

            <input
              type="search"
              placeholder="Search unavailable"
              aria-label="Search unavailable until task data is connected"
              disabled
            />
          </div>

          <div className="cf-topbar-right">

            {/* NOTIFICATIONS */}
            <div
              className="cf-notification-wrapper"
              onKeyDown={(event) => {
                if (
                  event.key === "Escape" &&
                  showNotifications
                ) {
                  event.preventDefault();
                  setShowNotifications(false);
                  notificationButton.current?.focus();
                }
              }}
            >
              <button
                ref={notificationButton}
                type="button"
                className="cf-icon-button cf-notifications"
                aria-label={
                  notificationStatus === "ready" ||
                  notifications.length > 0
                    ? `Notifications (${unreadCount} unread)`
                    : "Notifications"
                }
                aria-expanded={showNotifications}
                aria-controls={
                  showNotifications
                    ? "cf-notification-panel"
                    : undefined
                }
                onClick={() =>
                  setShowNotifications((open) => !open)
                }
              >
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  notifications
                </span>

                {unreadCount > 0 && (
                  <span
                    className="cf-notification-count"
                    aria-hidden="true"
                  >
                    {unreadCount}
                  </span>
                )}
              </button>

              {showNotifications && (
                <section
                  className="cf-notification-panel"
                  id="cf-notification-panel"
                  aria-labelledby="cf-notification-title"
                  tabIndex={-1}
                >
                  <h3 id="cf-notification-title">
                    Notifications
                  </h3>

                  {notificationStatus === "loading" && (
                    <p role="status">
                      Loading notifications…
                    </p>
                  )}

                  {notificationStatus === "error" && (
                    <div>
                      <p role="alert">
                        Could not load notifications.
                        {notifications.length > 0 &&
                          " Showing the last loaded list."}
                      </p>

                      <button
                        type="button"
                        className="cf-small-button"
                        disabled={isSavingNotification}
                        onClick={(event) => {
                          event.currentTarget
                            .closest("section")
                            ?.focus({ preventScroll: true });

                          retryNotifications();
                        }}
                      >
                        Retry
                      </button>
                    </div>
                  )}

                  {notificationStatus === "ready" &&
                    notifications.length === 0 && (
                      <p role="status">
                        No notifications yet.
                      </p>
                    )}

                  {notifications.length > 0 && (
                    <ul className="cf-notification-list">
                      {notifications.map(
                        ({ id, message, is_read: isRead }) => (
                          <li
                            key={id}
                            className="cf-notification-item"
                          >
                            <p>{message}</p>

                            {isRead ? (
                              <small role="status">Read</small>
                            ) : (
                              <button
                                type="button"
                                className="cf-small-button"
                                aria-disabled={
                                  isLoadingNotifications ||
                                  readStatus[id] === "saving"
                                }
                                onClick={(event) =>
                                  handleMarkAsRead(
                                    id,
                                    event.currentTarget
                                  )
                                }
                              >
                                {readStatus[id] === "saving"
                                  ? "Saving…"
                                  : "Mark as read"}
                              </button>
                            )}

                            {readStatus[id] === "error" && (
                              <p role="alert">
                                Could not mark as read.
                                Try again.
                              </p>
                            )}
                          </li>
                        )
                      )}
                    </ul>
                  )}
                </section>
              )}
            </div>

            {/* TODO: Display real authenticated user information. */}
            <div className="cf-profile">
              <div className="cf-profile-text">
                <strong>Account</strong>
                <span>Profile unavailable</span>
              </div>

              <div className="cf-avatar" aria-hidden="true">
                <span className="material-symbols-outlined">
                  person
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* MAIN DASHBOARD */}
        <main className="cf-main">

          {/* HERO */}
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

          {/* STATISTICS */}
          {/* TODO: Replace unavailable values with real API data. */}
          <section className="cf-stats">
            <article className="cf-stat-card">
              <div className="cf-stat-top">
                <span className="cf-stat-label">
                  ACTIVE CASES
                </span>
                <span className="cf-stat-icon green">
                  <span className="material-symbols-outlined">
                    folder_open
                  </span>
                </span>
              </div>

              <div className="cf-stat-value">
                <strong>—</strong>
              </div>

              <p>Data unavailable</p>
            </article>

            <article className="cf-stat-card">
              <div className="cf-stat-top">
                <span className="cf-stat-label">
                  PENDING TASKS
                </span>
                <span className="cf-stat-icon beige">
                  <span className="material-symbols-outlined">
                    pending_actions
                  </span>
                </span>
              </div>

              <div className="cf-stat-value">
                <strong>—</strong>
              </div>

              <p>Data unavailable</p>
            </article>

            <article className="cf-stat-card cf-stat-warning">
              <div className="cf-stat-top">
                <span className="cf-stat-label">
                  BLOCKED / OVERDUE
                </span>
                <span className="cf-stat-icon amber">
                  <span className="material-symbols-outlined">
                    warning
                  </span>
                </span>
              </div>

              <div className="cf-stat-value">
                <strong>—</strong>
              </div>

              <p>Data unavailable</p>
            </article>

            <article className="cf-stat-card">
              <div className="cf-stat-top">
                <span className="cf-stat-label">
                  COMPLETED TODAY
                </span>
                <span className="cf-stat-icon green">
                  <span className="material-symbols-outlined">
                    task_alt
                  </span>
                </span>
              </div>

              <div className="cf-stat-value">
                <strong>—</strong>
              </div>

              <p>Data unavailable</p>
            </article>
          </section>

          <div className="cf-content-grid">

            {/* ATTENTION TASKS */}
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

            {/* ASSIGNED TASKS */}
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

          {/* DEPARTMENT WORKLOAD */}
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
