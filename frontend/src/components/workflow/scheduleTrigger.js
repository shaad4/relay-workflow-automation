export const INTERVAL_PRESETS = [[5, "5 minutes"], [15, "15 minutes"], [30, "30 minutes"], [60, "1 hour"], [360, "6 hours"], [720, "12 hours"], [1440, "24 hours"]];
export const CRON_PRESETS = [["* * * * *", "Every minute"], ["0 * * * *", "Every hour"], ["0 9 * * *", "Daily at 9 AM"], ["0 9 * * 1", "Every Monday at 9 AM"], ["0 9 * * 1-5", "Weekdays at 9 AM"], ["0 9 1 * *", "First day of month at 9 AM"]];
export function normalizeSchedule(config = {}) {
  return {
    schedule_type: config.schedule_type ?? (config.cron || config.cron_expression ? "cron" : "interval"),
    interval_minutes: config.interval_minutes ?? 30,
    cron_expression: config.cron_expression ?? config.cron ?? "0 9 * * *",
    timezone: config.timezone ?? "Asia/Kolkata",
    enabled: config.enabled ?? true,
    input_data: config.input_data === undefined ? {} : config.input_data,
  };
}
export function validCron(expression) {
  const fields = String(expression ?? "").trim().split(/\s+/);
  if (fields.length !== 5) return false;
  const ranges = [[0, 59], [0, 23], [1, 31], [1, 12], [0, 7]];
  const aliases = [{}, {}, {}, { JAN: 1, FEB: 2, MAR: 3, APR: 4, MAY: 5, JUN: 6, JUL: 7, AUG: 8, SEP: 9, OCT: 10, NOV: 11, DEC: 12 }, { SUN: 0, MON: 1, TUE: 2, WED: 3, THU: 4, FRI: 5, SAT: 6 }];
  return fields.every((field, index) => field.split(",").every((part) => {
    const pieces = part.toUpperCase().split("/");
    if (pieces.length > 2 || (pieces.length === 2 && (!/^\d+$/.test(pieces[1]) || Number(pieces[1]) < 1))) return false;
    if (pieces[0] === "*") return true;
    const ends = pieces[0].split("-");
    if (ends.length > 2) return false;
    const values = ends.map((value) => /^\d+$/.test(value) ? Number(value) : aliases[index][value]);
    return values.every((value) => Number.isInteger(value) && value >= ranges[index][0] && value <= ranges[index][1]) && (values.length === 1 || values[0] <= values[1]);
  }));
}
export function validateSchedule(config) {
  const value = normalizeSchedule(config);
  const errors = [];
  if (!["interval", "cron"].includes(value.schedule_type)) errors.push({ field: "schedule_type", message: "Choose Interval or Cron." });
  if (value.schedule_type === "interval" && (value.interval_minutes === "" || !Number.isInteger(Number(value.interval_minutes)) || Number(value.interval_minutes) < 1 || Number(value.interval_minutes) > 10080)) errors.push({ field: "interval_minutes", message: "Enter a whole number from 1 to 10,080 minutes." });
  if (value.schedule_type === "cron" && (String(value.cron_expression).length > 100 || !validCron(value.cron_expression))) errors.push({ field: "cron_expression", message: "Enter a valid five-field cron expression (minute, hour, day, month, weekday)." });
  try { if (!value.timezone) throw new Error(); new Intl.DateTimeFormat("en", { timeZone: value.timezone }).format(); }
  catch { errors.push({ field: "timezone", message: "Choose a valid IANA timezone." }); }
  if (!value.input_data || typeof value.input_data !== "object" || Array.isArray(value.input_data)) errors.push({ field: "input_data", message: "Scheduled input must be a JSON object." });
  return errors;
}
export function schedulePayload(config) {
  const value = normalizeSchedule(config);
  return { ...value, interval_minutes: value.schedule_type === "interval" ? Number(value.interval_minutes) : null, cron_expression: value.schedule_type === "cron" ? value.cron_expression.trim() : null };
}
export function scheduleNodePayload(config) {
  const { input_data, ...payload } = schedulePayload(config);
  void input_data;
  return payload;
}
export function scheduleSummary(config) {
  const value = normalizeSchedule(config);
  if (validateSchedule(value).length) return "Complete the schedule configuration below.";
  if (value.schedule_type === "interval") return `Runs every ${value.interval_minutes} minute${Number(value.interval_minutes) === 1 ? "" : "s"}`;
  const preset = CRON_PRESETS.find(([expression]) => expression === value.cron_expression.trim());
  return `${preset ? `Runs ${preset[1].toLowerCase()}` : `Runs on cron ${value.cron_expression}`} (${value.timezone})`;
}
export function scheduleDate(value, timezone) {
  if (!value) return "Not scheduled";
  try { return new Intl.DateTimeFormat("en", { timeZone: timezone, dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }
  catch { return "Unavailable"; }
}
export function scheduleStatus(workflow, available, schedule) {
  if (!workflow?.published_version_id) return "Publish required";
  if (!available) return "Schedule unavailable";
  if (!["active", "published"].includes(String(workflow.status).toLowerCase())) return "Workflow inactive";
  if (!schedule) return "Ready to set up";
  return !schedule.enabled ? "Paused" : schedule.next_run_at ? "Active" : "Not scheduled";
}
export function scheduleError(error) {
  return ({ 401: "Your session has expired. Sign in again.", 404: "The workflow or schedule was not found. Refresh its state.", 409: "The schedule conflicts with the current workflow. Refresh, check that the workflow is active and its published version contains a Scheduled Trigger, then try again.", 422: "The schedule was rejected. Check the interval, five-field cron expression, timezone, and JSON input.", 503: "Scheduling is temporarily unavailable. Try again later.", 504: "The request timed out. Refresh schedule state before trying again." })[error?.status] || "The request could not be confirmed. Refresh schedule state before trying again.";
}

export async function createScheduleIfMissing(workflowId, config, api) {
  const response = await api.listSchedules();
  const rows = Array.isArray(response) ? response : response?.schedules || response?.results || response?.data || [];
  const existing = rows.find((schedule) => String(schedule.workflow_id) === String(workflowId));
  return existing || api.createSchedule({ workflow_id: workflowId, ...schedulePayload(config) });
}
