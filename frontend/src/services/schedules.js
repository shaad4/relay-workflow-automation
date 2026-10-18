import { apiRequest } from "@/lib/api";

export const createSchedule = (data) => apiRequest("/schedules/", { method: "POST", body: JSON.stringify(data), skipAuthRetry: true });
export const listSchedules = () => apiRequest("/schedules/", { method: "GET" });
export const getSchedule = (scheduleId) => apiRequest(`/schedules/${encodeURIComponent(scheduleId)}`, { method: "GET" });
export const updateSchedule = (scheduleId, data) => apiRequest(`/schedules/${encodeURIComponent(scheduleId)}`, { method: "PATCH", body: JSON.stringify(data) });
export const deleteSchedule = (scheduleId) => apiRequest(`/schedules/${encodeURIComponent(scheduleId)}`, { method: "DELETE", skipAuthRetry: true });
