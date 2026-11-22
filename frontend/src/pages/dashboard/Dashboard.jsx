import { useState, useEffect } from "react";
import { getNotifications } from "../../api/notifications";
import "../../styles/Dashboard.css";

export default function Dashboard() {
  const [search, setSearch] = useState("");
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([]);


  useEffect(() => {
    async function loadNotifications() {
      try {
        const data = await getNotifications();
        setNotifications(data.notifications);
      }
      catch (error) {
        console.error("Error fetching notifications:", error);
      }
    }
    loadNotifications();
  }, []);

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

            <nav className="cf-nav">
              <a href="/dashboard" className="cf-nav-link active">
                <span className="material-symbols-outlined">dashboard</span>
                Dashboard
              </a>

              <a href="/cases" className="cf-nav-link">
                <span className="material-symbols-outlined">folder_managed</span>
                Cases
              </a>

              <a href="/my-tasks" className="cf-nav-link">
                <span className="material-symbols-outlined">checklist</span>
                My Tasks
              </a>

              <a href="/analytics" className="cf-nav-link">
                <span className="material-symbols-outlined">analytics</span>
                Analytics
              </a>
            </nav>
          </div>

          <div className="cf-nav-section">
            <div className="cf-nav-heading">
              <p className="cf-nav-label">ADMINISTRATION</p>
              <span className="cf-authorized">Authorized</span>
            </div>

            <nav className="cf-nav">
              <a href="/admin/users" className="cf-nav-link">
                <span className="material-symbols-outlined">group</span>
                Users
              </a>

              <a href="/admin/departments" className="cf-nav-link">
                <span className="material-symbols-outlined">domain</span>
                Departments
              </a>
            </nav>
          </div>
        </div>

        <div className="cf-sidebar-footer">
          <div className="cf-footer-line">
            <span>Platform</span>
            <span className="cf-version">v21.2</span>
          </div>

          <div className="cf-footer-links">
            <a href="#privacy">Privacy</a>
            <span>•</span>
            <a href="#terms">Terms</a>
          </div>
        </div>
      </aside>

      <div className="cf-page">
        <header className="cf-topbar">
          <div className="cf-search">
            <span className="material-symbols-outlined">search</span>
            <input
              type="search"
              placeholder="Search cases, workflows, or staff..."
              aria-label="Search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>

          <div className="cf-topbar-right">
            <div className="cf-system-status">
              <span className="cf-status-dot"></span>
              System Active
            </div>

            <div className="cf-notification-wrapper">
              <button
                type="button"
                className="cf-icon-button cf-notifications"
                aria-label="Notifications"
                aria-expanded={showNotifications}
                onClick={() =>
                  setShowNotifications(!showNotifications)
                }
              >
                <span className="material-symbols-outlined">
                  notifications
                </span>
                <span className="cf-notification-count">3</span>
              </button>

              {showNotifications && (
                <div className="cf-notification-panel">
                  <h3>Notifications</h3>

                  {notifications.length === 0 ? (
                    <p>No notifications yet.</p>
                  ) : (
                    notifications.map((notification) => (
                      <p key={notification.id}>
                        {notification.message}
                      </p>
                    ))
                  )}
                </div>
              )}

            </div>

            <div className="cf-profile">
              <div className="cf-profile-text">
                <strong>Elena Rostova</strong>
                <span>Ops Lead / Admin</span>
              </div>
              <div className="cf-avatar">ER</div>
              <span className="material-symbols-outlined cf-chevron">
                expand_more
              </span>
            </div>
          </div>
        </header>

        <main className="cf-main">
          <section className="cf-hero">
            <div className="cf-hero-copy">
              <div className="cf-hero-eyebrow">
                <span className="cf-live-pill">
                  <span className="cf-status-dot"></span>
                  Live Shift Monitor
                </span>
                <span>St. Jude Wing • Ward 4 Ops Hub</span>
              </div>

              <h1>
                Good morning, Elena Rostova
                <span className="cf-role-title">
                  {" "}— Lead Coordinator
                </span>
              </h1>

              <p>
                Here is your operational workflow summary across all active
                hospital teams. <strong>4 items</strong> require immediate
                departmental attention.
              </p>
            </div>

            <div className="cf-hero-actions">
              <button type="button" className="cf-button cf-button-muted">
                <span className="material-symbols-outlined">sync</span>
                Sync Feeds
              </button>

              <a href="/cases/new" className="cf-button cf-button-primary">
                <span className="material-symbols-outlined">
                  add_circle
                </span>
                Initiate New Case
              </a>
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
                <span className="cf-count-pill">3 Critical</span>
              </div>

              <article className="cf-work-card">
                <div className="cf-work-card-body">
                  <div className="cf-work-card-top">
                    <div>
                      <div className="cf-card-tags">
                        <span className="cf-tag cf-tag-amber">
                          Due in 25 mins
                        </span>
                        <span className="cf-case-id">#CF-2026-0842</span>
                      </div>

                      <h3>Prepare Medical Transfer Documentation</h3>
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
                    <button type="button" className="cf-small-button">
                      Reassign
                    </button>
                    <button type="button" className="cf-small-button primary">
                      View Details
                    </button>
                  </div>
                </div>
              </article>

              <article className="cf-work-card">
                <div className="cf-work-card-body">
                  <div className="cf-work-card-top">
                    <div>
                      <div className="cf-card-tags">
                        <span className="cf-tag cf-tag-red">
                          <span className="cf-mini-dot"></span>
                          Blocked
                        </span>
                        <span className="cf-case-id">#CF-2026-0839</span>
                      </div>

                      <h3>Pharmacy Medication Discharge Verification</h3>

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
                    <button type="button" className="cf-small-button">
                      View Blocker
                    </button>
                    <button type="button" className="cf-small-button beige">
                      <span className="material-symbols-outlined">
                        notifications_active
                      </span>
                      Nudge Team
                    </button>
                  </div>
                </div>
              </article>

              <article className="cf-work-card">
                <div className="cf-work-card-body">
                  <div className="cf-work-card-top">
                    <div>
                      <div className="cf-card-tags">
                        <span className="cf-tag cf-tag-green">
                          <span className="cf-mini-dot green"></span>
                          In Progress
                        </span>
                        <span className="cf-case-id">#CF-2026-0850</span>
                      </div>

                      <h3>Patient Bed Turnover &amp; Final Sanitation</h3>
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
                    <button type="button" className="cf-small-button">
                      View Details
                    </button>
                    <button type="button" className="cf-small-button beige">
                      Reassign
                    </button>
                  </div>
                </div>
              </article>

              <a href="/my-tasks" className="cf-view-all">
                View All Tasks
                <span className="material-symbols-outlined">
                  arrow_forward
                </span>
              </a>
            </section>

            <section className="cf-assigned-section">
              <div className="cf-section-heading">
                <div className="cf-section-title">
                  <span className="material-symbols-outlined cf-green-icon">
                    assignment_ind
                  </span>
                  <h2>Tasks I've Assigned</h2>
                </div>
                <span className="cf-updated">Updated 1m ago</span>
              </div>

              <article className="cf-assigned-card">
                <div className="cf-assigned-card-top">
                  <span className="cf-case-id">#CF-2026-0842</span>
                  <span className="cf-tag cf-tag-amber">High Priority</span>
                </div>

                <h3>Review ICU Transfer Documentation</h3>

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
                  <button type="button">View Details</button>
                  <button type="button">Send Reminder</button>
                  <button type="button">Reassign</button>
                </div>
              </article>

              <article className="cf-assigned-card">
                <div className="cf-assigned-card-top">
                  <span className="cf-case-id">#CF-2026-0839</span>
                  <span className="cf-tag cf-tag-red">Blocked</span>
                </div>

                <h3>Verify Discharge Medication</h3>

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
                  <button type="button">View Details</button>
                  <button type="button">Send Reminder</button>
                  <button type="button">Reassign</button>
                </div>
              </article>

              <article className="cf-assigned-card">
                <div className="cf-assigned-card-top">
                  <span className="cf-case-id">#CF-2026-0850</span>
                  <span className="cf-tag cf-tag-green">Normal</span>
                </div>

                <h3>Complete Bed Turnover Inspection</h3>

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
                  <button type="button">View Details</button>
                  <button type="button">Send Reminder</button>
                  <button type="button">Reassign</button>
                </div>
              </article>

              <a href="/my-tasks" className="cf-assigned-link">
                View Task Directory
                <span className="material-symbols-outlined">
                  arrow_forward
                </span>
              </a>
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
        </main>
      </div>
    </div>
  );
}
