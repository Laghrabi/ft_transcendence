async function readResponse(response) {
  const data = await response.json().catch(() => null);

  if (response.ok && (!data || typeof data !== "object")) {
    throw new Error("The server returned an unexpected response. Please try again.");
  }

  if (!response.ok) {
    const message =
      (response.status >= 500
        ? "The authentication service is unavailable. Please try again later."
        : data?.error || data?.message || data?.detail ||
          (data && Object.values(data).flat().join(" "))) ||
      `Request failed (${response.status})`;

    throw new Error(message);
  }

  return data;
}

async function authFetch(url, options) {
  try {
    return await fetch(url, options);
  } catch {
    throw new Error("Unable to reach the authentication service. Please try again later.");
  }
}

async function getCsrfToken() {
  const response = await authFetch("/api/auth/csrf/", {
    credentials: "include",
  });

  const data = await readResponse(response);

  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith("csrftoken="));

  const token =
    data.csrfToken ||
    data.csrf_token ||
    (cookie ? decodeURIComponent(cookie.split("=")[1]) : null);

  if (!token) {
    throw new Error("Could not retrieve CSRF token.");
  }

  return token;
}

async function postAuth(endpoint, body) {
  const csrfToken = await getCsrfToken();

  const response = await authFetch(endpoint, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify(body),
  });

  return readResponse(response);
}

export function registerUser(name, email, password) {
  return postAuth("/api/auth/register/", {
    name,
    email,
    password,
  });
}

export function loginUser(email, password) {
  return postAuth("/api/auth/login/", {
    email,
    password,
  });
}

export async function getCurrentUser() {
  const response = await authFetch("/api/auth/me/", {
    credentials: "include",
  });

  return readResponse(response);
}
