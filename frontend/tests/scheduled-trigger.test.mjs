import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { retryScheduleActivation, publishWithSchedule, reconcilePublishedSchedule, refreshScheduleConfiguration, parseTriggerPayload, readPayloadDraft, writePayloadDraft, clearPayloadDraft, payloadDraftFromSchedule, createScheduleIfMissing, normalizeSchedule, validateSchedule, validCron, schedulePayload, scheduleNodePayload, scheduleStatus, scheduleDate } from "../src/components/workflow/scheduleTrigger.js";
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
  assert.equal(scheduleStatus(workflow, true, { enabled: false, workflow_version_id: "version" }), "Paused");
  assert.equal(scheduleStatus(workflow, true, { enabled: true, workflow_version_id: "version" }), "Scheduling needs attention");
  assert.equal(scheduleStatus(workflow, true, { enabled: true, workflow_version_id: "version", next_run_at: "2026-10-16T12:00:00Z" }), "Active");
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
  const controlsSource = await readFile(new URL("../src/components/workflow/InspectorControls.jsx", import.meta.url), "utf8");
  const controlsCompiled = await transform(controlsSource, { filename: "InspectorControls.jsx", jsc: { parser: { syntax: "ecmascript", jsx: true }, transform: { react: { runtime: "automatic" } } }, module: { type: "commonjs" } });
  const controls = {};
  new Function("require", "exports", controlsCompiled.code)(require, controls);
  const exports = {};
  const importMock = (name) => name === "./InspectorControls" ? controls : name === "./scheduleTrigger" ? helpers : name.startsWith("@/services/") ? {} : require(name);
  new Function("require", "exports", compiled.code)(importMock, exports);
  for (const isReadOnly of [false, true]) {
    const markup = renderToStaticMarkup(React.createElement(exports.default, { config: normalizeSchedule(), onChange() {}, workflowId: "visible-payload-test", isReadOnly }));
    assert.match(markup, /Trigger Payload \(JSON\)/);
    assert.match(markup, /Optional/);
    const payloadTag = markup.match(/<textarea[^>]*id="schedule-trigger-payload"[^>]*>/)[0];
    assert.equal(payloadTag.includes('readOnly=""'), isReadOnly);
    assert.ok(!payloadTag.includes('disabled=""'));
    if (isReadOnly) {
      assert.ok(!markup.match(/<fieldset[^>]*disabled=""/));
      assert.match(markup, /<button[^>]*aria-label="Schedule enabled"[^>]*disabled=""/);
      assert.match(markup, /<input[^>]*aria-label="Interval in minutes"[^>]*readOnly=""/);
      assert.match(markup, /<input[^>]*readOnly=""[^>]*value="Asia\/Kolkata"/);
    }
    assert.match(markup, /<textarea[^>]*id="schedule-trigger-payload"[^>]*>\{\}<\/textarea>/);
    assert.ok(markup.indexOf('id="schedule-trigger-payload"') < markup.indexOf('aria-label="Live schedule"'));
    assert.match(markup, /trigger.data.field_name/);
  }
});

function publishingFixture({ existing, trigger = "trigger.schedule", failPublish, failCreate, concurrent } = {}) {
  const calls = [];
  let workflow = { id: "workflow", status: "draft", published_version_id: null };
  let schedule = existing;
  const config = { schedule_type: "interval", interval_minutes: 5, cron_expression: null, timezone: "Asia/Kolkata", enabled: true };
  const api = {
    publishWorkflow: async () => {
      calls.push("publish");
      if (failPublish === "before") throw new Error("Validation failed");
      workflow = { ...workflow, status: "active", published_version_id: "version" };
      if (schedule) schedule = { ...schedule, workflow_version_id: "version" };
      if (failPublish === "after") throw Object.assign(new Error("Schedule synchronization could not be confirmed"), { status: 503 });
    },
    getWorkflow: async () => { calls.push("workflow"); return { ...workflow }; },
    getWorkflowVersions: async () => [{ id: "version", version: 2, status: "published" }],
    getWorkflowNodes: async () => [{ node_type: trigger, configuration: config }],
    listSchedules: async () => { calls.push("list"); return schedule ? [{ ...schedule }] : []; },
    getSchedule: async () => { calls.push("get"); return { ...schedule }; },
    createSchedule: async (data) => {
      calls.push(["create", data]);
      if (concurrent) {
        schedule = { ...data, id: "concurrent", workflow_version_id: "version", next_run_at: "2026-10-18T12:00:00Z" };
        throw Object.assign(new Error("Duplicate"), { status: 409 });
      }
      if (failCreate) throw Object.assign(new Error("Unavailable"), { status: 503 });
      schedule = { ...data, id: "new", workflow_version_id: "version", next_run_at: data.enabled ? "2026-10-18T12:00:00Z" : null };
      return { ...schedule };
    },
    updateSchedule: async (id, changes) => { calls.push(["update", id, changes]); schedule = { ...schedule, ...changes, next_run_at: schedule.enabled ? "2026-10-18T12:00:00Z" : null }; return { ...schedule }; },
  };
  return { api, calls, config };
}

test("Publish confirms publication before creating exactly one schedule using saved configuration and payload", async () => {
  const { api, calls } = publishingFixture();
  const result = await publishWithSchedule("workflow", 2, "version", { dirty: true, text: '{"test_id":"scheduled"}' }, api);
  assert.equal(result.workflow.status, "active");
  assert.equal(result.schedule.interval_minutes, 5);
  assert.equal(result.schedule.timezone, "Asia/Kolkata");
  assert.equal(result.schedule.workflow_version_id, "version");
  assert.ok(result.schedule.next_run_at);
  assert.deepEqual(result.schedule.input_data, { test_id: "scheduled" });
  const creates = calls.filter((call) => Array.isArray(call) && call[0] === "create");
  assert.equal(creates.length, 1);
  assert.ok(calls.indexOf("publish") < calls.indexOf("workflow"));
  assert.ok(calls.indexOf("workflow") < calls.indexOf(creates[0]));
});

test("Republish updates existing interval, keeps its ID, preserves payload and manual pause", async () => {
  for (const enabled of [true, false]) {
    const { api, calls } = publishingFixture({ existing: { id: "existing", workflow_id: "workflow", workflow_version_id: "old", schedule_type: "interval", interval_minutes: 30, cron_expression: null, timezone: "Asia/Kolkata", enabled, next_run_at: enabled ? "2026-10-18T12:00:00Z" : null, input_data: { report: "keep" } } });
    const result = await publishWithSchedule("workflow", 2, "version", { dirty: false, text: "{}" }, api);
    assert.equal(result.schedule.id, "existing");
    assert.equal(result.schedule.workflow_version_id, "version");
    assert.equal(result.schedule.interval_minutes, 5);
    assert.equal(result.schedule.enabled, enabled);
    assert.deepEqual(result.schedule.input_data, { report: "keep" });
    if (!enabled) assert.equal(result.schedule.next_run_at, null);
    assert.equal(calls.filter((call) => call[0] === "create").length, 0);
    assert.deepEqual(calls.find((call) => call[0] === "update")[2], { interval_minutes: 5 });
    const again = await reconcilePublishedSchedule("workflow", { dirty: false }, api);
    assert.equal(again.schedule.id, "existing");
    assert.equal(calls.filter((call) => call[0] === "update").length, 1);
  }
});

test("Publish failures before commit never create schedules; post-commit failures retain published state", async () => {
  const failed = publishingFixture({ failPublish: "before" });
  await assert.rejects(publishWithSchedule("workflow", 2, "version", {}, failed.api), /Validation failed/);
  assert.equal(failed.calls.includes("list"), false);
  const committed = publishingFixture({ failPublish: "after" });
  let published = false;
  const outcome = await publishWithSchedule("workflow", 2, "version", {}, committed.api, () => { published = true; });
  assert.equal(published, true);
  assert.equal(outcome.workflow.status, "active");
  assert.match(outcome.publicationWarning, /synchronization/);
  assert.ok(outcome.schedule);
});

test("Schedule POST failure leaves publication intact and retry reconciles without republishing", async () => {
  const { api, calls } = publishingFixture({ failCreate: true });
  let published = false;
  const result = await publishWithSchedule("workflow", 2, "version", {}, api, () => { published = true; });
  assert.equal(published, true);
  assert.equal(result.workflow.status, "active");
  assert.match(result.schedulingError, /unavailable/);
  assert.equal(calls.filter((call) => call[0] === "create").length, 1);
  assert.equal(calls.filter((call) => call === "list").length, 2);
  api.createSchedule = async (data) => ({ ...data, id: "recovered", workflow_version_id: "version", next_run_at: "2026-10-18T12:00:00Z" });
  api.getSchedule = async () => ({ id: "recovered", enabled: true, workflow_version_id: "version", next_run_at: "2026-10-18T12:00:00Z" });
  assert.equal((await reconcilePublishedSchedule("workflow", {}, api)).schedule.id, "recovered");
  assert.equal(calls.filter((call) => call === "publish").length, 1);
});

test("Concurrent creation refreshes after 409 without a second POST", async () => {
  const { api, calls } = publishingFixture({ concurrent: true });
  const result = await publishWithSchedule("workflow", 2, "version", {}, api);
  assert.equal(result.schedule.id, "concurrent");
  assert.equal(calls.filter((call) => call[0] === "create").length, 1);
  assert.equal(calls.filter((call) => call === "list").length, 2);
});

test("Manual and Webhook publishing never create or reactivate schedules", async () => {
  for (const trigger of ["trigger.manual", "trigger.webhook"]) {
    const { api, calls } = publishingFixture({ trigger });
    const result = await publishWithSchedule("workflow", 2, "version", {}, api);
    assert.equal(result.scheduled, false);
    assert.equal(calls.includes("list"), false);
    assert.equal(result.schedule, null);
  }
});

test("Version mismatch and missing/invalid next-run data cannot display Active", () => {
  const workflow = { status: "active", published_version_id: "new" };
  const schedule = { enabled: true, workflow_version_id: "old", next_run_at: "2026-10-18T12:00:00Z" };
  assert.equal(scheduleStatus(workflow, true, schedule), "Version mismatch");
  assert.equal(scheduleStatus(workflow, true, { ...schedule, workflow_version_id: "new", next_run_at: "invalid" }), "Scheduling needs attention");
  assert.equal(scheduleStatus(workflow, true, null), "Schedule not created");
  assert.equal(scheduleStatus(workflow, false, schedule), "Schedule unavailable");
});

test("Refreshing live configuration replaces untouched stale values while preserving edited fields", () => {
  const refreshed = refreshScheduleConfiguration({ interval_minutes: 5, timezone: "UTC", enabled: false }, { timezone: "Asia/Kolkata" });
  assert.equal(refreshed.interval_minutes, 5);
  assert.equal(refreshed.timezone, "Asia/Kolkata");
  assert.equal(refreshed.enabled, false);
});


test("Activation recovery retries lifecycle synchronization only for a confirmed version mismatch", async () => {
  const fixture = publishingFixture();
  await fixture.api.publishWorkflow();
  let version = "old";
  const record = { id: "existing", workflow_id: "workflow", ...fixture.config, input_data: {}, next_run_at: "2026-10-18T12:00:00Z" };
  fixture.api.listSchedules = async () => [{ ...record, workflow_version_id: version }];
  fixture.api.getSchedule = async () => ({ ...record, workflow_version_id: version });
  fixture.api.publishWorkflow = async () => { fixture.calls.push("sync-retry"); version = "version"; };
  const result = await retryScheduleActivation("workflow", {}, fixture.api);
  assert.equal(result.schedule.workflow_version_id, "version");
  assert.equal(fixture.calls.filter((call) => call === "sync-retry").length, 1);
  await retryScheduleActivation("workflow", {}, fixture.api);
  assert.equal(fixture.calls.filter((call) => call === "sync-retry").length, 1);
});
