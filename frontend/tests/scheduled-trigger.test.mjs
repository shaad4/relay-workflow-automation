import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createScheduleIfMissing, normalizeSchedule, validateSchedule, validCron, schedulePayload, scheduleNodePayload, scheduleStatus, scheduleDate } from "../src/components/workflow/scheduleTrigger.js";
import { validateNodeConfiguration } from "../src/components/workflow/configValidation.js";

test("interval and cron node configurations round-trip with incompatible fields cleared", () => {
  const interval = scheduleNodePayload(normalizeSchedule());
  assert.equal(interval.timezone, "Asia/Kolkata");
  assert.equal(interval.cron_expression, null);
  assert.equal("input_data" in interval, false); // node schema forbids this field
  assert.deepEqual(validateNodeConfiguration("trigger.schedule", JSON.parse(JSON.stringify(interval))), []);
  const cron = scheduleNodePayload({ ...interval, schedule_type: "cron", cron_expression: "0 9 * * 1-5" });
  assert.equal(cron.interval_minutes, null);
  assert.deepEqual(validateNodeConfiguration("trigger.schedule", cron), []);
  assert.equal(normalizeSchedule({ cron: "0 0 * * *", timezone: "UTC" }).schedule_type, "cron");
});
test("rejects invalid intervals, cron syntax, timezone and non-object input", () => {
  for (const interval_minutes of ["", 0, -1, 1.5, 10081, "abc"]) assert.ok(validateSchedule({ interval_minutes }).length);
  for (const interval_minutes of [1, 30, 10080]) assert.deepEqual(validateSchedule({ interval_minutes }), []);
  for (const expression of ["0 0 * *", "0 0 * * * *", "60 * * * *", "* 24 * * *", "*/0 * * * *", "* * 0 * *", "* * * 13 *", "* * * * 8", "* * * * 5-1", "* * * * ?"]) assert.equal(validCron(expression), false, expression);
  for (const expression of ["* * * * *", "*/15 9-17 * * MON-FRI", "0 9 1 JAN *", "0,30 * * * *"]) assert.equal(validCron(expression), true, expression);
  assert.ok(validateSchedule({ timezone: "not/a-zone" }).length);
  for (const input_data of [[], null, "{", 7, true]) assert.ok(validateSchedule({ input_data }).length);
});
test("schedule requests preserve pause and object input with no workspace/version fields", () => {
  const payload = schedulePayload({ enabled: false, input_data: { report_type: "daily" }, schedule_type: "cron", cron_expression: "0 9 * * *" });
  assert.equal(payload.enabled, false);
  assert.deepEqual(payload.input_data, { report_type: "daily" });
  assert.equal(payload.interval_minutes, null);
  assert.equal("workspace_id" in payload, false);
  assert.equal("workflow_version_id" in payload, false);
});
test("lifecycle statuses and backend timestamps remain distinct", () => {
  const workflow = { published_version_id: "version", status: "active" };
  assert.equal(scheduleStatus({}, true, null), "Publish required");
  assert.equal(scheduleStatus(workflow, false, null), "Schedule unavailable");
  assert.equal(scheduleStatus({ ...workflow, status: "inactive" }, true, { enabled: true }), "Workflow inactive");
  assert.equal(scheduleStatus(workflow, true, { enabled: false }), "Paused");
  assert.equal(scheduleStatus(workflow, true, { enabled: true }), "Not scheduled");
  assert.equal(scheduleStatus(workflow, true, { enabled: true, next_run_at: "2026-10-16T12:00:00Z" }), "Active");
  assert.equal(scheduleDate(null, "UTC"), "Not scheduled");
  assert.match(scheduleDate("2026-10-16T12:00:00Z", "Asia/Kolkata"), /5:30 PM/);
});
test("all schedule API operations use the existing gateway client with mock requests", async () => {
  const source = await readFile(new URL("../src/services/schedules.js", import.meta.url), "utf8");
  const requests = [];
  globalThis.__scheduleApiMock = async (...args) => { requests.push(args); return { id: "schedule" }; };
  try {
    const scheduleApi = await import(`data:text/javascript,${encodeURIComponent(source.replace('import { apiRequest } from "@/lib/api";', 'const apiRequest = globalThis.__scheduleApiMock;'))}`);
    await scheduleApi.createSchedule({ workflow_id: "workflow", ...schedulePayload({}) });
    await scheduleApi.listSchedules();
    await scheduleApi.getSchedule("schedule");
    await scheduleApi.updateSchedule("schedule", { enabled: false });
    await scheduleApi.deleteSchedule("schedule");
    assert.deepEqual(requests.map(([url, options]) => [url, options.method]), [["/schedules/", "POST"], ["/schedules/", "GET"], ["/schedules/schedule", "GET"], ["/schedules/schedule", "PATCH"], ["/schedules/schedule", "DELETE"]]);
    assert.equal(requests[0][1].skipAuthRetry, true);
    assert.equal(requests[4][1].skipAuthRetry, true);
    assert.deepEqual(JSON.parse(requests[3][1].body), { enabled: false });
  } finally { delete globalThis.__scheduleApiMock; }
});

test("creation reconciles authoritative state and never retries uncertain mutations", async () => {
  let creates = 0;
  const existing = { id: "existing", workflow_id: "workflow", enabled: false };
  const api = { listSchedules: async () => [existing], createSchedule: async () => { creates++; } };
  assert.equal(await createScheduleIfMissing("workflow", {}, api), existing);
  assert.equal(creates, 0);
  api.listSchedules = async () => [];
  api.createSchedule = async (payload) => { creates++; assert.equal(payload.workflow_id, "workflow"); throw new Error("timeout"); };
  await assert.rejects(createScheduleIfMissing("workflow", {}, api), /timeout/);
  assert.equal(creates, 1);
  api.listSchedules = async () => [existing];
  assert.equal(await createScheduleIfMissing("workflow", {}, api), existing);
  assert.equal(creates, 1);
  api.listSchedules = async () => { throw new Error("unavailable"); };
  await assert.rejects(createScheduleIfMissing("workflow", {}, api), /unavailable/);
  assert.equal(creates, 1);
});
