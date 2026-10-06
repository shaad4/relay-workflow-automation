const API_URL = process.env.NEXT_PUBLIC_AUTH_API_URL;

let refreshPromise = null;

function parseResponse(response, text) {
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

function getErrorMessage(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item.msg === "string") {
          const field = Array.isArray(item.loc)
            ? item.loc.filter((part) => part !== "body").join(".")
            : "";
          return field ? `${field}: ${item.msg}` : item.msg;
        }
        return null;
      })
      .filter(Boolean);
    if (messages.length) return messages.join(" ");
  }
  if (detail && typeof detail === "object") {
    if (typeof detail.message === "string") return detail.message;
    if (typeof detail.msg === "string") return detail.msg;
  }
  return null;
}

export async function refreshAuthTokens() {
  if (refreshPromise) return refreshPromise;
  const refresh = async () => {
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
    const text = await response.text();
    const data = parseResponse(response, text);
    if (!response.ok) {
      window.dispatchEvent(new CustomEvent("relay:session-expired"));
      return null;
    }
    return data;
  };
  const runRefresh = async () => {
    if (typeof navigator !== "undefined" && navigator.locks?.request) {
      return navigator.locks.request("relay-refresh-token", refresh);
    }
    return refresh();
  };

  refreshPromise = runRefresh().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

export async function apiRequest(
  endpoint,
  options = {}
) {
  const request = (requestOptions) => fetch(`${API_URL}${endpoint}`, {
    ...requestOptions,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(requestOptions.headers || {}),
    },
  });

  let response = await request(options);
  let text = await response.text();
  let data = parseResponse(response, text);

  const isRefreshRequest = endpoint === "/auth/refresh";
  if (response.status === 401 && !isRefreshRequest && typeof window !== "undefined") {
    const refreshedTokens = await refreshAuthTokens();
    if (refreshedTokens) {
      response = await request(options);
      text = await response.text();
      data = parseResponse(response, text);
    }
  }

  if (!response.ok) {
    const error = new Error(
      getErrorMessage(data.detail) ||
        getErrorMessage(data.message) ||
        "Something went wrong"
    );
    error.status = response.status;
    throw error;
  }

  return data;
}
