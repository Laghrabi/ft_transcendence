import { useState, useEffect } from "react";
import { getStaffMembers } from "../../api/users";

import Sidebar from "../../components/common/Sidebar";
import Topbar from "../../components/common/Topbar";
import StatCard from "../../components/common/StatCard";

import "../../styles/Common.css";
import "../../styles/Dashboard.css";
import "../../styles/Users.css";

function getInitials(name) {
    return name
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map((word) => word.charAt(0).toUpperCase())
        .join("");
}

function Users() {
    const [staffMembers, setStaffMembers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [activityFilter, setActivityFilter] = useState("all");

    useEffect(() => {
        let ignore = false;

        async function loadStaffMembers() {
            try {
                const data = await getStaffMembers();

                if (!ignore) {
                    setStaffMembers(data);
                }
            } catch (err) {
                if (!ignore) {
                    setError(err.message);
                }
            } finally {
                if (!ignore) {
                    setLoading(false);
                }
            }
        }

        loadStaffMembers();

        return () => {
            ignore = true;
        };
    }, []);

    const normalizedQuery = searchQuery.trim().toLowerCase();

    const filteredStaffMembers = staffMembers.filter((staff) => {
        const matchesSearch =
            staff.name.toLowerCase().includes(normalizedQuery) ||
            staff.email.toLowerCase().includes(normalizedQuery);

        const matchesActivity =
            activityFilter === "all" ||
            (activityFilter === "active" && staff.is_active) ||
            (activityFilter === "inactive" && !staff.is_active);

        return matchesSearch && matchesActivity;
    });

    return (
        <div className="cf-dashboard">
            <Sidebar />

            <div className="cf-page">
                <Topbar />

                <main className="cf-main">
                    <section className="cf-hero">
                        <div className="cf-hero-copy">
                            <h1>Users Management</h1>
                            <p>Manage hospital staff accounts.</p>
                        </div>
                    </section>

                    <section className="cf-stats">
                        <StatCard
                            label="TOTAL ACTIVE STAFF"
                            icon="groups"
                            color="green"
                            value="—"
                            description="Data unavailable"
                        />
                    </section>

                    <section className="users-directory">
                        <div className="users-directory-header">
                            <h2>Staff Directory</h2>

                            <div className="users-directory-controls">
                                <div className="users-search">
                                    <span className="material-symbols-outlined">
                                        search
                                    </span>

                                    <input
                                        type="search"
                                        placeholder="Search by name or email..."
                                        aria-label="Search staff by name or email"
                                        value={searchQuery}
                                        onChange={(event) =>
                                            setSearchQuery(event.target.value)
                                        }
                                    />
                                </div>

                                <select
                                    className="users-activity-filter"
                                    aria-label="Filter by account activity"
                                    value={activityFilter}
                                    onChange={(event) =>
                                        setActivityFilter(event.target.value)
                                    }
                                >
                                    <option value="all">All statuses</option>
                                    <option value="active">Active</option>
                                    <option value="inactive">Inactive</option>
                                </select>
                            </div>
                        </div>

                        <table className="users-table">
                            <thead>
                                <tr>
                                    <th>Staff Member</th>
                                    <th>Role</th>
                                    <th>Activity</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>

                            <tbody>
                                {loading && (
                                    <tr>
                                        <td colSpan={4}
                                            className="users-table-message">
                                            Loading staff members...
                                        </td>
                                    </tr>
                                )}

                                {!loading && error && (
                                    <tr>
                                        <td colSpan={4}
                                            className="users-table-message users-error">
                                            {error}
                                        </td>
                                    </tr>
                                )}

                                {!loading && !error &&
                                    staffMembers.length === 0 && (
                                    <tr>
                                        <td colSpan={4}
                                            className="users-table-message">
                                            No staff members found.
                                        </td>
                                    </tr>
                                )}

                                {!loading && !error &&
                                    staffMembers.length > 0 &&
                                    filteredStaffMembers.length === 0 && (
                                    <tr>
                                        <td
                                            colSpan={4}
                                            className="users-table-message"
                                        >
                                            No matching staff members.
                                        </td>
                                    </tr>
                                )}

                                {!loading && !error &&
                                    filteredStaffMembers.map((staff) => (
                                    <tr key={staff.id}>
                                        <td>
                                            <div className="users-staff">
                                                <div className="users-avatar">
                                                    {staff.avatar ? (
                                                        <img
                                                            src={staff.avatar}
                                                            alt=""
                                                        />
                                                    ) : (
                                                        getInitials(staff.name)
                                                    )}
                                                </div>

                                                <div className="users-staff-info">
                                                    <span className="users-staff-name">
                                                        {staff.name}
                                                    </span>

                                                    <span className="users-staff-email">
                                                        {staff.email}
                                                    </span>
                                                </div>
                                            </div>
                                        </td>

                                        <td>
                                            <div className="users-role">
                                                <span>
                                                    {staff.profession ?? "—"}
                                                </span>

                                                {staff.is_department_admin && (
                                                    <span className="users-admin-badge">
                                                        Administrator
                                                    </span>
                                                )}
                                            </div>
                                        </td>

                                        <td>
                                            <span
                                                className={
                                                    staff.is_active
                                                        ? "users-activity users-active"
                                                        : "users-activity users-inactive"
                                                }
                                            >
                                                {staff.is_active
                                                    ? "Active"
                                                    : "Inactive"}
                                            </span>
                                        </td>

                                        <td>
                                            <button
                                                type="button"
                                                aria-label={`Actions for ${staff.name}`}
                                            >
                                                ⋯
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </section>
                </main>
            </div>
        </div>
    );
}

export default Users;