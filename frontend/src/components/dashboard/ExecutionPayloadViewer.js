"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { defaultPayloadTab, emptyPayloadMessages, payloadSection, payloadSizeLabel, payloadTabs, serializePayload, payloadTokens } from "@/lib/executionPayload";

function ColoredJson({ text, section }) {
  const tokens = useMemo(() => payloadTokens(text, section.start, section.end), [text, section.start, section.end]);
  return <code>{tokens.map((token, index) => <span key={index} className={`payload-token-${token.type}`}>{token.text}</span>)}</code>;
}

function FormattedField({ name, value, depth = 0 }) {
  const [open, setOpen] = useState(depth === 0);
  const [limit, setLimit] = useState(20);
  const [page, setPage] = useState(0);
  const [showText, setShowText] = useState(false);
  const [query, setQuery] = useState("");
  const [copied, setCopied] = useState(null);
  const fieldRef = useRef(null);
  const searchId = useId();
  const container = value !== null && typeof value === "object";
  const keys = container ? Object.keys(value) : [];
  const filteredKeys = keys.filter(key => key.toLowerCase().includes(query.trim().toLowerCase()));
  const string = typeof value === "string";
  const section = payloadSection(container ? "" : string ? value : serializePayload(value), page);
  const longText = section.text.length > 650 || section.text.split("\n").length > 10;
  const renderedText = longText && !showText ? `${section.text.split("\n").slice(0, 10).join("\n").slice(0, 650)}…` : section.text;
  const copyMessage = copied?.value === value ? copied.message : "";
  async function copyValue() {
    try {
      await navigator.clipboard.writeText(string ? value : serializePayload(value));
      setCopied({ value, message: "Copied" });
    } catch { setCopied({ value, message: "Copy unavailable — select the text" }); }
  }
  return <div className={`payload-field ${container ? "is-container" : "is-value"}`}>
    {container ? <>
      {depth === 0 && keys.length > 3 && <div className="payload-field-search"><label className="sr-only" htmlFor={searchId}>Filter top-level fields by name</label><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5"/><path d="m13 13 4 4"/></svg><input id={searchId} type="search" value={query} placeholder="Find a field by name…" onChange={event => { setQuery(event.target.value); setLimit(20); setOpen(true); }}/><span>{filteredKeys.length} / {keys.length}</span></div>}
      <button type="button" className="payload-field-heading" aria-expanded={open} onClick={() => setOpen(current => !current)}><span className="payload-field-chevron" aria-hidden="true">{open ? "⌄" : "›"}</span><span className="payload-token-key">{depth === 0 ? "Recorded fields" : name}</span><small>{Array.isArray(value) ? "Array" : "Object"} · {keys.length} {Array.isArray(value) ? "items" : "fields"}</small></button>
      {open && <div className="payload-field-children">{filteredKeys.length ? filteredKeys.slice(0, limit).map(key => <FormattedField key={key} name={key} value={value[key]} depth={depth + 1}/>) : query ? <div className="payload-no-matches"><p>No matching fields</p><button type="button" onClick={() => setQuery("")}>Clear search</button></div> : <span className="payload-token-null">{Array.isArray(value) ? "[]" : "{}"}</span>}{filteredKeys.length > limit && <button className="payload-show-more" type="button" onClick={() => setLimit(count => count + 20)}>Show next {Math.min(20, filteredKeys.length - limit)} · {filteredKeys.length - limit} remaining</button>}</div>}
    </> : <>
      <div className="payload-field-heading"><span className="payload-token-key">{name}</span><small className="payload-type-badge">{value === null ? "null" : typeof value}</small><button type="button" className="payload-copy-value" onClick={copyValue} aria-label={`Copy value of ${name}`} title="Copy this field’s complete value">{copyMessage === "Copied" ? "Copied ✓" : "Copy value"}</button></div>
      <div ref={fieldRef} className={`payload-field-value payload-token-${string ? "string" : value === null ? "null" : typeof value}`}>{string && value === "" ? '""' : renderedText}</div>
      {longText && <div className="payload-text-controls"><span>{section.text.length.toLocaleString()} characters{section.total > 1 ? " in this section" : ""}</span><button type="button" aria-expanded={showText} onClick={() => { setShowText(current => !current); fieldRef.current?.scrollTo({ top: 0 }); }}>{showText ? "Show less ↑" : "Read more ↓"}</button></div>}
      {copyMessage && <span className={copyMessage === "Copied" ? "sr-only" : "block px-3 py-2 text-[10px] text-[var(--text-secondary)]"} role="status">{copyMessage}</span>}
      {section.total > 1 && <div className="payload-field-pages"><button type="button" disabled={section.page === 0} onClick={() => { setPage(section.page - 1); fieldRef.current?.scrollTo({ top: 0 }); }}>Previous</button><span>Section {section.page + 1} / {section.total}</span><button type="button" disabled={section.page === section.total - 1} onClick={() => { setPage(section.page + 1); fieldRef.current?.scrollTo({ top: 0 }); }}>Next</button></div>}
    </>}
  </div>;
}

export function JsonPayloadViewer({ value, kind }) {
  const [pagination, setPagination] = useState(null);
  const page = pagination?.kind === kind ? pagination.page : 0;
  const [mode, setMode] = useState("formatted");
  const [wrap, setWrap] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [copyState, setCopyState] = useState(null);
  const contentRef = useRef(null);
  useEffect(() => { contentRef.current?.scrollTo({ top: 0, left: 0 }); }, [kind, mode]);
  const empty = value == null;
  const text = useMemo(() => serializePayload(value), [value]);
  const bytes = useMemo(() => new TextEncoder().encode(text).length, [text]);
  const section = payloadSection(text, page);
  const type = empty ? "No data" : Array.isArray(value) ? `Array · ${value.length} items` : typeof value === "object" ? `Object · ${Object.keys(value).length} fields` : typeof value;
  const changePage = next => { setPagination({ kind, page: next }); contentRef.current?.scrollTo({ top: 0, left: 0 }); };
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopyState({ text, kind, message: "JSON copied", success: true });
    } catch {
      setCopyState({ text, kind, message: "Couldn’t copy. Select the visible text and copy it manually.", success: false });
    }
  }
  const copyMessage = copyState?.text === text && copyState?.kind === kind ? copyState : null;
  return <div className={`execution-payload-viewer ${expanded ? "is-expanded" : ""}`}>
    <div className="execution-payload-toolbar"><span className="execution-payload-type">{type}{!empty && <span> · {payloadSizeLabel(bytes)}</span>}</span><div className="execution-payload-actions"><div className="payload-view-switch" role="group" aria-label="Payload display"><button type="button" aria-pressed={mode === "formatted"} onClick={() => setMode("formatted")}>Formatted</button><button type="button" aria-pressed={mode === "json"} onClick={() => setMode("json")}>JSON</button></div>{mode === "json" && <button type="button" disabled={empty} aria-pressed={wrap} onClick={() => setWrap(current => !current)}>Wrap lines</button>}<button type="button" disabled={empty} aria-pressed={expanded} onClick={() => setExpanded(current => !current)}>{expanded ? "Compact view" : "Expand view"}</button><button type="button" disabled={empty} onClick={copy} className="payload-copy-all" title="Copy the full JSON payload from this tab">{copyMessage?.success ? "Copied ✓" : "Copy JSON"}</button></div></div>
    <div ref={contentRef} className="execution-payload-content" tabIndex={empty ? undefined : 0} role="region" aria-label={`${kind} ${mode === "json" ? "JSON" : "formatted data"}${mode === "json" && section.total > 1 ? `, section ${section.page + 1} of ${section.total}` : ""}`}>
      {empty ? <div className="execution-payload-empty"><span aria-hidden="true">{kind === "error" ? "✓" : "{ }"}</span><p>{emptyPayloadMessages[kind]}</p></div> : mode === "formatted" ? <div className="payload-formatted"><FormattedField key={kind} name="Payload" value={value}/></div> : <pre className={wrap ? "is-wrapped" : ""}><ColoredJson text={text} section={section}/></pre>}
    </div>
    <div className="execution-payload-footer">
      <span className="execution-payload-feedback" role="status">{copyMessage?.message || (mode === "formatted" ? "Formatted for reading · Copy preserves original JSON" : section.total > 1 ? "Large payload · Copy JSON includes all sections" : "JSON · Read only")}</span>
      {!empty && mode === "json" && section.total > 1 && <nav aria-label={`${kind} payload sections`}><button type="button" disabled={section.page === 0} onClick={() => changePage(section.page - 1)} aria-label="Previous payload section">←</button><span aria-live="polite">Section {section.page + 1} / {section.total}</span><button type="button" disabled={section.page === section.total - 1} onClick={() => changePage(section.page + 1)} aria-label="Next payload section">→</button></nav>}
    </div>
  </div>;
}

export default function ExecutionPayloadViewer({ step }) {
  const id = useId();
  // Switch to the appropriate payload when status changes; preserve a user's
  // chosen tab across ordinary polling updates with the same status.
  const [selection, setSelection] = useState(null);
  const tab = selection?.status === step.status ? selection.tab : defaultPayloadTab(step.status);
  function choose(next) { setSelection({ status: step.status, tab: next }); }
  function navigate(event, index) {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % payloadTabs.length;
    else if (event.key === "ArrowLeft") next = (index + payloadTabs.length - 1) % payloadTabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = payloadTabs.length - 1;
    else return;
    event.preventDefault(); choose(payloadTabs[next]);
    event.currentTarget.parentElement.querySelectorAll('[role="tab"]')[next]?.focus();
  }
  return <section className="execution-payload-inspector" data-payload-tab={tab} aria-label={`Recorded data for ${step.node_name || step.node_id}`}>
    <div className="execution-payload-tabs" role="tablist" aria-label="Step payloads">{payloadTabs.map((kind, index) => <button key={kind} id={`${id}-${kind}`} role="tab" type="button" aria-selected={tab === kind} aria-controls={`${id}-panel`} tabIndex={tab === kind ? 0 : -1} onKeyDown={event => navigate(event, index)} onClick={() => choose(kind)}>{kind.charAt(0).toUpperCase() + kind.slice(1)}{step[kind] != null && <span aria-hidden="true" className={kind === "error" ? "has-error" : ""}/>}</button>)}</div>
    <div id={`${id}-panel`} role="tabpanel" aria-labelledby={`${id}-${tab}`}><JsonPayloadViewer kind={tab} value={step[tab]}/></div>
  </section>;
}
