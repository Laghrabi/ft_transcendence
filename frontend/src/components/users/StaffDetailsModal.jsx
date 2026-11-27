import { useState, useEffect, useRef } from "react";
import { getStaffDetails } from "../../api/users";

import "../../styles/StaffDetailsModal.css";

function StaffDetailsModal({
    staffId,
    staffSummary,
    onClose,
    getInitials
}) {
    const [staffDetails, setStaffDetails] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const dialogRef = useRef(null);

    useEffect(() => {
        const dialog = dialogRef.current;

        dialog.showModal();

        return () => {
            dialog.close();
        };
    }, []);

    useEffect(() => {
        let ignore = false;

        async function loadStaffDetails() {
            try {
                const data = await getStaffDetails(staffId);

                if (!ignore) {
                    setStaffDetails(data);
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

        loadStaffDetails();

        return () => {
            ignore = true;
        };
    }, [staffId]);

    function closeModal() {
        dialogRef.current.close();
        onClose();
    }

    function handleOverlayClick(event) {
        if (event.target === event.currentTarget) {
            closeModal();
        }
    }

    function handleCancel(event) {
        event.preventDefault();
        closeModal();
    }

    const memberships = staffDetails?.department_memberships;
    const hasMembershipsData = Array.isArray(memberships);

    const staffName =
        staffDetails?.name ?? staffSummary?.name;

    const isActive =
        staffDetails?.is_active ?? staffSummary?.is_active;

    const dateJoined =
        staffDetails?.date_joined ?? staffSummary?.date_joined;

    const createdDate = dateJoined ? new Date(dateJoined) : null;

    const accountCreated =
        createdDate && !Number.isNaN(createdDate.getTime())
            ? createdDate.toLocaleString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
            })
            : "Not available";

    return (
        <dialog
            ref={dialogRef}
            className="staff-details-modal"
            aria-labelledby="staff-details-title"
            onClick={handleOverlayClick}
            onCancel={handleCancel}
        >
            <div className="staff-details-content">

                {/* Modal header */}
                <header className="staff-details-header">
                    <div className="staff-details-header-icon">
                        <span
                            className="material-symbols-outlined"
                            aria-hidden="true"
                        >
                            person
                        </span>
                    </div>

                    <div className="staff-details-heading">
                        <h2 id="staff-details-title">
                            Staff Details{staffName ? `: ${staffName}` : ""}
                        </h2>

                        <p>
                            View staff information, department
                            assignments, and roles.
                        </p>
                    </div>

                    <button
                        type="button"
                        className="staff-details-close"
                        aria-label="Close staff details"
                        onClick={closeModal}
                    >
                        <span className="material-symbols-outlined">
                            close
                        </span>
                    </button>
                </header>

                <div className="staff-details-body">

                    {loading && (
                        <p className="staff-details-message">
                            Loading staff details...
                        </p>
                    )}

                    {!loading && error && (
                        <p className="staff-details-message staff-details-error">
                            {error}
                        </p>
                    )}

                    {!loading && !error && staffDetails && (
                        <>
                            {/* Staff profile */}
                            <section className="staff-details-profile">

                                <div className="staff-details-avatar">
                                    {staffDetails.avatar ? (
                                        <img
                                            src={staffDetails.avatar}
                                            alt=""
                                        />
                                    ) : (
                                        getInitials(staffDetails.name)
                                    )}
                                </div>

                                <div className="staff-details-identity">
                                    <h3>{staffDetails.name}</h3>

                                    <div className="staff-details-info-row">
                                        <span className="material-symbols-outlined">
                                            mail
                                        </span>

                                        <span>{staffDetails.email}</span>
                                    </div>

                                    <div className="staff-details-info-row">
                                        <span className="material-symbols-outlined">
                                            badge
                                        </span>

                                        <span>ID #{staffId}</span>
                                    </div>
                                </div>

                                {typeof isActive === "boolean" && (
                                    <div
                                        className={
                                            isActive
                                                ? "staff-details-status staff-details-active"
                                                : "staff-details-status staff-details-inactive"
                                        }
                                    >
                                        <span className="staff-details-status-dot" />

                                        {isActive ? "Active" : "Inactive"}
                                    </div>
                                )}
                            </section>

                            {/* Department assignments */}
                            {hasMembershipsData && (
                                <section className="staff-details-departments">

                                    <div className="staff-details-section-header">
                                        <div className="staff-details-section-icon">
                                            <span className="material-symbols-outlined">
                                                layers
                                            </span>
                                        </div>

                                        <div>
                                            <h3>Department Assignments</h3>

                                            <p>
                                                Departments the staff member
                                                belongs to and their role in each.
                                            </p>
                                        </div>
                                    </div>

                                    {memberships.length === 0 ? (
                                        <p className="staff-details-empty">
                                            No department memberships.
                                        </p>
                                    ) : (
                                        <div className="staff-details-table-wrapper">
                                            <table className="staff-details-table">
                                                <thead>
                                                    <tr>
                                                        <th>Department</th>
                                                        <th>Role</th>
                                                    </tr>
                                                </thead>

                                                <tbody>
                                                    {memberships.map((membership) => (
                                                        <tr key={membership.department_id}>

                                                            <td>
                                                                <div className="staff-details-department">

                                                                    <div className="staff-details-department-icon">
                                                                        <span className="material-symbols-outlined">
                                                                            apartment
                                                                        </span>
                                                                    </div>

                                                                    <div className="staff-details-department-info">
                                                                        <span>
                                                                            {membership.department_name}
                                                                        </span>

                                                                        {membership.department_is_active === false && (
                                                                            <small>
                                                                                Inactive department
                                                                            </small>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </td>

                                                            <td>
                                                                <span className="staff-details-role">
                                                                    {membership.role_name}
                                                                </span>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </section>
                            )}

                            {/* Account creation information */}
                            <section className="staff-details-created">

                                <span className="material-symbols-outlined">
                                    assignment_ind
                                </span>

                                <div>
                                    <p>Account Created</p>

                                    <strong>{accountCreated}</strong>
                                </div>
                            </section>
                        </>
                    )}
                </div>
            </div>
        </dialog>
    );
}

export default StaffDetailsModal;