"use client";

import { useEffect, useRef, useState } from "react";
import { createSchedule, listSchedules, updateSchedule, deleteSchedule } from "@/services/schedules";
import { getWorkflow, getWorkflowVersions, getWorkflowNodes } from "@/services/workflows";
import { createScheduleIfMissing, CRON_PRESETS, INTERVAL_PRESETS, normalizeSchedule, validateSchedule, schedulePayload, scheduleSummary, scheduleDate, scheduleStatus, scheduleError } from "./scheduleTrigger";

const inputClass = "mt-1 w-full rounded-[6px] border border-[var(--border-default)] bg-[var(--input-bg)] px-2 py-2 text-[11px] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)] disabled:opacity-60";
const buttonClass = "rounded-[6px] border border-[var(--border-default)] px-3 py-2 text-[11px] hover:bg-[var(--elevated)] focus-visible:outline-2 focus-visible:outline-[var(--accent)] disabled:opacity-50 disabled:cursor-not-allowed";
const rowsOf = (data) => Array.isArray(data) ? data : data?.results || data?.data || data?.schedules || data?.versions || data?.nodes || [];

function ScheduleFields({ config, onChange, disabled, includeInput = true }) {
  const value = normalizeSchedule(config);
  const [inputText, setInputText] = useState(() => JSON.stringify(value.input_data, null, 2));
  const [jsonError, setJsonError] = useState("");
  const timezoneOptions = [...new Set([value.timezone, "Asia/Kolkata", "UTC", "America/New_York", "Europe/London", "Asia/Dubai", "Asia/Singapore", "Asia/Tokyo", ...(typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : [])])];
  const change = (field, next) => onChange({ ...value, [field]: next });
  return <div className="space-y-3 text-[11px] text-[var(--text-secondary)]">
    <fieldset disabled={disabled} className="space-y-3 disabled:opacity-70">
      <legend className="mb-1.5 font-medium">Schedule type</legend>
      <div className="grid grid-cols-2 gap-1 rounded-[6px] border border-[var(--border-subtle)] bg-[var(--elevated)] p-1">{["interval", "cron"].map((type) => <button key={type} type="button" aria-pressed={value.schedule_type === type} onClick={() => change("schedule_type", type)} className={`rounded py-1.5 capitalize focus-visible:outline-2 focus-visible:outline-[var(--accent)] ${value.schedule_type === type ? "bg-[var(--accent)] text-white" : "text-[var(--text-secondary)]"}`}>{type}</button>)}</div>
      {value.schedule_type === "interval" ? <label className="block">Run every
        <select aria-label="Interval presets" value={INTERVAL_PRESETS.some(([minutes]) => minutes === Number(value.interval_minutes)) ? value.interval_minutes : "custom"} onChange={(event) => change("interval_minutes", event.target.value === "custom" ? "" : Number(event.target.value))} className={inputClass}>{INTERVAL_PRESETS.map(([minutes, label]) => <option key={minutes} value={minutes}>{label}</option>)}<option value="custom">Custom interval</option></select>
        <input aria-label="Interval in minutes" type="number" min="1" max="10080" step="1" value={value.interval_minutes} onChange={(event) => change("interval_minutes", event.target.value === "" ? "" : Number(event.target.value))} className={inputClass}/><span className="mt-1 block text-[10px] text-[var(--text-tertiary)]">Minutes · 1 to 10,080 (7 days)</span>
      </label> : <div className="space-y-2"><label className="block">Cron expression<input value={value.cron_expression} maxLength={100} onChange={(event) => change("cron_expression", event.target.value)} placeholder="0 9 * * *" className={`${inputClass} font-mono`}/></label><label className="block">Common schedules<select value="" onChange={(event) => change("cron_expression", event.target.value)} className={inputClass}><option value="" disabled>Choose a preset…</option>{CRON_PRESETS.map(([expression, label]) => <option key={expression} value={expression}>{label}</option>)}</select></label><p className="rounded border border-[var(--border-subtle)] bg-[var(--elevated)] p-2 font-mono text-[10px] leading-5">minute · hour · day · month · weekday<br/>* any · , list · - range · / step</p></div>}
      <label className="block">Timezone<select value={value.timezone} onChange={(event) => change("timezone", event.target.value)} className={inputClass}>{timezoneOptions.map((timezone) => <option key={timezone} value={timezone}>{timezone}</option>)}</select></label>
      <label className="flex items-center justify-between gap-3 rounded-[6px] border border-[var(--border-subtle)] p-3"><span>Enabled<span className="mt-1 block text-[10px] text-[var(--text-tertiary)]">Desired state when this configuration is applied</span></span><button type="button" role="switch" aria-checked={value.enabled} aria-label="Schedule enabled" onClick={() => change("enabled", !value.enabled)} className={`relative h-5 w-9 shrink-0 rounded-full focus-visible:outline-2 focus-visible:outline-[var(--accent)] ${value.enabled ? "bg-[var(--accent)]" : "bg-[var(--border-strong)]"}`}><span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${value.enabled ? "left-[18px]" : "left-0.5"}`}/></button></label>
      {includeInput && <><label className="block">Scheduled input <span className="text-[var(--text-tertiary)]">(optional JSON object)</span><textarea rows={4} value={inputText} spellCheck={false} onChange={(event) => { const text = event.target.value; setInputText(text); try { const parsed = JSON.parse(text); if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error(); setJsonError(""); change("input_data", parsed); } catch { setJsonError("Enter a valid JSON object."); change("input_data", text); } }} className={`${inputClass} font-mono resize-y`}/></label>
      {jsonError && <p role="alert" className="text-red-500">{jsonError}</p>}
      <p className="text-[10px] text-[var(--text-tertiary)]">Read input with <code>{"{{trigger.data.report_type}}"}</code></p></>}
    </fieldset>
    <div className="rounded-[6px] border border-[var(--accent)]/25 bg-[var(--accent)]/5 p-3 leading-5"><p className="font-medium text-[var(--text-primary)]">{scheduleSummary(value)}</p></div>
    {validateSchedule(value).map((error) => <p key={error.field} role="alert" className="text-[10px] text-red-500">{error.message}</p>)}
  </div>;
}

export default function ScheduleConfig({ config, onChange, isReadOnly, workflowId, revision }) {
  const [state, setState] = useState(null);
  const [activeConfig, setActiveConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [editing, setEditing] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const lock = useRef(false);
  const generation = useRef(0);
  const deleteCancel = useRef(null);
  useEffect(() => { if (confirmDelete) deleteCancel.current?.focus(); }, [confirmDelete]);
  useEffect(() => {
    let cancelled = false;
    generation.current += 1;
    async function load() {
      const [workflow, schedules] = await Promise.all([getWorkflow(workflowId), listSchedules()]);
      let trigger = null;
      if (workflow.published_version_id) {
        const versions = rowsOf(await getWorkflowVersions(workflowId));
        const published = versions.find((version) => String(version.id) === String(workflow.published_version_id));
        if (!published) throw new Error("Published version unavailable");
        const nodes = rowsOf(await getWorkflowNodes(workflowId, published.version_number ?? published.version));
        trigger = nodes.find((node) => (node.node_type || node.type || node.type_id || node.data?.typeId) === "trigger.schedule");
      }
      const schedule = rowsOf(schedules).find((item) => String(item.workflow_id) === String(workflowId)) || null;
      if (!cancelled) { setState({ workflow, schedule, trigger }); setActiveConfig(normalizeSchedule(schedule || trigger?.config || trigger?.configuration || trigger?.data?.config)); }
    }
    load().catch((failure) => { if (!cancelled) setError(scheduleError(failure)); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; generation.current += 1; };
  }, [workflowId, revision, refresh]);
  const mutate = async (action) => {
    if (lock.current || loading || !state) return;
    lock.current = true; setPending(true); setError(""); setNotice("");
    const currentGeneration = generation.current;
    try {
      const result = await action();
      if (generation.current !== currentGeneration) return;
      setState((previous) => ({ ...previous, schedule: result }));
      if (result) setActiveConfig(normalizeSchedule(result));
      setEditing(false); setConfirmDelete(false); setNotice(result ? "Schedule saved." : "Schedule deleted. Future automatic runs have stopped.");
    } catch (failure) {
      if (generation.current === currentGeneration) { setError(scheduleError(failure)); setState(null); setConfirmDelete(false); }
    } finally { lock.current = false; setPending(false); }
  };
  const status = state ? scheduleStatus(state.workflow, Boolean(state.trigger), state.schedule) : "";
  const canApply = state && Boolean(state.trigger) && ["active", "published"].includes(String(state.workflow.status).toLowerCase());
  const inconsistent = state?.schedule && state?.trigger && String(state.schedule.workflow_version_id) !== String(state.workflow.published_version_id);
  const schedule = state?.schedule;
  return <div className="space-y-4">
    {!isReadOnly && <><ScheduleFields config={config} onChange={onChange} disabled={pending} includeInput={false}/><p className="text-[10px] leading-4 text-[var(--text-tertiary)]">Draft configuration only. Save the node and workflow, then publish. Changes here do not update the live schedule.</p></>}
    <section aria-label="Live schedule" aria-busy={loading || pending} className="space-y-3 border-t border-[var(--border-subtle)] pt-4 text-[11px] text-[var(--text-secondary)]">
      <div className="flex items-center justify-between gap-2"><h3 className="font-semibold text-[var(--text-primary)]">Live schedule</h3>{status && <span className={`rounded-full border px-2 py-0.5 text-[10px] ${status === "Active" ? "border-emerald-500/30 text-emerald-500" : "border-[var(--border-default)]"}`}>{status}</span>}</div>
      {loading ? <p role="status">Loading schedule…</p> : state && <>
        {!schedule && <p className="leading-5">{canApply ? "No schedule exists. Activate scheduling using the published trigger configuration." : "Publish a Scheduled Trigger and activate the workflow to set up automatic runs."}</p>}
        {inconsistent && <p role="alert" className="text-amber-500">The schedule does not match the published version. Refresh its state. If this persists, republish the workflow before updating scheduling.</p>}
        {schedule && <div className="space-y-2 rounded-[6px] border border-[var(--border-subtle)] bg-[var(--elevated)] p-3"><p className="font-medium text-[var(--text-primary)]">{scheduleSummary(schedule)}</p><dl className="space-y-2 text-[10px]"><div><dt>Schedule type</dt><dd className="capitalize text-[var(--text-primary)]">{schedule.schedule_type}</dd></div><div><dt>Timezone</dt><dd className="text-[var(--text-primary)]">{schedule.timezone}</dd></div><div><dt>Next scheduled run</dt><dd className="text-[var(--text-primary)]">{scheduleDate(schedule.next_run_at, schedule.timezone)}</dd></div><div><dt>Last scheduled dispatch</dt><dd className="text-[var(--text-primary)]">{schedule.last_run_at ? scheduleDate(schedule.last_run_at, schedule.timezone) : "No dispatch yet"}</dd></div></dl><p className="text-[10px] text-[var(--text-tertiary)]">Times shown in {schedule.timezone}. Dispatch does not confirm execution success.</p></div>}
        {schedule && <div className="flex flex-wrap gap-2"><button type="button" disabled={pending || !canApply || inconsistent} onClick={() => mutate(() => updateSchedule(schedule.id, { enabled: !schedule.enabled }))} className={buttonClass}>{pending ? "Saving…" : schedule.enabled ? "Pause schedule" : "Resume schedule"}</button><button type="button" disabled={pending || !canApply || inconsistent} onClick={() => setEditing(!editing)} className={buttonClass}>{editing ? "Cancel editing" : "Edit live schedule"}</button></div>}
        {(!schedule || editing) && canApply && !inconsistent && <><p className="text-[10px] leading-4">{schedule ? "These changes apply directly to the live schedule. Its paused state is preserved unless you change Enabled." : "Review the published trigger configuration before activating."}</p><ScheduleFields key={`${schedule?.id || "new"}:${refresh}:${revision}`} config={activeConfig} onChange={setActiveConfig} disabled={pending}/><button type="button" disabled={pending || validateSchedule(activeConfig).length > 0} onClick={() => mutate(async () => {
          if (schedule) return updateSchedule(schedule.id, schedulePayload(activeConfig));
          return createScheduleIfMissing(workflowId, activeConfig, { listSchedules, createSchedule });
        })} className={`${buttonClass} w-full bg-[var(--accent)] text-white`}>{pending ? "Saving…" : schedule ? "Update Schedule" : "Activate schedule"}</button></>}
        {schedule && <button type="button" disabled={pending} onClick={() => setConfirmDelete(true)} className={`${buttonClass} text-red-500`}>Delete schedule</button>}
      </>}
      {error && <p role="alert" className="rounded-[6px] border border-red-500/30 bg-red-500/5 p-2 leading-5 text-red-500">{error}</p>}
      {notice && <p role="status" className="text-emerald-500">{notice}</p>}
      <button type="button" disabled={pending || loading} onClick={() => { setLoading(true); setState(null); setEditing(false); setError(""); setRefresh((value) => value + 1); }} className={buttonClass}>Refresh schedule state</button>
    </section>
    {confirmDelete && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onKeyDown={(event) => { if (event.key === "Escape" && !pending) setConfirmDelete(false); if (event.key === "Tab") { const buttons = event.currentTarget.querySelectorAll("button:not(:disabled)"); if (buttons.length && event.shiftKey && document.activeElement === buttons[0]) { event.preventDefault(); buttons[buttons.length - 1].focus(); } else if (buttons.length && !event.shiftKey && document.activeElement === buttons[buttons.length - 1]) { event.preventDefault(); buttons[0].focus(); } } }}><section role="dialog" aria-modal="true" aria-labelledby="delete-schedule-title" aria-describedby="delete-schedule-description" className="w-full max-w-md space-y-4 rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] p-5 shadow-2xl"><h3 id="delete-schedule-title" className="font-semibold text-[var(--text-primary)]">Delete schedule?</h3><p id="delete-schedule-description" className="text-xs leading-5 text-[var(--text-secondary)]">This stops future automatic runs. Your workflow will not be deleted.</p><div className="flex justify-end gap-2"><button ref={deleteCancel} type="button" disabled={pending} onClick={() => setConfirmDelete(false)} className={buttonClass}>Cancel</button><button type="button" disabled={pending} onClick={() => mutate(async () => { await deleteSchedule(schedule.id); return null; })} className={`${buttonClass} bg-red-600 text-white`}>{pending ? "Deleting…" : "Delete schedule"}</button></div></section></div>}
  </div>;
}
