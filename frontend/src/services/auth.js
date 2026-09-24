import { apiRequest } from "@/lib/api";

export async function registerUser(data) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function loginUser(data) {
  return apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function refreshToken(refresh_token) {
  return apiRequest("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({
      refresh_token,
    }),
  });
}

export async function logoutUser() {
  return apiRequest("/auth/logout", {
    method: "POST",
  });
}

export async function getCurrentUser(token) {
  return apiRequest("/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function forgotPassword(email) {
  return apiRequest("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({
      email,
    }),
  });
}

export async function resetPassword(token, newPassword) {
  return apiRequest("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({
      token,
      new_password: newPassword,
    }),
  });
}