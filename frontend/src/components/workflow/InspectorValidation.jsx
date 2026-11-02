"use client";

import { createContext, useContext } from "react";

export const InspectorValidation = createContext({ issues: [], schema: null });

export function FieldRequirements({ field }) {
  const { schema } = useContext(InspectorValidation);
  if (!field) return null;
  const property = schema?.properties?.[field];
  const hints = property
    ? [
        schema.required?.includes(field) ? "Required" : "Optional",
        property.maxLength
          ? `Up to ${property.maxLength.toLocaleString("en-US")} characters`
          : null,
      ].filter(Boolean)
    : [];
  return hints.length ? (
    <p className="text-[10px] font-normal normal-case tracking-normal text-[var(--text-tertiary)]">
      {hints.join(" · ")}
    </p>
  ) : null;
}

export function FieldFeedback({ field, errorsOnly = false }) {
  const { issues } = useContext(InspectorValidation);
  if (!field) return null;
  const fieldIssues = issues.filter(
    (issue) =>
      issue.field === field ||
      issue.field?.startsWith(`${field}.`) ||
      issue.field?.startsWith(`${field}[`),
  );
  if (errorsOnly && !fieldIssues.length) return null;
  return (
    <div className="mt-1.5 space-y-1.5 normal-case tracking-normal">
      {!errorsOnly && <FieldRequirements field={field} />}
      {fieldIssues.map((issue, index) => {
        // The field label already identifies the node and setting being edited.
        const message = issue.message?.replace(/^.+? node '[^']+': .+? - /, "");
        const suggestion =
          issue.suggestion ===
          "Read the node's configuration_schema and correct this field."
            ? null
            : issue.suggestion;
        return (
          <div
            key={index}
            role="alert"
            className="flex items-start gap-1.5 text-[11px] leading-4 text-red-600 dark:text-red-400"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              className="mt-0.5 h-3 w-3 shrink-0"
            >
              <circle cx="8" cy="8" r="6" />
              <path d="M8 4.5v4M8 10.5v1" strokeLinecap="round" />
            </svg>
            <div className="min-w-0 space-y-0.5 break-words">
              {issue.field !== field && (
                <p className="font-medium">{issue.field}</p>
              )}
              <p>{message}</p>
              {issue.expression && (
                <code className="block select-text break-all text-[10px]">
                  {issue.expression}
                </code>
              )}
              {suggestion && <p className="select-text">{suggestion}</p>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
