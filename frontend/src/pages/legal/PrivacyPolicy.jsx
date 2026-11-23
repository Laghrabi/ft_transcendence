
import "../../styles/PrivacyPolicy.css";
import { Link } from "react-router-dom";

function PrivacyPolicy() {
    return (
        <div className="privacy-screen">
            <main className="privacy-page">

                <header className="privacy-header">
                    <h1>CareFlow Privacy Policy</h1>

                    <p className="privacy-date">
                        Last updated: November 21, 2026
                    </p>

                    <p>
                        CareFlow is a hospital workflow coordination platform
                        designed to help healthcare staff manage cases, organize
                        tasks, communicate across departments, and monitor
                        operational progress.
                    </p>

                    <p>
                        This Privacy Policy explains the types of information
                        handled by CareFlow and how that information supports
                        the application's functionality.
                    </p>

                    <Link to="/login" className="privacy-back-link">
                        ← Back to Login
                    </Link>
                </header>

                <section className="privacy-section">
                    <h2>1. Information We Collect</h2>

                    <p>
                        CareFlow processes information related to staff accounts
                        and hospital operations.
                    </p>

                    <h3>Staff Account Information</h3>
                    <ul>
                        <li>Full name and work email address</li>
                        <li>Account login credentials</li>
                        <li>Professional role, such as doctor or nurse</li>
                        <li>Department information</li>
                    </ul>

                    <h3>Workflow Information</h3>
                    <ul>
                        <li>Hospital case information</li>
                        <li>Assigned tasks and responsibilities</li>
                        <li>Case comments and their authors</li>
                        <li>Case progress and workflow activities</li>
                    </ul>

                    <h3>Notification Information</h3>
                    <ul>
                        <li>
                            Messages about task assignments, reassignment,
                            and case updates
                        </li>
                        <li>The recipient of each notification</li>
                        <li>Notification creation dates and read status</li>
                    </ul>
                </section>

                <section className="privacy-section">
                    <h2>2. How We Use Your Information</h2>

                    <p>
                        CareFlow uses information to support hospital
                        coordination and staff communication.
                    </p>

                    <ul>
                        <li>Managing staff accounts and authentication</li>
                        <li>Organizing hospital cases and tasks</li>
                        <li>Supporting communication between staff members</li>
                        <li>Recording comments associated with cases</li>
                        <li>
                            Delivering notifications about workflow activity
                        </li>
                        <li>
                            Supporting visibility into task assignments
                            and case progress
                        </li>
                    </ul>

                    <p>
                        CareFlow is also designed to provide operational
                        reporting and Analytics features based on workflow
                        information.
                    </p>
                </section>

                <section className="privacy-section">
                    <h2>3. Access to Information</h2>

                    <p>
                        CareFlow is intended for hospital staff using the
                        application for operational coordination.
                    </p>

                    <p>
                        Authentication is required to access case comments
                        and personal notifications.
                    </p>

                    <p>
                        Notification records are associated with individual
                        staff accounts, and the notification API restricts
                        access to the recipient's own notifications.
                    </p>

                    <p>
                        Case comments are associated with their authors and
                        cases and can be accessed through the application's
                        authenticated collaboration features.
                    </p>

                    <p>
                        Staff should only enter, access, or share information
                        necessary for their authorized work.
                    </p>
                </section>

                <section className="privacy-section">
                    <h2>4. Authentication and Cookies</h2>

                    <p>
                        CareFlow uses session-based authentication to recognize
                        signed-in users.
                    </p>

                    <p>
                        Session cookies support access to authenticated
                        application features.
                    </p>

                    <p>
                        The application also uses Cross-Site Request Forgery
                        (CSRF) protection for relevant requests. CSRF tokens
                        help protect authenticated sessions against unauthorized
                        requests from other websites.
                    </p>

                    <p>
                        These mechanisms support the application's login
                        and request-handling functionality.
                    </p>
                </section>

                <section className="privacy-section">
                    <h2>5. Notifications and Communication</h2>

                    <p>
                        CareFlow supports notifications related to hospital
                        workflow activities, including task assignments,
                        task reassignments, and completed cases.
                    </p>

                    <p>
                        Notification messages are stored with their recipient,
                        creation time, and read status.
                    </p>

                    <p>
                        CareFlow also supports realtime notification delivery
                        through WebSocket connections, allowing authenticated
                        users to receive updates while using the application.
                    </p>

                    <p>
                        Case comments allow staff to record information
                        and communicate about workflow activities.
                    </p>
                </section>

                <section className="privacy-section">
                    <h2>6. Data Storage and Security</h2>

                    <p>
                        CareFlow uses a backend database to store application
                        records, including comments and notifications.
                    </p>

                    <p>
                        Its backend includes authentication and permission
                        checks for supported API operations.
                    </p>

                    <p>
                        The notification system uses authenticated connections
                        and delivers realtime updates to user-specific channels.
                    </p>

                    <p>
                        CareFlow's infrastructure also includes Redis for
                        realtime messaging and a reverse proxy for routing
                        application requests.
                    </p>

                    <p>
                        Users are responsible for protecting their login
                        credentials and avoiding the disclosure of sensitive
                        information through unauthorized channels.
                    </p>
                </section>

                <section className="privacy-section">
                    <h2>7. Your Information and Account Access</h2>

                    <p>
                        Staff members should use CareFlow in accordance with
                        their organization's data-handling and access policies.
                    </p>

                    <p>
                        Questions about account information, access permissions,
                        or corrections to records should be directed to the
                        administrator responsible for the CareFlow deployment.
                    </p>

                    <p>
                        CareFlow is designed to support operational coordination;
                        decisions about access to sensitive hospital information
                        must follow the organization's applicable privacy and
                        confidentiality requirements.
                    </p>
                </section>

                <section className="privacy-section">
                    <h2>8. Updates to This Policy</h2>

                    <p>
                        This Privacy Policy may be updated as CareFlow's
                        features and information-handling practices change.
                        The updated version will be made available through
                        the application.
                    </p>
                </section>

                <footer className="privacy-footer">
                    <p>© 2026 CareFlow</p>

                    <Link to="/login">
                        Back to Login
                    </Link>
                </footer>

            </main>
        </div>
    );
}

export default PrivacyPolicy;
