export const deadLetterFilters = [
  ["", "All"],
  ["pending", "Pending"],
  ["replayed", "Replayed"],
  ["resolved", "Resolved"],
];

export function deadLetterError(error) {
  if (error?.status === 401)
    return "Your session has expired. Please sign in again.";
  if (error?.status === 404)
    return "Dead-letter event not found. It may no longer be available in this workspace.";
  if (error?.status === 409)
    return "This event has already been handled. Refresh to see its current status.";
  if (error?.status === 422)
    return "This execution is not eligible for safe replay.";
  if (error?.status >= 500)
    return "Relay is temporarily unable to process this request. Please try again.";
  if (error?.name === "TimeoutError")
    return "The request took too long. Please refresh before trying again.";
  return "We couldn’t load or update this dead-letter event. Check your connection and try again.";
}

// Never render the error object or arbitrary payload fields. Hide diagnostic dumps,
// and redact common credential forms in the single human-readable message.
export function deadLetterMessage(error) {
  const message = error?.message;
  if (typeof message !== "string" || !message.trim())
    return "No error message available.";
  if (
    /private key|traceback|stack trace|\bat .+\(.+:\d+:\d+\)|[{}\[\]\n\r]/i.test(
      message,
    )
  )
    return "Action execution failed. Review the original execution for details.";
  return message
    .replace(/\b(?:authorization|cookie|set-cookie)\s*[:=].*/gi, "[REDACTED]")
    .replace(/\b(?:bearer|basic)\s+[^\s,;]+/gi, "[REDACTED]")
    .replace(
      /\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|secret|credential)s?\s*[:=]\s*(?:"[^"]*"|'[^']*'|[^\s,;]+)/gi,
      "[REDACTED]",
    )
    .replace(
      /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g,
      "[REDACTED]",
    )
    .replace(/\b(?:sk-|sk_live_|sk_test_|ghp_)[A-Za-z0-9_-]+\b/g, "[REDACTED]")
    .replace(/https?:\/\/\S+/gi, "[URL REDACTED]")
    .slice(0, 500);
}
