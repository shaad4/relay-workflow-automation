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

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return null;
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    const text = await response.text();
    const data = parseResponse(response, text);
    if (!response.ok || !data.access_token) {
      localStorage.removeItem("refresh_token");
      window.dispatchEvent(new CustomEvent("relay:session-expired"));
      return null;
    }
    localStorage.setItem("access_token", data.access_token);
    window.dispatchEvent(new CustomEvent("relay:access-token", { detail: data.access_token }));
    return data.access_token;
  })().finally(() => {
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
    const accessToken = await refreshAccessToken();
    if (accessToken) {
      const headers = new Headers(options.headers || {});
      if (headers.has("Authorization") || options.headers?.authorization) {
        headers.set("Authorization", `Bearer ${accessToken}`);
      }
      response = await request({ ...options, headers: Object.fromEntries(headers.entries()) });
      text = await response.text();
      data = parseResponse(response, text);
    }
  }

  if (!response.ok) {
    throw new Error(
      data.detail || data.message || "Something went wrong"
    );
  }

  return data;
}
