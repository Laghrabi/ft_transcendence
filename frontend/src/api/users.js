export async function getStaffMembers() {
    const response = await fetch("/api/auth/users/", {
        method: "GET",
        credentials: "include",
    });

    if (!response.ok) {
        throw new Error(
            `Failed to retrieve staff members (${response.status})`
        );
    }

    const data = await response.json();

    return data;
}

export async function getStaffDetails(staffId) {
    const response = await fetch(
        `/api/auth/users/${staffId}/`,
        {
            method: "GET",
            credentials: "include",
        }
    );

    if (!response.ok) {
        throw new Error(
            `Failed to retrieve staff details (${response.status})`
        );
    }

    const data = await response.json();

    return data;
}

async function getCsrfToken() {
    const response = await fetch("/api/auth/csrf/", {
        method: "GET",
        credentials: "include",
    });

    if (!response.ok) {
        throw new Error("Failed to retrieve CSRF token.");
    }

    const data = await response.json();

    if (!data.csrf_token) {
        throw new Error("CSRF token is missing.");
    }

    return data.csrf_token;
}

async function postStaffAction(endpoint) {
    const csrfToken = await getCsrfToken();

    let response;

    try {
        response = await fetch(endpoint, {
            method: "POST",
            credentials: "include",
            headers: {
                "X-CSRFToken": csrfToken,
            },
        });
    } catch {
        throw new Error(
            "Unable to confirm the operation. Refresh the directory before retrying."
        );
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
        throw new Error(
            data?.message ||
            data?.detail ||
            data?.error ||
            `Request failed (${response.status}).`
        );
    }

    return data;
}

export function activateStaff(staffId) {
    return postStaffAction(
        `/api/auth/admin/users/${staffId}/activate/`
    );
}

export function deactivateStaff(staffId) {
    return postStaffAction(
        `/api/auth/admin/users/${staffId}/deactivate/`
    );
}
