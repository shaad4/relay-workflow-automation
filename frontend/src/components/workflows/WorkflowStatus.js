"use client";

export default function WorkflowStatus({ status = "draft" }) {
  const isPublished = String(status).toLowerCase() === "published";

  return (
    <div className="inline-flex items-center gap-2 select-none text-[12px] font-mono leading-none">
      <span
        aria-hidden="true"
        className={`w-2 h-2 rounded-full shrink-0 ${
          isPublished
            ? "bg-[#3FB950]"
            : "bg-[var(--text-tertiary)]"
        }`}
      />
      <span
        className={
          isPublished
            ? "text-[#3FB950] font-medium"
            : "text-[var(--text-tertiary)]"
        }
      >
        {isPublished ? "Published" : "Draft"}
      </span>
    </div>
  );
}
