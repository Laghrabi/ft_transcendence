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
