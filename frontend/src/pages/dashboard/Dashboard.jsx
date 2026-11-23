import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { getNotifications, markNotificationRead } from "../../api/notifications";
import "../../styles/Dashboard.css";

const attentionTasks = {
  transfer: { caseId: "#CF-2026-0842", title: "Prepare Medical Transfer Documentation" },
  medication: { caseId: "#CF-2026-0839", title: "Pharmacy Medication Discharge Verification" },
  turnover: { caseId: "#CF-2026-0850", title: "Patient Bed Turnover & Final Sanitation" },
};

const assignedTasks = {
  transfer: { caseId: "#CF-2026-0842", title: "Review ICU Transfer Documentation" },
  medication: { caseId: "#CF-2026-0839", title: "Verify Discharge Medication" },
  turnover: { caseId: "#CF-2026-0850", title: "Complete Bed Turnover Inspection" },
};

export default function Dashboard() {
  const [search, setSearch] = useState("");
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [notificationStatus, setNotificationStatus] = useState("loading");
  const [notificationRetry, setNotificationRetry] = useState(0);
  const [readStatus, setReadStatus] = useState({});
  const notificationButton = useRef(null);
  const unreadCount = notifications.filter((notification) => !notification.is_read).length;
  const isLoadingNotifications = notificationStatus === "loading";
  const isSavingNotification = Object.values(readStatus).includes("saving");
  const query = search.trim().toLowerCase();
  const matchesTask = ({ title, caseId }) =>
    title.toLowerCase().includes(query) || caseId.toLowerCase().includes(query);
  const attentionMatches = Object.values(attentionTasks).filter(matchesTask).length;
  const assignedMatches = Object.values(assignedTasks).filter(matchesTask).length;

  useEffect(() => {
    const controller = new AbortController();

    async function loadNotifications() {
      try {
        const data = await getNotifications({ signal: controller.signal });
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

  function retryNotifications() {
    setNotificationStatus("loading");
    setNotificationRetry((attempt) => attempt + 1);
  }

  async function handleMarkAsRead(id, button) {
    if (isLoadingNotifications || readStatus[id] === "saving") return;

    setReadStatus((current) => ({ ...current, [id]: "saving" }));

    try {
      const updated = await markNotificationRead(id);
      if (document.activeElement === button) {
        button.closest("section")?.focus({ preventScroll: true });
      }
      setNotifications((current) =>
        current.map((notification) => (notification.id === id ? updated : notification))
      );
      setReadStatus((current) => {
        const next = { ...current };
        delete next[id];
        return next;
      });
    } catch {
      setReadStatus((current) => ({ ...current, [id]: "error" }));
    }
  }

  return (
    <div className="cf-dashboard">
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
              <Link to="/dashboard" className="cf-nav-link active" aria-current="page">
                <span className="material-symbols-outlined" aria-hidden="true">dashboard</span>
                Dashboard
              </Link>

              <Link to="/cases" className="cf-nav-link">
                <span className="material-symbols-outlined" aria-hidden="true">folder_managed</span>
                Cases
              </Link>

              <Link to="/my-tasks" className="cf-nav-link">
                <span className="material-symbols-outlined" aria-hidden="true">checklist</span>
                My Tasks
              </Link>

              <Link to="/analytics" className="cf-nav-link">
                <span className="material-symbols-outlined" aria-hidden="true">analytics</span>
                Analytics
              </Link>
            </nav>
          </div>

          <div className="cf-nav-section">
            <div className="cf-nav-heading">
              <p className="cf-nav-label">ADMINISTRATION</p>
            </div>

            <nav className="cf-nav" aria-label="Administration">
              <Link to="/admin/users" className="cf-nav-link">
                <span className="material-symbols-outlined" aria-hidden="true">group</span>
                Users
              </Link>

              <Link to="/admin/departments" className="cf-nav-link">
                <span className="material-symbols-outlined" aria-hidden="true">domain</span>
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
        <header className="cf-topbar">
          <div className="cf-search">
            <span className="material-symbols-outlined" aria-hidden="true">search</span>
            <input
              type="search"
              placeholder="Search sample tasks..."
              aria-label="Search sample tasks by title or case ID"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <span className="cf-visually-hidden" role="status">
              {query && `${attentionMatches} attention tasks and ${assignedMatches} assigned tasks match.`}
            </span>
          </div>

          <div className="cf-topbar-right">
            <div className="cf-system-status">
              <span className="cf-status-dot"></span>
              Dashboard Preview
            </div>

            <div
              className="cf-notification-wrapper"
              onKeyDown={(event) => {
                if (event.key === "Escape" && showNotifications) {
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
                aria-label={notificationStatus === "ready" || notifications.length > 0
                  ? `Notifications (${unreadCount} unread)`
                  : "Notifications"}
                aria-expanded={showNotifications}
                aria-controls={showNotifications ? "cf-notification-panel" : undefined}
                onClick={() => setShowNotifications((open) => !open)}
              >
                <span className="material-symbols-outlined" aria-hidden="true">
                  notifications
                </span>
                {unreadCount > 0 && (
                  <span className="cf-notification-count" aria-hidden="true">
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
                  <h3 id="cf-notification-title">Notifications</h3>

                  {notificationStatus === "loading" && (
                    <p role="status">Loading notifications…</p>
                  )}
                  {notificationStatus === "error" && (
                    <div>
                      <p role="alert">
                        Could not load notifications.
                        {notifications.length > 0 && " Showing the last loaded list."}
                      </p>
                      <button
                        type="button"
                        className="cf-small-button"
                        disabled={isSavingNotification}
                        onClick={(event) => {
                          event.currentTarget.closest("section")?.focus({ preventScroll: true });
                          retryNotifications();
                        }}
                      >
                        Retry
                      </button>
                    </div>
                  )}
                  {notificationStatus === "ready" && notifications.length === 0 && (
                    <p role="status">No notifications yet.</p>
                  )}
                  {notifications.length > 0 && (
                    <ul className="cf-notification-list">
                      {notifications.map(({ id, message, is_read: isRead }) => (
                        <li key={id} className="cf-notification-item">
                          <p>{message}</p>
                          {isRead ? (
                            <small role="status">Read</small>
                          ) : (
                            <button
                              type="button"
                              className="cf-small-button"
                              aria-disabled={isLoadingNotifications || readStatus[id] === "saving"}
                              onClick={(event) => handleMarkAsRead(id, event.currentTarget)}
                            >
                              {readStatus[id] === "saving" ? "Saving…" : "Mark as read"}
                            </button>
                          )}
                          {readStatus[id] === "error" && (
                            <p role="alert">Could not mark as read. Try again.</p>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              )}
            </div>

            <div className="cf-profile">
              <div className="cf-profile-text">
                <strong>Account</strong>
                <span>Profile unavailable</span>
              </div>
              <div className="cf-avatar" aria-hidden="true">
                <span className="material-symbols-outlined">person</span>
              </div>
            </div>
          </div>
        </header>

        <main className="cf-main">
          <section className="cf-hero">
            <div className="cf-hero-copy">
              <div className="cf-hero-eyebrow">
                <span className="cf-live-pill">
                  <span className="cf-status-dot"></span>
                  Shift Overview
                </span>
                <span>Sample operations data</span>
              </div>

              <h1>CareFlow Dashboard</h1>

              <p>
                The metrics, tasks, and department workloads below use sample
                data. Actions on these sample tasks are unavailable.
              </p>
            </div>

            <div className="cf-hero-actions">
              <button
                type="button"
                className="cf-button cf-button-muted"
                disabled={isLoadingNotifications || isSavingNotification}
                onClick={() => {
                  setShowNotifications(true);
                  retryNotifications();
                  notificationButton.current?.focus({ preventScroll: true });
                }}
              >
                <span className="material-symbols-outlined" aria-hidden="true">sync</span>
                Refresh Notifications
              </button>

              <Link to="/cases/new" className="cf-button cf-button-primary">
                <span className="material-symbols-outlined" aria-hidden="true">
                  add_circle
                </span>
                Initiate New Case
              </Link>
            </div>
          </section>

          <section className="cf-stats">
            <article className="cf-stat-card">
              <div className="cf-stat-top">
                <span className="cf-stat-label">ACTIVE CASES</span>
                <span className="cf-stat-icon green">
                  <span className="material-symbols-outlined">
                    folder_open
                  </span>
                </span>
              </div>

              <div className="cf-stat-value">
                <strong>42</strong>
                <span className="cf-positive">
                  <span className="material-symbols-outlined">
                    trending_up
                  </span>
                  +4 this shift
                </span>
              </div>

              <p>18 in Discharge, 14 in Transfer, 10 Routine Handoffs</p>

              <div className="cf-segmented-progress">
                <span className="cf-segment-one"></span>
                <span className="cf-segment-two"></span>
                <span className="cf-segment-three"></span>
              </div>
            </article>

            <article className="cf-stat-card">
              <div className="cf-stat-top">
                <span className="cf-stat-label">PENDING TASKS</span>
                <span className="cf-stat-icon beige">
                  <span className="material-symbols-outlined">
                    pending_actions
                  </span>
                </span>
              </div>

              <div className="cf-stat-value">
                <strong>19</strong>
                <span>Across 6 wards</span>
              </div>

              <p>7 awaiting department handoff confirmation</p>

              <div className="cf-stat-bottom">
                <span>Team capacity</span>
                <strong>76% Allocated</strong>
              </div>
            </article>

            <article className="cf-stat-card cf-stat-warning">
              <div className="cf-stat-top">
                <span className="cf-stat-label">BLOCKED / OVERDUE</span>
                <span className="cf-stat-icon amber">
                  <span className="material-symbols-outlined">
                    warning
                  </span>
                </span>
              </div>

              <div className="cf-stat-value">
                <strong>3</strong>
                <span className="cf-action-pill">Action Needed</span>
              </div>

              <p>2 Pharmacy review delays, 1 Radiology sign-off</p>

              <div className="cf-stat-bottom cf-warning-text">
                <span className="material-symbols-outlined">
                  schedule
                </span>
                Avg delay time: +38m
              </div>
            </article>

            <article className="cf-stat-card">
              <div className="cf-stat-top">
                <span className="cf-stat-label">COMPLETED TODAY</span>
                <span className="cf-stat-icon green">
                  <span className="material-symbols-outlined">
                    task_alt
                  </span>
                </span>
              </div>

              <div className="cf-stat-value">
                <strong>28</strong>
                <span className="cf-success-pill">+12% speed</span>
              </div>

              <p>Average turnaround: 46 mins across all queues</p>

              <div className="cf-stat-bottom cf-positive">
                <span className="material-symbols-outlined">
                  verified
                </span>
                Target SLA met: 92.4%
              </div>
            </article>
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
                <span className="cf-count-pill">{attentionMatches} shown</span>
              </div>

              <article className="cf-work-card" hidden={!matchesTask(attentionTasks.transfer)}>
                <div className="cf-work-card-body">
                  <div className="cf-work-card-top">
                    <div>
                      <div className="cf-card-tags">
                        <span className="cf-tag cf-tag-amber">
                          Due in 25 mins
                        </span>
                        <span className="cf-case-id">{attentionTasks.transfer.caseId}</span>
                      </div>

                      <h3>{attentionTasks.transfer.title}</h3>
                      <p>
                        Room 402B • Escalation level: Ward Transfer protocol
                      </p>
                    </div>

                    <div className="cf-assignee">
                      <span className="cf-small-avatar">ER</span>
                      <div>
                        <strong>Elena Rostova</strong>
                        <small>Assigned Owner</small>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="cf-work-card-footer">
                  <div className="cf-work-meta">
                    <span className="material-symbols-outlined">
                      swap_horiz
                    </span>
                    Handover: <strong>ICU → Step-Down</strong>
                  </div>

                  <div className="cf-card-actions">
                    <button type="button" disabled className="cf-small-button">
                      Reassign
                    </button>
                    <button type="button" disabled className="cf-small-button primary">
                      View Details
                    </button>
                  </div>
                </div>
              </article>

              <article className="cf-work-card" hidden={!matchesTask(attentionTasks.medication)}>
                <div className="cf-work-card-body">
                  <div className="cf-work-card-top">
                    <div>
                      <div className="cf-card-tags">
                        <span className="cf-tag cf-tag-red">
                          <span className="cf-mini-dot"></span>
                          Blocked
                        </span>
                        <span className="cf-case-id">{attentionTasks.medication.caseId}</span>
                      </div>

                      <h3>{attentionTasks.medication.title}</h3>

                      <div className="cf-dependency">
                        <span className="material-symbols-outlined">
                          lock_clock
                        </span>
                        Dependency: Awaiting Dr. Marcus approval
                      </div>
                    </div>

                    <div className="cf-assignee">
                      <span className="cf-small-avatar neutral">PH</span>
                      <div>
                        <strong>Pharmacy Team</strong>
                        <small>Queue Pool</small>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="cf-work-card-footer">
                  <div className="cf-work-meta">
                    <span className="material-symbols-outlined">
                      timer
                    </span>
                    Stalled for <strong>32 mins</strong>
                  </div>

                  <div className="cf-card-actions">
                    <button type="button" disabled className="cf-small-button">
                      View Blocker
                    </button>
                    <button type="button" disabled className="cf-small-button beige">
                      <span className="material-symbols-outlined">
                        notifications_active
                      </span>
                      Nudge Team
                    </button>
                  </div>
                </div>
              </article>

              <article className="cf-work-card" hidden={!matchesTask(attentionTasks.turnover)}>
                <div className="cf-work-card-body">
                  <div className="cf-work-card-top">
                    <div>
                      <div className="cf-card-tags">
                        <span className="cf-tag cf-tag-green">
                          <span className="cf-mini-dot green"></span>
                          In Progress
                        </span>
                        <span className="cf-case-id">{attentionTasks.turnover.caseId}</span>
                      </div>

                      <h3>{attentionTasks.turnover.title}</h3>
                      <p>
                        Ward 3, Bed 12-A • Standard turnover protocol
                      </p>
                    </div>

                    <div className="cf-assignee">
                      <span className="cf-small-avatar">JA</span>
                      <div>
                        <strong>J. Alvarez</strong>
                        <small>Env. Services</small>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="cf-work-card-footer">
                  <div className="cf-work-meta">
                    <span className="material-symbols-outlined">
                      hourglass_bottom
                    </span>
                    Target Completion: <strong>45 mins</strong>
                  </div>

                  <div className="cf-card-actions">
                    <button type="button" disabled className="cf-small-button">
                      View Details
                    </button>
                    <button type="button" disabled className="cf-small-button beige">
                      Reassign
                    </button>
                  </div>
                </div>
              </article>

              {attentionMatches === 0 && (
                <p className="cf-task-search-empty">No matching sample tasks.</p>
              )}

              <Link to="/my-tasks" className="cf-view-all">
                View All Tasks
                <span className="material-symbols-outlined" aria-hidden="true">
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
                <span className="cf-count-pill">{assignedMatches} shown</span>
              </div>

              <article className="cf-assigned-card" hidden={!matchesTask(assignedTasks.transfer)}>
                <div className="cf-assigned-card-top">
                  <span className="cf-case-id">{assignedTasks.transfer.caseId}</span>
                  <span className="cf-tag cf-tag-amber">High Priority</span>
                </div>

                <h3>{assignedTasks.transfer.title}</h3>

                <div className="cf-detail-rows">
                  <div>
                    <span>ASSIGNED TO</span>
                    <strong>Dr. Sarah Chen</strong>
                  </div>
                  <div>
                    <span>DEPARTMENT</span>
                    <strong>Inpatient Care</strong>
                  </div>
                  <div>
                    <span>STATUS</span>
                    <strong className="cf-status-progress">
                      In Progress
                    </strong>
                  </div>
                  <div>
                    <span>DEADLINE</span>
                    <strong>Today, 11:30 AM</strong>
                  </div>
                </div>

                <div className="cf-assigned-actions">
                  <button type="button" disabled>View Details</button>
                  <button type="button" disabled>Send Reminder</button>
                  <button type="button" disabled>Reassign</button>
                </div>
              </article>

              <article className="cf-assigned-card" hidden={!matchesTask(assignedTasks.medication)}>
                <div className="cf-assigned-card-top">
                  <span className="cf-case-id">{assignedTasks.medication.caseId}</span>
                  <span className="cf-tag cf-tag-red">Blocked</span>
                </div>

                <h3>{assignedTasks.medication.title}</h3>

                <div className="cf-detail-rows">
                  <div>
                    <span>ASSIGNED TO</span>
                    <strong>Pharmacy Team</strong>
                  </div>
                  <div>
                    <span>DEPARTMENT</span>
                    <strong>Pharmacy</strong>
                  </div>
                  <div>
                    <span>STATUS</span>
                    <strong className="cf-status-blocked">
                      Blocked
                    </strong>
                  </div>
                  <div>
                    <span>DEADLINE</span>
                    <strong>Today, 12:00 PM</strong>
                  </div>
                </div>

                <div className="cf-assigned-actions">
                  <button type="button" disabled>View Details</button>
                  <button type="button" disabled>Send Reminder</button>
                  <button type="button" disabled>Reassign</button>
                </div>
              </article>

              <article className="cf-assigned-card" hidden={!matchesTask(assignedTasks.turnover)}>
                <div className="cf-assigned-card-top">
                  <span className="cf-case-id">{assignedTasks.turnover.caseId}</span>
                  <span className="cf-tag cf-tag-green">Normal</span>
                </div>

                <h3>{assignedTasks.turnover.title}</h3>

                <div className="cf-detail-rows">
                  <div>
                    <span>ASSIGNED TO</span>
                    <strong>J. Alvarez</strong>
                  </div>
                  <div>
                    <span>DEPARTMENT</span>
                    <strong>Environmental Services</strong>
                  </div>
                  <div>
                    <span>STATUS</span>
                    <strong className="cf-status-progress">
                      In Progress
                    </strong>
                  </div>
                  <div>
                    <span>DEADLINE</span>
                    <strong>Today, 1:15 PM</strong>
                  </div>
                </div>

                <div className="cf-assigned-actions">
                  <button type="button" disabled>View Details</button>
                  <button type="button" disabled>Send Reminder</button>
                  <button type="button" disabled>Reassign</button>
                </div>
              </article>

              {assignedMatches === 0 && (
                <p className="cf-task-search-empty">No matching sample tasks.</p>
              )}

              <Link to="/my-tasks" className="cf-assigned-link">
                View Task Directory
                <span className="material-symbols-outlined" aria-hidden="true">
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
                  Active operational case balance across downstream service
                  points
                </p>
              </div>

              <div className="cf-legend">
                <span>
                  <i className="cf-legend-green"></i>
                  Optimal flow
                </span>
                <span>
                  <i className="cf-legend-amber"></i>
                  Review threshold
                </span>
              </div>
            </div>

            <div className="cf-department-grid">
              <article className="cf-department-card">
                <div className="cf-department-name">
                  <strong>EMERGENCY</strong>
                  <span className="material-symbols-outlined">
                    emergency
                  </span>
                </div>
                <div className="cf-department-count">
                  <strong>12</strong>
                  <span>Active cases</span>
                </div>
                <div className="cf-progress-track">
                  <span style={{ width: "80%" }}></span>
                </div>
                <small>Handoff SLA: 94%</small>
              </article>

              <article className="cf-department-card">
                <div className="cf-department-name">
                  <strong>SURGERY</strong>
                  <span className="material-symbols-outlined">
                    medical_services
                  </span>
                </div>
                <div className="cf-department-count">
                  <strong>9</strong>
                  <span>Active cases</span>
                </div>
                <div className="cf-progress-track">
                  <span style={{ width: "60%" }}></span>
                </div>
                <small>Handoff SLA: 88%</small>
              </article>

              <article className="cf-department-card">
                <div className="cf-department-name">
                  <strong>RADIOLOGY</strong>
                  <span className="material-symbols-outlined">
                    view_in_ar
                  </span>
                </div>
                <div className="cf-department-count">
                  <strong>8</strong>
                  <span>Active cases</span>
                </div>
                <div className="cf-progress-track">
                  <span style={{ width: "55%" }}></span>
                </div>
                <small>Handoff SLA: 91%</small>
              </article>

              <article className="cf-department-card warning">
                <div className="cf-department-name">
                  <strong>PHARMACY</strong>
                  <span className="material-symbols-outlined">
                    medication
                  </span>
                </div>
                <div className="cf-department-count">
                  <strong>7</strong>
                  <span>Slow Queue</span>
                </div>
                <div className="cf-progress-track">
                  <span style={{ width: "72%" }}></span>
                </div>
                <small>Handoff SLA: 71% (Alert)</small>
              </article>

              <article className="cf-department-card">
                <div className="cf-department-name">
                  <strong>TRANSPORT</strong>
                  <span className="material-symbols-outlined">
                    local_shipping
                  </span>
                </div>
                <div className="cf-department-count">
                  <strong>6</strong>
                  <span>Active cases</span>
                </div>
                <div className="cf-progress-track">
                  <span style={{ width: "40%" }}></span>
                </div>
                <small>Handoff SLA: 98%</small>
              </article>
            </div>
          </section>

          <nav className="cf-footer-links cf-compact-legal" aria-label="Legal">
            <Link to="/privacy">Privacy</Link>
            <span aria-hidden="true">•</span>
            <Link to="/terms">Terms</Link>
          </nav>
        </main>
      </div>
    </div>
  );
}
