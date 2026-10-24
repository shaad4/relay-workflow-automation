import { apiRequest } from "@/lib/api";

export function getDashboardOverview(range = "7d", { signal } = {}) {
  const timeout = AbortSignal.timeout(15000);
  return apiRequest(`/dashboard/overview?${new URLSearchParams({ range })}`, {
    method: "GET", signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
  });
}
