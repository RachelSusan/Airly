// Fetch wrapper: JSON in, JSON out, friendly errors.

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

const DEFAULT_ERROR = "Something went wrong. Please try again.";

async function request(path, { method = "GET", body } = {}) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("You seem to be offline. Check your connection and try again.", 0);
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    // non-JSON body; handled below
  }
  if (!response.ok) {
    throw new ApiError(data?.error?.message ?? DEFAULT_ERROR, response.status);
  }
  return data;
}

export const api = {
  geocode: (q, country) =>
    request(`/api/geocode?q=${encodeURIComponent(q)}${country ? `&country=${country}` : ""}`),
  air: ({ lat, lon }) => request(`/api/air?lat=${lat}&lon=${lon}`),
  grid: ({ lat, lon }) => request(`/api/air/grid?lat=${lat}&lon=${lon}`),
  plan: (body) => request("/api/plan", { method: "POST", body }),
  chat: (body) => request("/api/chat", { method: "POST", body }),
  scenarios: () => request("/api/scenarios"),
  simulate: (body) => request("/api/simulate", { method: "POST", body }),
};
