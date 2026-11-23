async function readResponse(response) {
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || `Notification request failed (${response.status}).`);
  }

  return data;
}

function isNotification(notification) {
  return Number.isInteger(notification?.id)
    && typeof notification.message === "string"
    && typeof notification.is_read === "boolean";
}

export async function getNotifications({ signal } = {}) {
  const response = await fetch("/api/notifications/", {
    credentials: "include",
    cache: "no-store",
    signal,
  });
  const data = await readResponse(response);

  if (!Array.isArray(data?.notifications) || !data.notifications.every(isNotification)) {
    throw new Error("The server returned an invalid notification list.");
  }

  return data;
}

async function getCsrfToken() {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith("csrftoken="));
  const cookieToken = cookie && decodeURIComponent(cookie.slice("csrftoken=".length));

  if (cookieToken) {
    return cookieToken;
  }

  const response = await fetch("/api/auth/csrf/", { credentials: "include" });
  const data = await response.json().catch(() => null);
  const token = data?.csrfToken || data?.csrf_token;

  if (!response.ok || !token) {
    throw new Error("Could not retrieve a CSRF token.");
  }

  return token;
}

export async function markNotificationRead(id) {
  const csrfToken = await getCsrfToken();
  const response = await fetch(`/api/notifications/${id}/read/`, {
    method: "PATCH",
    credentials: "include",
    headers: { "X-CSRFToken": csrfToken },
  });
  const notification = await readResponse(response);

  if (!isNotification(notification) || notification.id !== id || !notification.is_read) {
    throw new Error("The server did not confirm the notification was marked as read.");
  }

  return notification;
}
