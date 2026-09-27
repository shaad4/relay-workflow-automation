"use client";

export default function WorkflowStatus({ status = "draft" }) {
  const normalizedStatus = String(status).toLowerCase();
  const isActive = normalizedStatus === "active";
  const isInactive = normalizedStatus === "inactive";
  const isPublished = normalizedStatus === "published";
  const label = isActive ? "Active" : isInactive ? "Inactive" : isPublished ? "Published" : "Draft";

  return (
    <div className="inline-flex items-center gap-2 select-none text-[12px] font-mono leading-none">
      <span
        aria-hidden="true"
        className={`w-2 h-2 rounded-full shrink-0 ${
          isActive || isPublished
            ? "bg-[#3FB950]"
            : isInactive
              ? "bg-[#D29922]"
              : "bg-[var(--text-tertiary)]"
        }`}
      />
      <span
        className={
          isActive || isPublished
            ? "text-[#3FB950] font-medium"
            : isInactive
              ? "text-[#D29922] font-medium"
              : "text-[var(--text-tertiary)]"
        }
      >
        {label}
      </span>
    </div>
  );
}
