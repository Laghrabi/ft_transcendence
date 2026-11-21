async function readResponse(response) {
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "An error occurred.");
  }
  return response.json();
}

export async function getNotifications() {
  const response = await fetch("/api/notifications/");

  const data = await readResponse(response);

  return data;
} 

