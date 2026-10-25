"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAuth } from "@/context/AuthContext";
import { getDashboardOverview } from "@/services/dashboard";
import CreateWorkflowDialog from "@/components/workflows/CreateWorkflowDialog";
import { ExecutionIcon, ExecutionStatusBadge, executionButton } from "./ExecutionUI";
import { formatDuration, formatTime, statusLabel, workflowName } from "@/lib/executions";
import styles from "./DashboardOverview.module.css";

const ranges = [{ value: "24h", label: "24 Hours" }, { value: "7d", label: "7 Days" }, { value: "30d", label: "30 Days" }];
const states = [
  ["completed", "Completed", "var(--overview-completed)"], ["failed", "Failed", "var(--overview-failed)"],
  ["running", "Running", "var(--overview-running)"], ["waiting_for_approval", "Waiting for approval", "var(--overview-waiting)"],
  ["pending", "Pending", "var(--text-tertiary)"], ["cancelled", "Cancelled", "var(--border-strong)"],
];
const number = value => new Intl.NumberFormat("en-US").format(value);
function bucketLabel(value, range, full = false) {
  return new Intl.DateTimeFormat("en-US", { timeZone: "UTC", month: full || range !== "24h" ? "short" : undefined,
    day: full || range !== "24h" ? "numeric" : undefined, hour: range === "24h" ? "numeric" : undefined }).format(new Date(value));
}
function ActivityTooltip({ active, payload, label, range }) {
  if (!active || !payload?.length) return null;
  return <div className={styles.tooltip}><strong>{bucketLabel(label, range, true)} UTC</strong>{payload.map(item => <div key={item.dataKey}><span>{item.name}</span><b>{number(item.value)}</b></div>)}</div>;
}
function Skeleton() {
  return <div role="status" aria-label="Loading dashboard" className={styles.skeleton}><span className="sr-only">Loading dashboard</span><div className={styles.kpis}>{[0, 1, 2, 3].map(i => <div key={i} className={styles.placeholder}/>)}</div><div className={styles.placeholder} style={{ height: 340 }}/><div className={styles.columns}><div className={styles.placeholder} style={{ height: 260 }}/><div className={styles.placeholder} style={{ height: 260 }}/></div></div>;
}
function Metric({ title, value, detail, href, icon }) {
  const content = <><div className={styles.metricTitle}><span>{title}</span><ExecutionIcon type={icon}/></div><strong className={styles.metricValue}>{value}</strong><span className={styles.muted}>{detail}</span></>;
  return href ? <Link href={href} className={styles.metric}>{content}</Link> : <div className={styles.metric}>{content}</div>;
}

export default function DashboardOverview() {
  const { isInitializing } = useAuth();
  const router = useRouter();
  const [range, setRange] = useState("7d");
  const [reload, setReload] = useState(0);
  const [result, setResult] = useState({ loading: true, data: null, error: null });
  const [createOpen, setCreateOpen] = useState(false);
  useEffect(() => {
    if (isInitializing) return;
    const controller = new AbortController();
    let disposed = false;
    getDashboardOverview(range, { signal: controller.signal }).then(data => {
      if (!disposed) setResult({ loading: false, data, error: null });
    }).catch(error => {
      if (!disposed) setResult({ loading: false, data: null, error: error.message || "Unable to load dashboard." });
    });
    return () => { disposed = true; controller.abort(); };
  }, [range, reload, isInitializing]);
  function refresh() { setResult({ loading: true, data: null, error: null }); setReload(value => value + 1); }
  function changeRange(value) { if (value !== range) { setResult({ loading: true, data: null, error: null }); setRange(value); } }
  const { data, loading, error } = result;
  const attention = data ? [
    { label: "Pending approvals", count: data.pending_approvals, note: "Assigned to you · current backlog", href: "/approvals", icon: "approval" },
    { label: "Failed executions", count: data.failed, note: "Created in selected period", href: "/dashboard/executions", icon: "alert" },
    { label: "Pending dead-letter events", count: data.pending_dlq, note: "Current backlog · review recovery", href: "/dashboard/executions/dead-letter", icon: "replay" },
  ] : [];
  return <div className={styles.overview}>
    <header className={styles.header}><div><p className={styles.eyebrow}><span className={styles.relayMark} aria-hidden="true"><i/><i/><i/></span>RELAY / WORKSPACE OVERVIEW</p><h1>Overview</h1><p className={styles.subtitle}>Monitor your workflows and execution activity.</p></div><div className={styles.actions}><label className="sr-only" htmlFor="overview-range">Time range</label><select id="overview-range" value={range} onChange={event => changeRange(event.target.value)} className={executionButton}>{ranges.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select><button type="button" className={`${executionButton} ${styles.create}`} onClick={() => setCreateOpen(true)}><span aria-hidden="true">＋</span>Create Workflow</button></div></header>
    {loading ? <Skeleton/> : error ? <div role="alert" className={styles.empty}><ExecutionIcon type="alert"/><h2>Overview unavailable</h2><p>{error}</p><button className={executionButton} onClick={refresh}>Try again</button></div> : data && <>
      <div className={styles.analytics}>
      <section aria-label="Workspace metrics" className={styles.kpis}>
        <Metric title="Active Workflows" value={number(data.active_workflows)} detail={`${number(data.total_workflows)} workflows in this workspace`} href="/dashboard/workflows" icon="generic"/>
        <Metric title="Total Executions" value={number(data.total_executions)} detail="Created in selected period" href="/dashboard/executions" icon="history"/>
        <Metric title="Success Rate" value={data.success_rate === null ? "—" : `${data.success_rate.toFixed(2)}%`} detail="Completed ÷ completed and failed" icon="check"/>
        <div className={styles.metric}><div className={styles.metricTitle}><span>Needs Attention</span><ExecutionIcon type="approval"/></div><div className={styles.attentionMini}>{attention.map(item => <Link key={item.label} href={item.href}><b>{number(item.count)}</b><span>{item.label.replace("Pending ", "").replace(" executions", "")}</span></Link>)}</div><span className={styles.muted}>Separate categories · may overlap</span></div>
      </section>
      <section className={styles.panel} aria-labelledby="activity-title"><div className={styles.panelHeader}><div><h2 id="activity-title"><span className={styles.sectionNumber} aria-hidden="true">01</span>Execution Activity</h2><p>Executions created per {range === "24h" ? "hour" : "day"} · UTC · current bucket is partial</p></div><div className={styles.chartLegend}>{states.slice(0, 2).map(([key, label, color]) => <span key={key}><i style={{ background: color }}/>{label}<b>{number(data[key])}</b></span>)}</div></div>
        {data.completed + data.failed === 0 ? <div className={styles.chartEmpty}><ExecutionIcon type="history" className="h-6 w-6"/><h3>No completed or failed executions yet</h3><p>{data.total_executions ? "Activity will appear here as your executions finish." : "Run a workflow to see activity for this period."}</p></div> : <div className={styles.activity} aria-label="Completed and failed execution activity"><ResponsiveContainer width="100%" height="100%"><AreaChart accessibilityLayer data={data.execution_activity} margin={{ top: 12, right: 12, bottom: 0, left: -20 }}><CartesianGrid vertical={false} stroke="var(--border-subtle)" strokeOpacity={0.75}/><XAxis dataKey="bucket" tickFormatter={value => bucketLabel(value, range)} tickLine={false} axisLine={false} minTickGap={36} tick={{ fill: "var(--text-tertiary)", fontSize: 12 }} dy={10}/><YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: "var(--text-tertiary)", fontSize: 12 }}/><Tooltip content={<ActivityTooltip range={range}/>} cursor={{ stroke: "var(--border-strong)" }}/>{states.slice(0, 2).map(([key, label, color]) => <Area key={key} type="linear" dataKey={key} name={label} stroke={color} fill={color} fillOpacity={0.025} strokeWidth={2} isAnimationActive={false} activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--surface)" }}/>)}</AreaChart></ResponsiveContainer></div>}
        <details className={styles.dataTable}><summary>View activity data</summary><div className={styles.tableScroll}><table><thead><tr><th>Bucket (UTC)</th><th>Completed</th><th>Failed</th></tr></thead><tbody>{data.execution_activity.map(row => <tr key={row.bucket}><td>{bucketLabel(row.bucket, range, true)}</td><td>{row.completed}</td><td>{row.failed}</td></tr>)}</tbody></table></div></details>
      </section>
      </div>
      <div className={styles.columns}><section className={styles.panel} aria-labelledby="status-title"><div className={styles.panelHeader}><div><h2 id="status-title"><span className={styles.sectionNumber} aria-hidden="true">02</span>Execution Status</h2><p>Executions created in the selected period</p></div></div><div className={styles.distribution}><div className={styles.donut}>{data.total_executions > 0 ? <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={states.map(([key, name, color]) => ({ name, value: data[key], color }))} dataKey="value" innerRadius="74%" outerRadius="88%" paddingAngle={data.total_executions > 1 ? 2 : 0} stroke="var(--surface)" isAnimationActive={false}>{states.map(([key, , color]) => <Cell key={key} fill={color}/>)}</Pie></PieChart></ResponsiveContainer> : <div className={styles.emptyRing}/>}<div className={styles.donutLabel}><strong>{number(data.total_executions)}</strong><span>{data.total_executions ? "executions" : "No executions"}</span></div></div><ul className={styles.statusLegend}>{states.map(([key, label, color]) => <li key={key}><span><i style={{ background: color }}/>{label}</span><b>{number(data[key])}</b></li>)}</ul></div></section>
      <section className={styles.panel} aria-labelledby="attention-title"><div className={styles.panelHeader}><div><h2 id="attention-title"><span className={styles.sectionNumber} aria-hidden="true">03</span>Needs Attention</h2><p>Your next decisions and recovery actions</p></div></div><div className={styles.attentionRows}>{attention.map(item => <Link key={item.label} href={item.href}><span className={styles.rowIcon}><ExecutionIcon type={item.icon}/></span><span className={styles.rowText}><strong>{item.label}</strong><small>{item.note}</small></span><b>{number(item.count)}</b><span aria-hidden="true">↗</span></Link>)}</div><p className={styles.footnote}>A failed execution may also have a dead-letter event.</p></section></div>
      <section className={styles.panel} aria-labelledby="recent-title"><div className={styles.panelHeader}><div><h2 id="recent-title"><span className={styles.sectionNumber} aria-hidden="true">04</span>Recent Executions</h2><p>Latest activity across all time</p></div><Link href="/dashboard/executions" className={styles.viewAll}>View all <span aria-hidden="true">↗</span></Link></div>{data.recent_executions.length ? <div className={styles.tableScroll}><table className={styles.recent}><thead><tr><th>Workflow</th><th>Trigger</th><th>Status</th><th>Started / created</th><th>Duration</th></tr></thead><tbody>{data.recent_executions.slice(0, 5).map(run => <tr key={run.id} onClick={event => { if (!event.target.closest("a")) router.push(`/dashboard/executions/${encodeURIComponent(run.id)}`); }}><td><div className={styles.workflowCell}><span className={styles.workflowIcon}><ExecutionIcon type={run.trigger_type}/></span><div><Link href={`/dashboard/executions/${encodeURIComponent(run.id)}`}>{workflowName(run)}</Link><small className={styles.runId}>RUN / {run.id.slice(0, 8)}</small></div></div></td><td><span className={styles.trigger}><ExecutionIcon type={run.trigger_type}/>{statusLabel(run.trigger_type)}</span></td><td><ExecutionStatusBadge status={run.status}/></td><td>{formatTime(run.started_at || run.created_at)}</td><td className={styles.duration}>{formatDuration(run.duration_ms)}</td></tr>)}</tbody></table></div> : <div className={styles.empty}><ExecutionIcon type="manual" className="h-6 w-6"/><h3>Your first run starts here</h3><p>Create a workflow, connect a trigger, and watch it work.</p><Link href="/dashboard/workflows" className={executionButton}>Explore workflows</Link></div>}</section>
      <footer className={styles.footer}><span>UTC buckets · recent execution times shown locally</span><button type="button" onClick={refresh}>Refresh overview <span aria-hidden="true">↻</span></button></footer>
    </>}
    <CreateWorkflowDialog open={createOpen} onClose={() => setCreateOpen(false)} onSuccess={refresh}/>
  </div>;
}
