const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TIMEOUT_MS = 60000; // AI generation can take a while; never hang forever

function getToken() {
  return localStorage.getItem("token");
}

// FastAPI validation errors (422) return detail as a list of {loc, msg}
function errorMessage(body, status) {
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail) && body.detail.length) {
    return body.detail
      .map((d) => {
        const field = d.loc?.[d.loc.length - 1];
        const msg = (d.msg || "").replace(/^Value error, /, "");
        return field && field !== "body" ? `${field.replace(/_/g, " ")}: ${msg}` : msg;
      })
      .join(". ");
  }
  if (status === 429) return "Too many requests. Please wait a moment and try again.";
  if (status >= 500) return "The server ran into a problem. Please try again.";
  return `HTTP ${status}`;
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...options, headers, signal: AbortSignal.timeout(TIMEOUT_MS) });
  } catch (err) {
    if (err.name === "TimeoutError") {
      throw new Error("The server took too long to respond. Please try again.", { cause: err });
    }
    throw new Error("Can't reach the server. Check your connection and try again.", { cause: err });
  }

  if (!res.ok) {
    // Session expired or revoked — drop the stale token and return to the login screen
    if (res.status === 401 && token && !path.startsWith("/api/auth/")) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.assign("/");
    }
    const body = await res.json().catch(() => ({}));
    const err = new Error(errorMessage(body, res.status));
    err.status = res.status; // e.g. 402 = plan limit reached
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get:    (path)        => request(path),
  post:   (path, body)  => request(path, { method: "POST",   body: JSON.stringify(body) }),
  put:    (path, body)  => request(path, { method: "PUT",    body: JSON.stringify(body) }),
  patch:  (path, body)  => request(path, { method: "PATCH",  body: JSON.stringify(body) }),
  delete: (path)        => request(path, { method: "DELETE" }),
};
