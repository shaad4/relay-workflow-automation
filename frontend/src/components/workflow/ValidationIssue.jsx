export default function ValidationIssue({ issue, onSelect }) {
  const location = [
    issue.nodeLabel || issue.nodeId || issue.node_id,
    issue.field,
  ]
    .filter(Boolean)
    .join(" → ");
  return (
    <div className="space-y-1 break-words text-[11px] leading-4">
      {location &&
        (onSelect && (issue.nodeId || issue.node_id) ? (
          <button
            type="button"
            onClick={() => onSelect(issue)}
            className="text-left font-semibold underline underline-offset-2 focus-visible:outline focus-visible:outline-2"
          >
            {location}
          </button>
        ) : (
          <p className="font-semibold">{location}</p>
        ))}
      <p>{issue.message}</p>
      {issue.expression && (
        <code className="block select-text break-all">{issue.expression}</code>
      )}
      {issue.suggestion && <p className="select-text">{issue.suggestion}</p>}
    </div>
  );
}
