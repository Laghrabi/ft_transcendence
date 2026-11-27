import { useState, useRef } from "react";
import { Link } from "react-router-dom";
import Sidebar from "../../components/common/Sidebar";
import Topbar from "../../components/common/Topbar";
import Notifications from "../../components/common/Notifications";
import "../../styles/Dashboard.css";
import "../../styles/CreateCase.css";

export default function CreateCase() {
  const [showNotifications, setShowNotifications] = useState(false);
  const [notificationStatus, setNotificationStatus] = useState("loading");
  const [notificationRetry, setNotificationRetry] = useState(0);
  const [readStatus, setReadStatus] = useState({});
  const notificationButton = useRef(null);

  const [priority, setPriority] = useState("Medium");

  function retryNotifications() {
    setNotificationStatus("loading");
    setNotificationRetry((attempt) => attempt + 1);
  }

  return (
    <div className="cf-dashboard cf-create-case">
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

        <main className="cf-main create-main">
          <header className="create-header">
            <nav className="create-breadcrumb">
              <Link to="/cases">
                <span className="material-symbols-outlined">
                  folder_managed
                </span>
                Cases
              </Link>
              <span>/</span>
              <span>Initiate New Case</span>
            </nav>

            <h1>Initiate Operational Case</h1>

            <p>
              Launch a structured cross-department hospital
              coordination workflow using a workflow template.
            </p>
          </header>

          <form
            className="create-layout"
            onSubmit={(event) => event.preventDefault()}
          >
            <div className="create-left">
              <section className="create-section">
                <div className="create-section-heading">
                  <h2>
                    <span className="create-number">1</span>
                    Select Workflow Template
                  </h2>
                  <span className="create-tag">Required</span>
                </div>

                <p className="create-description">
                  Choose the standardized sequence that dictates
                  department handoffs and dependencies.
                </p>

                {/* TODO: Get workflow templates from backend */}

                <div className="create-templates">
                  {[1, 2, 3, 4].map((number) => (
                    <div className="create-template" key={number}>
                      <span className="create-template-icon material-symbols-outlined">
                        account_tree
                      </span>

                      <h3>Workflow Template</h3>
                      <p>Template data unavailable</p>

                      <div className="create-template-details">
                        <span>— Ordered Steps</span>
                        <span>SLA: —</span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section className="create-section">
                <div className="create-section-heading">
                  <h2>
                    <span className="create-number">2</span>
                    Operational Parameters
                  </h2>
                  <small>Routing Metadata</small>
                </div>

                <div className="create-fields">
                  {/* TODO: Get departments and coordinators from backend */}

                  <label className="create-field">
                    <span>Originating Department *</span>
                    <select disabled>
                      <option>Select department</option>
                    </select>
                  </label>

                  <label className="create-field">
                    <span>Initial Case Coordinator *</span>
                    <select disabled>
                      <option>Select coordinator</option>
                    </select>
                  </label>

                  <div className="create-priority">
                    <p>Priority & Dispatch Urgency *</p>

                    <div className="create-priority-options">
                      {["Low", "Medium", "High", "Urgent"].map((level) => (
                        <button
                          key={level}
                          type="button"
                          aria-pressed={priority === level}
                          className={`priority-option ${level.toLowerCase()} ${
                            priority === level ? "selected" : ""
                          }`}
                          onClick={() => setPriority(level)}
                        >
                          <span className="priority-dot"></span>
                          {level}
                        </button>
                      ))}
                    </div>
                  </div>

                  <label className="create-field">
                    <span>Location / Bed / Ref ID *</span>
                    <input
                      type="text"
                      placeholder="Enter operational reference"
                      required
                    />
                    <small>
                      Do not enter sensitive patient data.
                    </small>
                  </label>

                  <label className="create-field">
                    <span>Target Completion SLA *</span>
                    <input
                      type="text"
                      placeholder="Not available yet"
                      disabled
                    />
                    <small>
                      Based on workflow and priority.
                    </small>
                  </label>
                </div>
              </section>

              <section className="create-section">
                <div className="create-section-heading">
                  <h2>
                    <span className="create-number">3</span>
                    Coordination & Dispatch Brief
                  </h2>
                </div>

                <textarea
                  aria-label="Coordination and dispatch brief"
                  placeholder="Enter operational coordination instructions..."
                  rows="4"
                />

                <small>
                  Do not include sensitive patient information.
                </small>
              </section>
            </div>

            <div className="create-right">
              <section className="create-blueprint">
                <div className="create-section-heading">
                  <h2>
                    <span className="material-symbols-outlined">
                      route
                    </span>
                    Execution Blueprint
                  </h2>
                  <span className="create-tag">Preview</span>
                </div>

                <div className="create-blueprint-info">
                  <span className="material-symbols-outlined">
                    account_tree
                  </span>
                  <p>
                    The workflow sequence will appear here when
                    a template is available and selected.
                  </p>
                </div>

                <p className="create-preview-title">
                  Sequence Preview
                </p>

                {/* TODO: Display workflow tasks from backend */}

                <div className="create-empty">
                  <span className="material-symbols-outlined">
                    account_tree
                  </span>
                  <p>No workflow preview available</p>
                </div>
              </section>

              <section className="create-section create-actions">
                <div className="create-section-heading">
                  <span>Pre-Flight Check</span>
                  <span className="create-tag">Incomplete</span>
                </div>

                {/* TODO: Connect case creation to backend */}

                <button
                  className="create-submit"
                  type="submit"
                  disabled
                >
                  Create & Launch Workflow
                  <span className="material-symbols-outlined">
                    arrow_forward
                  </span>
                </button>

                <Link className="create-cancel" to="/cases">
                  Cancel & Return to Cases
                </Link>
              </section>
            </div>
          </form>
        </main>
      </div>
    </div>
  );
}