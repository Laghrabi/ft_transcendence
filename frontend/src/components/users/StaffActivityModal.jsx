import { useState, useEffect, useRef } from "react";

import {
    activateStaff,
    deactivateStaff,
} from "../../api/users";

import "../../styles/StaffActivityModal.css";

function StaffActivityModal({
    staff,
    action,
    onClose,
    onSuccess,
}) {
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);

    const dialogRef = useRef(null);
    const submittingRef = useRef(false);

    const isDeactivation = action === "deactivate";

    const actionLabel = isDeactivation
        ? "Deactivate"
        : "Activate";

    useEffect(() => {
        const dialog = dialogRef.current;

        dialog.showModal();

        return () => {
            dialog.close();
        };
    }, []);

    function closeModal() {
        if (submittingRef.current) {
            return;
        }

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

    async function handleSubmit() {
        if (submittingRef.current) {
            return;
        }

        submittingRef.current = true;
        setSubmitting(true);
        setError(null);

        let data;

        try {
            if (isDeactivation) {
                data = await deactivateStaff(staff.id);
            } else {
                data = await activateStaff(staff.id);
            }
        } catch (err) {
            setError(err.message);
            submittingRef.current = false;
            setSubmitting(false);
            return;
        }

        dialogRef.current?.close();

        onSuccess(
            data?.message ??
            `Staff account ${isDeactivation
                ? "deactivated"
                : "activated"} successfully.`
        );
    }

    return (
        <dialog
            ref={dialogRef}
            className="staff-activity-modal"
            aria-labelledby="staff-activity-title"
            aria-describedby="staff-activity-description"
            onClick={handleOverlayClick}
            onCancel={handleCancel}
        >
            <div className="staff-activity-content">

                <header className="staff-activity-header">
                    <div
                        className={
                            isDeactivation
                                ? "staff-activity-icon staff-activity-danger"
                                : "staff-activity-icon staff-activity-success"
                        }
                    >
                        <span className="material-symbols-outlined">
                            {isDeactivation
                                ? "person_off"
                                : "person_check"}
                        </span>
                    </div>

                    <h2 id="staff-activity-title">
                        {actionLabel} Staff Account
                    </h2>

                    <button
                        type="button"
                        className="staff-activity-close"
                        aria-label="Close confirmation"
                        onClick={closeModal}
                        disabled={submitting}
                    >
                        <span className="material-symbols-outlined">
                            close
                        </span>
                    </button>
                </header>

                <div className="staff-activity-body">

                    <p id="staff-activity-description">
                        Are you sure you want to{" "}
                        {actionLabel.toLowerCase()}{" "}
                        <strong>{staff.name}</strong>?
                    </p>

                    <div
                        className={
                            isDeactivation
                                ? "staff-activity-notice staff-activity-danger"
                                : "staff-activity-notice staff-activity-success"
                        }
                    >
                        <span className="material-symbols-outlined">
                            info
                        </span>

                        <p>
                            {isDeactivation
                                ? "This staff member will no longer be able to access CareFlow. Existing tasks and records will be preserved."
                                : "This staff member will regain access to CareFlow."}
                        </p>
                    </div>

                    {error && (
                        <p
                            className="staff-activity-error"
                            role="alert"
                        >
                            {error}
                        </p>
                    )}
                </div>

                <footer className="staff-activity-footer">
                    <button
                        type="button"
                        className="staff-activity-cancel"
                        onClick={closeModal}
                        disabled={submitting}
                    >
                        Cancel
                    </button>

                    <button
                        type="button"
                        className={
                            isDeactivation
                                ? "staff-activity-confirm staff-activity-confirm-danger"
                                : "staff-activity-confirm staff-activity-confirm-success"
                        }
                        onClick={handleSubmit}
                        disabled={submitting}
                    >
                        {submitting
                            ? isDeactivation
                                ? "Deactivating..."
                                : "Activating..."
                            : actionLabel}
                    </button>
                </footer>
            </div>
        </dialog>
    );
}

export default StaffActivityModal;