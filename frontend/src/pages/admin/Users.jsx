import { useState, useEffect } from "react";
import { getStaffMembers } from "../../api/users";

import Sidebar from "../../components/common/Sidebar";
import Topbar from "../../components/common/Topbar";
import StatCard from "../../components/common/StatCard";
import StaffDetailsModal from "../../components/users/StaffDetailsModal";

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
    const [openMenuId, setOpenMenuId] = useState(null);
    const [selectedStaffId, setSelectedStaffId] = useState(null);

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

    useEffect(() => {
        if (openMenuId === null) {
            return;
        }

        function handleOutsideClick(event) {
            if (
                event.target instanceof Element &&
                !event.target.closest(".users-actions")
            ) {
                setOpenMenuId(null);
            }
        }

        function handleEscape(event) {
            if (event.key === "Escape") {
                setOpenMenuId(null);

                document
                    .getElementById(`users-action-trigger-${openMenuId}`)
                    ?.focus();
            }
        }

        document.addEventListener("pointerdown", handleOutsideClick);
        document.addEventListener("keydown", handleEscape);

        return () => {
            document.removeEventListener("pointerdown", handleOutsideClick);
            document.removeEventListener("keydown", handleEscape);
        };
    }, [openMenuId]);

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

    function toggleMenu(staffId) {
        setOpenMenuId((previousId) =>
            previousId === staffId ? null : staffId
        );
    }

    function openStaffDetails(staffId) {
        setOpenMenuId(null);
        setSelectedStaffId(staffId);
    }

    function closeStaffDetails() {
        setSelectedStaffId(null);

        document
            .getElementById(`users-action-trigger-${selectedStaffId}`)
            ?.focus();
    }

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
                                            <div className="users-actions">
                                                <button
                                                    type="button"
                                                    id={`users-action-trigger-${staff.id}`}
                                                    className="users-action-trigger"
                                                    aria-label={`Actions for ${staff.name}`}
                                                    aria-expanded={openMenuId === staff.id}
                                                    onClick={() => toggleMenu(staff.id)}
                                                >
                                                    <span className="material-symbols-outlined">
                                                        more_horiz
                                                    </span>
                                                </button>

                                                {openMenuId === staff.id && (
                                                    <div className="users-action-menu">
                                                        <button
                                                            type="button"
                                                            className="users-action-option"
                                                            onClick={() => openStaffDetails(staff.id)}
                                                        >
                                                            <span className="material-symbols-outlined">
                                                                visibility
                                                            </span>
                                                            View Staff
                                                        </button>

                                                        {staff.can_activate === true && (
                                                            <button
                                                                type="button"
                                                                className="users-action-option users-action-activate"
                                                                disabled
                                                            >
                                                                <span className="material-symbols-outlined">
                                                                    person_check
                                                                </span>
                                                                Activate
                                                            </button>
                                                        )}

                                                        {staff.can_deactivate === true && (
                                                            <button
                                                                type="button"
                                                                className="users-action-option users-action-deactivate"
                                                                disabled
                                                            >
                                                                <span className="material-symbols-outlined">
                                                                    person_off
                                                                </span>
                                                                Deactivate
                                                            </button>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </section>
                </main>
            </div>
            {selectedStaffId !== null && (
                <StaffDetailsModal
                    key={selectedStaffId}
                    staffId={selectedStaffId}
                    staffSummary={staffMembers.find(
                        (staff) => staff.id === selectedStaffId
                    )}
                    onClose={closeStaffDetails}
                    getInitials={getInitials}
                />
            )}
        </div>
    );
}

export default Users;