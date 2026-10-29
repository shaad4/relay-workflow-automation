export const INTERVAL_PRESETS = [
  [5, "5 minutes"],
  [15, "15 minutes"],
  [30, "30 minutes"],
  [60, "1 hour"],
  [360, "6 hours"],
  [720, "12 hours"],
  [1440, "24 hours"],
];
export const CRON_PRESETS = [
  ["* * * * *", "Every minute"],
  ["0 * * * *", "Every hour"],
  ["0 9 * * *", "Daily at 9 AM"],
  ["0 9 * * 1", "Every Monday at 9 AM"],
  ["0 9 * * 1-5", "Weekdays at 9 AM"],
  ["0 9 1 * *", "First day of month at 9 AM"],
];
export function normalizeSchedule(config = {}) {
  return {
    schedule_type:
      config.schedule_type ??
      (config.cron || config.cron_expression ? "cron" : "interval"),
    interval_minutes: config.interval_minutes ?? 30,
    cron_expression: config.cron_expression ?? config.cron ?? "0 9 * * *",
    timezone: config.timezone ?? "Asia/Kolkata",
    enabled: config.enabled ?? true,
    input_data: config.input_data === undefined ? {} : config.input_data,
  };
}
export function validCron(expression) {
  const fields = String(expression ?? "")
    .trim()
    .split(/\s+/);
  if (fields.length !== 5) return false;
  const ranges = [
    [0, 59],
    [0, 23],
    [1, 31],
    [1, 12],
    [0, 7],
  ];
  const aliases = [
    {},
    {},
    {},
    {
      JAN: 1,
      FEB: 2,
      MAR: 3,
      APR: 4,
      MAY: 5,
      JUN: 6,
      JUL: 7,
      AUG: 8,
      SEP: 9,
      OCT: 10,
      NOV: 11,
      DEC: 12,
    },
    { SUN: 0, MON: 1, TUE: 2, WED: 3, THU: 4, FRI: 5, SAT: 6 },
  ];
  return fields.every((field, index) =>
    field.split(",").every((part) => {
      const pieces = part.toUpperCase().split("/");
      if (
        pieces.length > 2 ||
        (pieces.length === 2 &&
          (!/^\d+$/.test(pieces[1]) || Number(pieces[1]) < 1))
      )
        return false;
      if (pieces[0] === "*") return true;
      const ends = pieces[0].split("-");
      if (ends.length > 2) return false;
      const values = ends.map((value) =>
        /^\d+$/.test(value) ? Number(value) : aliases[index][value],
      );
      return (
        values.every(
          (value) =>
            Number.isInteger(value) &&
            value >= ranges[index][0] &&
            value <= ranges[index][1],
        ) &&
        (values.length === 1 || values[0] <= values[1])
      );
    }),
  );
}
export function validateSchedule(config) {
  const value = normalizeSchedule(config);
  const errors = [];
  if (!["interval", "cron"].includes(value.schedule_type))
    errors.push({
      field: "schedule_type",
      message: "Choose Interval or Cron.",
    });
  if (
    value.schedule_type === "interval" &&
    (value.interval_minutes === "" ||
      !Number.isInteger(Number(value.interval_minutes)) ||
      Number(value.interval_minutes) < 1 ||
      Number(value.interval_minutes) > 10080)
  )
    errors.push({
      field: "interval_minutes",
      message: "Enter a whole number from 1 to 10,080 minutes.",
    });
  if (
    value.schedule_type === "cron" &&
    (String(value.cron_expression).length > 100 ||
      !validCron(value.cron_expression))
  )
    errors.push({
      field: "cron_expression",
      message:
        "Enter a valid five-field cron expression (minute, hour, day, month, weekday).",
    });
  try {
    if (!value.timezone) throw new Error();
    new Intl.DateTimeFormat("en", { timeZone: value.timezone }).format();
  } catch {
    errors.push({
      field: "timezone",
      message: "Choose a valid IANA timezone.",
    });
  }
  if (
    !value.input_data ||
    typeof value.input_data !== "object" ||
    Array.isArray(value.input_data)
  )
    errors.push({
      field: "input_data",
      message: "Scheduled input must be a JSON object.",
    });
  return errors;
}
export function schedulePayload(config) {
  const value = normalizeSchedule(config);
  return {
    ...value,
    interval_minutes:
      value.schedule_type === "interval"
        ? Number(value.interval_minutes)
        : null,
    cron_expression:
      value.schedule_type === "cron" ? value.cron_expression.trim() : null,
  };
}
export function scheduleNodePayload(config) {
  const { input_data, ...payload } = schedulePayload(config);
  void input_data;
  return payload;
}
export function scheduleSummary(config) {
  const value = normalizeSchedule(config);
  if (validateSchedule(value).length)
    return "Complete the schedule configuration below.";
  if (value.schedule_type === "interval")
    return `Runs every ${value.interval_minutes} minute${Number(value.interval_minutes) === 1 ? "" : "s"}`;
  const preset = CRON_PRESETS.find(
    ([expression]) => expression === value.cron_expression.trim(),
  );
  return `${preset ? `Runs ${preset[1].toLowerCase()}` : `Runs on cron ${value.cron_expression}`} (${value.timezone})`;
}
export function scheduleDate(value, timezone) {
  if (!value) return "Not scheduled";
  try {
    return new Intl.DateTimeFormat("en", {
      timeZone: timezone,
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return "Unavailable";
  }
}
export function scheduleStatus(workflow, available, schedule) {
  if (!workflow?.published_version_id) return "Publish required";
  if (!available) return "Schedule unavailable";
  if (String(workflow.status).toLowerCase() !== "active")
    return "Workflow inactive";
  if (!schedule) return "Schedule not created";
  if (
    String(schedule.workflow_version_id) !==
    String(workflow.published_version_id)
  )
    return "Version mismatch";
  return !schedule.enabled
    ? "Paused"
    : schedule.next_run_at && Number.isFinite(Date.parse(schedule.next_run_at))
      ? "Active"
      : "Scheduling needs attention";
}
export function scheduleError(error) {
  return (
    {
      401: "Your session has expired. Sign in again.",
      404: "The workflow or schedule was not found. Refresh its state.",
      409: "The schedule conflicts with the current workflow. Refresh, check that the workflow is active and its published version contains a Scheduled Trigger, then try again.",
      422: "The schedule was rejected. Check the interval, five-field cron expression, timezone, and JSON input.",
      503: "Scheduling is temporarily unavailable. Try again later.",
      504: "The request timed out. Refresh schedule state before trying again.",
    }[error?.status] ||
    "The request could not be confirmed. Refresh schedule state before trying again."
  );
}

export async function createScheduleIfMissing(workflowId, config, api) {
  const response = await api.listSchedules();
  const rows = Array.isArray(response)
    ? response
    : response?.schedules || response?.results || response?.data || [];
  const existing = rows.find(
    (schedule) => String(schedule.workflow_id) === String(workflowId),
  );
  return (
    existing ||
    api.createSchedule({ workflow_id: workflowId, ...schedulePayload(config) })
  );
}

export function parseTriggerPayload(text) {
  let input;
  try {
    input = JSON.parse(text.trim() || "{}");
  } catch {
    return { error: "Invalid JSON format. Check your syntax." };
  }
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    return { error: "Trigger payload must be a JSON object." };
  }
  return { input };
}

// Node configuration forbids input_data. Keep unsaved payloads across inspector
// remounts and publishing in this tab until the schedule API confirms a save.
const payloadDrafts = new Map();
const payloadDraftKey = (workflowId) => `relay:schedule-payload:${workflowId}`;
export function readPayloadDraft(workflowId, storage) {
  const key = payloadDraftKey(workflowId);
  let text = payloadDrafts.get(key);
  try {
    text ??= storage?.getItem(key) ?? undefined;
  } catch {
    /* In-memory drafts still survive remounts. */
  }
  return { text: text ?? "{}", dirty: text !== undefined };
}
export function writePayloadDraft(workflowId, text, storage) {
  const key = payloadDraftKey(workflowId);
  payloadDrafts.set(key, text);
  try {
    storage?.setItem(key, text);
  } catch {
    /* Retain the in-memory draft. */
  }
}
export function clearPayloadDraft(workflowId, storage) {
  const key = payloadDraftKey(workflowId);
  payloadDrafts.delete(key);
  try {
    storage?.removeItem(key);
  } catch {
    /* Storage may be unavailable. */
  }
}

export function payloadDraftFromSchedule(draft, schedule) {
  return draft.dirty
    ? draft
    : {
        text: JSON.stringify(schedule?.input_data ?? {}, null, 2),
        dirty: false,
      };
}

const scheduleRows = (response, key) =>
  Array.isArray(response)
    ? response
    : response?.[key] || response?.results || response?.data || [];
const canonicalJSON = (value) =>
  JSON.stringify(value, (_, item) =>
    item && typeof item === "object" && !Array.isArray(item)
      ? Object.fromEntries(
          Object.entries(item).sort(([a], [b]) => a.localeCompare(b)),
        )
      : item,
  );

export async function reconcilePublishedSchedule(
  workflowId,
  payloadDraft,
  api,
  intendedConfig,
) {
  const workflow = await api.getWorkflow(workflowId);
  if (!workflow.published_version_id)
    throw new Error("Publish this workflow before activating its schedule.");
  const versions = scheduleRows(
    await api.getWorkflowVersions(workflowId),
    "versions",
  );
  const version = versions.find(
    (item) => String(item.id) === String(workflow.published_version_id),
  );
  if (!version || version.status !== "published")
    throw new Error(
      "The published workflow version could not be confirmed. Refresh and try again.",
    );
  const nodes = scheduleRows(
    await api.getWorkflowNodes(
      workflowId,
      version.version_number ?? version.version,
    ),
    "nodes",
  );
  const trigger = nodes.find(
    (node) =>
      (node.node_type || node.type || node.data?.typeId) === "trigger.schedule",
  );
  if (!trigger) return { workflow, schedule: null, scheduled: false };
  if (workflow.status !== "active")
    throw new Error("Activate the workflow before scheduling automatic runs.");
  const config =
    intendedConfig ??
    trigger.configuration ??
    trigger.config ??
    trigger.data?.config ??
    {};
  const parsed = payloadDraft?.dirty
    ? parseTriggerPayload(payloadDraft.text)
    : { input: {} };
  if (parsed.error) throw new Error(parsed.error);
  const findExisting = async () =>
    scheduleRows(await api.listSchedules(), "schedules").find(
      (item) => String(item.workflow_id) === String(workflowId),
    );
  let existing = await findExisting();
  if (!existing) {
    const desired = schedulePayload({ ...config, input_data: parsed.input });
    const errors = validateSchedule(desired);
    if (errors.length) throw new Error(errors[0].message);
    try {
      existing = await api.createSchedule({
        workflow_id: workflowId,
        ...desired,
      });
    } catch (error) {
      // Reconcile an uncertain POST once; never blindly repeat a creation.
      if (error.status && ![409, 503, 504].includes(error.status)) throw error;
      existing = await findExisting();
      if (!existing) throw error;
    }
  }
  if (
    String(existing.workflow_version_id) !==
    String(workflow.published_version_id)
  )
    throw Object.assign(
      new Error(
        "Schedule version mismatch. Workflow publication succeeded, but lifecycle synchronization needs attention. Retry schedule activation to synchronize the published version.",
      ),
      { code: "SCHEDULE_VERSION_MISMATCH" },
    );
  const desired = schedulePayload({
    ...config,
    enabled: existing.enabled,
    input_data: payloadDraft?.dirty
      ? parsed.input
      : (existing.input_data ?? {}),
  });
  const errors = validateSchedule(desired);
  if (errors.length) throw new Error(errors[0].message);
  const changes = {};
  for (const field of [
    "schedule_type",
    "interval_minutes",
    "cron_expression",
    "timezone",
    "input_data",
  ]) {
    if (
      canonicalJSON(existing[field] ?? null) !== canonicalJSON(desired[field])
    )
      changes[field] = desired[field];
  }
  if (Object.keys(changes).length)
    await api.updateSchedule(existing.id, changes);
  const schedule = await api.getSchedule(existing.id);
  if (
    String(schedule.workflow_version_id) !==
    String(workflow.published_version_id)
  )
    throw new Error(
      "Schedule version mismatch. Refresh schedule state and retry activation.",
    );
  if (
    schedule.enabled &&
    (!schedule.next_run_at ||
      !Number.isFinite(Date.parse(schedule.next_run_at)))
  )
    throw new Error(
      "Automatic scheduling could not be confirmed. Refresh schedule state and explicitly resume the schedule if appropriate.",
    );
  return { workflow, schedule, scheduled: true };
}

export async function publishWithSchedule(
  workflowId,
  versionNumber,
  versionId,
  payloadDraft,
  api,
  onPublished = () => {},
) {
  let publicationError;
  try {
    await api.publishWorkflow(workflowId, versionNumber);
  } catch (error) {
    publicationError = error;
  }
  let workflow;
  try {
    workflow = await api.getWorkflow(workflowId);
  } catch (error) {
    throw publicationError || error;
  }
  if (
    String(workflow.published_version_id) !== String(versionId) ||
    workflow.status !== "active"
  ) {
    throw (
      publicationError ||
      new Error(
        "Publishing was not confirmed. Refresh workflow state before retrying.",
      )
    );
  }
  onPublished(workflow);
  const draft =
    typeof payloadDraft === "function" ? payloadDraft() : payloadDraft;
  try {
    const result = await reconcilePublishedSchedule(workflowId, draft, api);
    return {
      ...result,
      payloadDraft: draft,
      publicationWarning: publicationError
        ? `Workflow published, but lifecycle synchronization was not fully confirmed. ${publicationError.message || "Refresh its state before retrying synchronization."}`
        : null,
    };
  } catch (error) {
    return {
      workflow,
      schedulingError: error.status ? scheduleError(error) : error.message,
    };
  }
}

export function refreshScheduleConfiguration(
  configuration,
  unsavedChanges = {},
) {
  return { ...normalizeSchedule(configuration), ...unsavedChanges };
}

export async function retryScheduleActivation(workflowId, payloadDraft, api) {
  try {
    return await reconcilePublishedSchedule(workflowId, payloadDraft, api);
  } catch (error) {
    if (error.code !== "SCHEDULE_VERSION_MISMATCH") throw error;
    const workflow = await api.getWorkflow(workflowId);
    const versions = scheduleRows(
      await api.getWorkflowVersions(workflowId),
      "versions",
    );
    const version = versions.find(
      (item) => String(item.id) === String(workflow.published_version_id),
    );
    if (!version || workflow.status !== "active") throw error;
    // The publish endpoint is idempotent for this already-published active
    // version: retry its lifecycle synchronization, without a new publication.
    await api.publishWorkflow(
      workflowId,
      version.version_number ?? version.version,
    );
    return reconcilePublishedSchedule(workflowId, payloadDraft, api);
  }
}
