import { useState, useRef } from "react";
import { Link } from "react-router-dom";
import Sidebar from "../../components/common/Sidebar";
import Topbar from "../../components/common/Topbar";
import Notifications from "../../components/common/Notifications";
import StatCard from "../../components/common/StatCard";
import "../../styles/Dashboard.css";
import "../../styles/CasesList.css";

export default function CasesList() {
  const [showNotifications, setShowNotifications] = useState(false);
  const [notificationStatus, setNotificationStatus] = useState("loading");
  const [notificationRetry, setNotificationRetry] = useState(0);
  const [readStatus, setReadStatus] = useState({});

  const notificationButton = useRef(null);

  function retryNotifications() {
    setNotificationStatus("loading");
    setNotificationRetry((attempt) => attempt + 1);
  }

  return (
    <div className="cf-dashboard cf-cases">

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

        <main className="cf-main cases-main">

          {/* Statistics cards */}
          {/* TODO: Connect real case statistics APIs. */}

          <section
            className="cf-stats cases-stats"
            aria-label="Case statistics"
          >
            <StatCard
              label="ACTIVE PIPELINES"
              icon="monitor_heart"
              color="green"
              value="—"
              description="Data unavailable"
            />

            <StatCard
              label="BLOCKED HANDOFFS"
              icon="warning"
              color="amber"
              value="—"
              description="Data unavailable"
              warning
            />

            <StatCard
              label="AVG. ESCORT TIME"
              icon="schedule"
              color="beige"
              value="—"
              description="Data unavailable"
            />

            <StatCard
              label="HANDOFFS TODAY"
              icon="fact_check"
              color="green"
              value="—"
              description="Data unavailable"
            />
          </section>

          {/* Page heading */}

          <section className="cases-heading">
            <div>
              <span className="cases-eyebrow">
                Cross-Ward Routing
              </span>

              <h1>Cases &amp; Workflows</h1>

              <p>
                Search, filter, and track cross-department
                hospital coordination cases.
              </p>
            </div>

            <div className="cases-actions">
              <button
                type="button"
                className="cf-button cf-button-muted"
                disabled
              >
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  tune
                </span>
                Batch Actions
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
                Create New Case
              </Link>
            </div>
          </section>

          {/* Case categories */}

          <div className="cases-segments">

            <div
              className="cases-tabs"
              aria-label="Case categories"
            >
              {[
                "Active Cases",
                "Blocked / Delayed",
                "Completed",
                "Archived",
              ].map((label) => (
                <button
                  key={label}
                  type="button"
                  disabled
                >
                  {label} <span>—</span>
                </button>
              ))}
            </div>

            <div className="cases-legend">
              <span>Normal Velocity</span>
              <span>Pending Handshake</span>
              <span>Bottleneck SLA</span>
            </div>

          </div>

          {/* Search and filters */}
          {/* TODO: Connect filters to real case data. */}

          <section
            className="cases-filters"
            aria-label="Case filters"
          >
            <div className="cases-filter-grid">

              <div className="cases-search">
                <span
                  className="material-symbols-outlined"
                  aria-hidden="true"
                >
                  search
                </span>

                <input
                  aria-label="Search cases"
                  placeholder="Search by Case ID, reference, or keyword..."
                  disabled
                />
              </div>

              {[
                "Types",
                "Departments",
                "Statuses",
                "Priorities",
              ].map((label) => (
                <select
                  key={label}
                  aria-label={`Filter by ${label.toLowerCase()}`}
                  disabled
                >
                  <option>All {label}</option>
                </select>
              ))}

            </div>

            <div className="cases-filter-footer">
              <span>
                Filters unavailable until case data is connected.
              </span>

              <div className="cases-actions">
                <button type="button" disabled>
                  Reset Filters
                </button>

                <button type="button" disabled>
                  Apply Filters
                </button>
              </div>
            </div>
          </section>

          {/* Cases table */}
          {/* TODO: Fetch and render real cases from Django. */}

          <section
            className="cases-table-panel"
            aria-label="Operational cases"
          >
            <div
              className="cases-table-scroll"
              tabIndex={0}
              role="region"
              aria-label="Scrollable cases table"
            >
              <table className="cases-table">

                <thead>
                  <tr>
                    {[
                      "Case ID & Ref",
                      "Workflow Type",
                      "Lead Department",
                      "Current Stage",
                      "Coordinator / Lead",
                      "Status",
                      "Priority",
                      "Waiting Time & SLA",
                      "Actions",
                    ].map((heading) => (
                      <th key={heading} scope="col">
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  <tr>
                    <td
                      colSpan={9}
                      className="cases-unavailable"
                    >
                      <span
                        className="material-symbols-outlined"
                        aria-hidden="true"
                      >
                        folder_open
                      </span>

                      <strong>Case data unavailable</strong>

                      <p>
                        Case records will appear here when
                        the backend integration is ready.
                      </p>
                    </td>
                  </tr>
                </tbody>

              </table>
            </div>

            {/* Pagination */}

            <div className="cases-pagination">

              <span>Case count unavailable</span>

              <label>
                Rows per page:

                <select disabled defaultValue="7">
                  <option>7</option>
                  <option>15</option>
                  <option>30</option>
                </select>
              </label>

              <div className="cases-actions">
                <button type="button" disabled>
                  ‹ Previous
                </button>

                <button type="button" disabled>
                  Next ›
                </button>
              </div>

            </div>
          </section>

          {/* Archive information */}

          <section className="cases-info">

            <span
              className="material-symbols-outlined"
              aria-hidden="true"
            >
              info
            </span>

            <div>
              <strong>
                Looking for past discharge logs or non-active ward runs?
              </strong>

              <p>
                Archive access will be available when
                supported by the backend.
              </p>
            </div>

            <div className="cases-actions">
              <button type="button" disabled>
                Export Shift CSV
              </button>

              <button type="button" disabled>
                View Protocol Guide
              </button>
            </div>

          </section>

        </main>
      </div>
    </div>
  );
}