import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { parseTriggerPayload, readPayloadDraft, writePayloadDraft, clearPayloadDraft, payloadDraftFromSchedule, createScheduleIfMissing, normalizeSchedule, validateSchedule, validCron, schedulePayload, scheduleNodePayload, scheduleStatus, scheduleDate } from "../src/components/workflow/scheduleTrigger.js";
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


test("optional trigger payload accepts objects and empty text with distinct validation errors", () => {
  for (const text of ["", "   ", "{}"]) assert.deepEqual(parseTriggerPayload(text), { input: {} });
  const input = { report_type: "daily", department: "sales", enabled: true, count: 10 };
  assert.deepEqual(parseTriggerPayload(JSON.stringify(input)), { input });
  assert.match(parseTriggerPayload('{"report_type":').error, /Invalid JSON format/);
  for (const text of ["[]", "null", '"text"', "4", "true"]) assert.match(parseTriggerPayload(text).error, /must be a JSON object/);
});

test("schedule load formats saved input and never overwrites unsaved or invalid editor text", () => {
  const clean = { text: "{}", dirty: false };
  assert.deepEqual(payloadDraftFromSchedule(clean, { input_data: null }), clean);
  assert.deepEqual(payloadDraftFromSchedule(clean, {}), clean);
  assert.equal(payloadDraftFromSchedule(clean, { input_data: { department: "sales" } }).text, '{\n  "department": "sales"\n}');
  for (const text of ['{\n  "unfinished":', '{"department":"finance"}', ""]) {
    const dirty = { text, dirty: true };
    assert.equal(payloadDraftFromSchedule(dirty, { input_data: { department: "sales" } }), dirty);
  }
});

test("payload drafts survive publishing remounts and reloads until a confirmed save clears them", async () => {
  const entries = new Map();
  const storage = { getItem: (key) => entries.get(key) ?? null, setItem: (key, value) => entries.set(key, value), removeItem: (key) => entries.delete(key) };
  const workflowId = "payload-test-workflow";
  const text = '{\n  "test_id": "SCHEDULE-001"\n}';
  writePayloadDraft(workflowId, text, storage);
  assert.deepEqual(readPayloadDraft(workflowId, storage), { text, dirty: true });
  assert.deepEqual(readPayloadDraft("other-workflow", storage), { text: "{}", dirty: false });
  const reloaded = await import("../src/components/workflow/scheduleTrigger.js?payload-reload");
  assert.deepEqual(reloaded.readPayloadDraft(workflowId, storage), { text, dirty: true });
  clearPayloadDraft(workflowId, storage);
  assert.deepEqual(readPayloadDraft(workflowId, storage), { text: "{}", dirty: false });
  const blockedStorage = { getItem() { throw new Error(); }, setItem() { throw new Error(); }, removeItem() { throw new Error(); } };
  writePayloadDraft(workflowId, "{", blockedStorage);
  assert.deepEqual(readPayloadDraft(workflowId, blockedStorage), { text: "{", dirty: true });
  clearPayloadDraft(workflowId, blockedStorage);
});

test("payload-only updates persist to the existing schedule and reload from the API", async () => {
  const source = await readFile(new URL("../src/services/schedules.js", import.meta.url), "utf8");
  let saved = { id: "existing-payload-schedule", workflow_id: "workflow", enabled: false, schedule_type: "interval", interval_minutes: 30, input_data: {} };
  const requests = [];
  globalThis.__payloadApiMock = async (url, options) => {
    requests.push([url, options]);
    if (options.method === "PATCH") saved = { ...saved, ...JSON.parse(options.body) };
    return { ...saved };
  };
  try {
    const api = await import(`data:text/javascript,${encodeURIComponent(source.replace('import { apiRequest } from "@/lib/api";', 'const apiRequest = globalThis.__payloadApiMock;'))}`);
    const payload = parseTriggerPayload('{"report_name":"Daily Sales","test_id":"SCHEDULE-001"}');
    await api.updateSchedule(saved.id, { input_data: payload.input });
    const loaded = await api.getSchedule(saved.id);
    assert.deepEqual(JSON.parse(requests[0][1].body), { input_data: payload.input });
    assert.deepEqual(loaded.input_data, payload.input);
    assert.equal(loaded.enabled, false);
    assert.equal(loaded.interval_minutes, 30);
    assert.equal(requests.some(([, options]) => options.method === "POST"), false);
    assert.deepEqual(parseTriggerPayload(payloadDraftFromSchedule({ text: "{}", dirty: false }, loaded).text).input, payload.input);
    const created = schedulePayload({ ...normalizeSchedule(), input_data: payload.input });
    assert.deepEqual(created.input_data, payload.input);
    assert.equal("input_data" in scheduleNodePayload(created), false);
  } finally { delete globalThis.__payloadApiMock; }
});

test("payload textarea is visible above live schedule for draft and published inspectors", async () => {
  const { transform, loadBindings } = await import("next/dist/build/swc/index.js");
  await loadBindings();
  const React = await import("react");
  const { renderToStaticMarkup } = await import("react-dom/server");
  const { createRequire } = await import("node:module");
  const require = createRequire(import.meta.url);
  const helpers = await import("../src/components/workflow/scheduleTrigger.js");
  const source = await readFile(new URL("../src/components/workflow/ScheduleConfig.jsx", import.meta.url), "utf8");
  const compiled = await transform(source, { filename: "ScheduleConfig.jsx", jsc: { parser: { syntax: "ecmascript", jsx: true }, transform: { react: { runtime: "automatic" } } }, module: { type: "commonjs" } });
  const exports = {};
  const importMock = (name) => name === "./scheduleTrigger" ? helpers : name.startsWith("@/services/") ? {} : require(name);
  new Function("require", "exports", compiled.code)(importMock, exports);
  for (const isReadOnly of [false, true]) {
    const markup = renderToStaticMarkup(React.createElement(exports.default, { config: normalizeSchedule(), onChange() {}, workflowId: "visible-payload-test", isReadOnly }));
    assert.match(markup, /Trigger Payload \(JSON\)/);
    assert.match(markup, /Optional/);
    assert.match(markup, /<textarea[^>]*id="schedule-trigger-payload"[^>]*>\{\}<\/textarea>/);
    assert.ok(markup.indexOf('id="schedule-trigger-payload"') < markup.indexOf('aria-label="Live schedule"'));
    assert.match(markup, /trigger.data.field_name/);
  }
});
