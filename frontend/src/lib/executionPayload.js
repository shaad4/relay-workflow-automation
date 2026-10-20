// Payloads are already sanitized by the API. Preserve every value verbatim.
export const PAYLOAD_SECTION_SIZE = 12000;
export const payloadTabs = ["input", "output", "error"];
export const emptyPayloadMessages = {
  input: "No input data recorded.", output: "No output available.", error: "No error recorded.",
};
export function defaultPayloadTab(status) {
  const normalized = String(status).toLowerCase();
  if (["failed", "dead_lettered"].includes(normalized)) return "error";
  return normalized === "completed" ? "output" : "input";
}
export function serializePayload(value) {
  return JSON.stringify(value === undefined ? null : value, null, 2);
}
// Avoid cutting a surrogate pair between sections (for example emoji in prompts).
export function payloadSection(text, requestedPage = 0, size = PAYLOAD_SECTION_SIZE) {
  const total = Math.max(1, Math.ceil(text.length / size));
  const page = Math.max(0, Math.min(requestedPage, total - 1));
  const boundary = position => position > 0 && position < text.length &&
    /[\uD800-\uDBFF]/.test(text[position - 1]) && /[\uDC00-\uDFFF]/.test(text[position]) ? position - 1 : position;
  const start = boundary(page * size);
  const end = boundary(Math.min((page + 1) * size, text.length));
  return { page, total, start, end, text: text.slice(start, end) };
}
export function payloadSizeLabel(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Tokenize the complete JSON for correct string context at section boundaries.
// Only tokens intersecting the visible section are returned to React.
export function payloadTokens(text, start = 0, end = text.length) {
  const tokens = [];
  const pattern = /"(?:\\[\s\S]|[^"\\])*"|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g;
  let cursor = start;
  for (const match of text.matchAll(pattern)) {
    const from = match.index;
    const to = from + match[0].length;
    if (to <= start) continue;
    if (from >= end) break;
    if (from > cursor) tokens.push({ type: "punctuation", text: text.slice(cursor, Math.min(from, end)) });
    const raw = match[0];
    const type = raw[0] === '"' ? (/^\s*:/.test(text.slice(to, to + 20)) ? "key" : "string") : raw === "null" ? "null" : /true|false/.test(raw) ? "boolean" : "number";
    tokens.push({ type, text: text.slice(Math.max(from, start), Math.min(to, end)) });
    cursor = Math.min(to, end);
  }
  if (cursor < end) tokens.push({ type: "punctuation", text: text.slice(cursor, end) });
  return tokens;
}
