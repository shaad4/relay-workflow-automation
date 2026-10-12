export const processingStatuses = new Set(["uploading", "pending", "parsing", "chunking", "embedding"]);

const labels = {
  uploading: "Uploading", pending: "Queued", parsing: "Extracting text",
  chunking: "Preparing chunks", embedding: "Generating embeddings", ready: "Ready", failed: "Failed",
};

export default function DocumentStatusBadge({ status }) {
  const processing = processingStatuses.has(status);
  const color = status === "ready" ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-700 dark:text-emerald-400"
    : status === "failed" ? "border-red-500/20 bg-red-500/5 text-red-700 dark:text-red-400"
    : processing ? "border-[var(--accent)]/20 bg-[var(--accent)]/5 text-[var(--accent-hover)]"
    : "border-[var(--border-default)] text-[var(--text-secondary)]";
  return <div className="inline-flex flex-col items-start gap-2"><span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2 py-1 text-[10px] font-medium ${color}`}>
    {processing ? <span className="relay-ingestion-bars" aria-hidden="true"><i/><i/><i/></span> : <span aria-hidden="true">{status === "ready" ? "✓" : status === "failed" ? "!" : "·"}</span>}
    {labels[status] || "Unknown status"}
  </span>
    {processing && <div className="relay-ingestion-track" aria-hidden="true">{["uploading", "pending", "parsing", "chunking", "embedding"].map((step, index, stages) => <span key={step} className={index < stages.indexOf(status) ? "is-complete" : step === status ? "is-current" : ""}/>)}</div>}
  </div>;
}
