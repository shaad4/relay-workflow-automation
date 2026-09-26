import { apiRequest } from "@/lib/api";

export async function getWorkflows(token) {
  return apiRequest("/workflows/", {
    method: "GET",
    headers: token
      ? {
          Authorization: `Bearer ${token}`,
        }
      : {},
  });
}
