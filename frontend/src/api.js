const API = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(`${API}/api/v1${path}`, {
      ...options,
      signal: controller.signal,
    });
    if (response.status === 204) return null;
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = body?.detail;
      throw new Error(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((e) => `${e.loc.join(".")}: ${e.msg}`).join("; ")
            : `Service returned HTTP ${response.status}. Please try again.`,
      );
    }
    if (!body) throw new Error("The server returned an unreadable response.");
    return body;
  } catch (error) {
    if (error.name === "AbortError")
      throw new Error("The request timed out. Please try again.");
    if (error instanceof TypeError)
      throw new Error(
        "Cannot reach the server. Check your connection and that the backend is running.",
      );
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
