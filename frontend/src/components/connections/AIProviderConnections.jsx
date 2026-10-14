"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createAIConnection, listAIConnections, getAIConnection, updateAIConnection, deleteAIConnection, testAIConnection, listAIConnectionModels } from "@/services/aiProviderConnections";
import { Modal, Field, inputClass, buttonClass, primaryClass, secondaryClass } from "./ConnectionUI";
import { AI_PROVIDERS, aiConnectionPayload, aiConnectionError } from "./aiConnectionForm";

const emptyForm = () => ({ name: "", provider: "openai", api_key: "", status: "active" });
const providerName = (id) => AI_PROVIDERS.find((provider) => provider.id === id)?.name || id;

export default function AIProviderConnections() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [reload, setReload] = useState(0);
  const [modal, setModal] = useState(null);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [errors, setErrors] = useState({});
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [models, setModels] = useState(null);
  const [result, setResult] = useState(null);
  const locked = useRef(false);
  const alive = useRef(false);
  const requestId = useRef(0);

  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; };
  }, []);

  useEffect(() => {
    let current = true;
    listAIConnections().then((data) => {
      if (!Array.isArray(data)) throw new Error("Invalid connection list");
      if (current) { setItems(data); setLoadError(""); }
    }).catch((error) => { if (current) setLoadError(aiConnectionError(error)); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [reload]);

  const refresh = () => { setLoading(true); setReload((value) => value + 1); };
  const close = useCallback(() => {
    if (locked.current) return;
    requestId.current++;
    setModal(null); setSelected(null); setForm(emptyForm()); setVisible(false);
    setErrors({}); setModels(null); setResult(null);
  }, []);

  const open = (type, item = null) => {
    setSelected(item); setForm(emptyForm()); setVisible(false); setErrors({});
    setModels(null); setResult(null); setModal(type); setNotice("");
  };

  const loadDetails = async (item) => {
    open("details", item);
    const id = ++requestId.current;
    try {
      const data = await getAIConnection(item.id);
      if (!data?.id || data.id !== item.id) throw new Error("Invalid connection details");
      if (!alive.current || id !== requestId.current) return;
      setSelected(data);
      setForm({ name: data.name, provider: data.provider, status: data.status, api_key: "" });
      setModal("edit");
    } catch (error) {
      if (alive.current && id === requestId.current) setErrors({ api: aiConnectionError(error) });
    }
  };

  const save = async (event) => {
    event.preventDefault();
    if (locked.current) return;
    const editing = modal === "edit";
    const { data, errors: validation } = aiConnectionPayload(form, editing);
    if (Object.keys(validation).length) { setErrors(validation); return; }
    locked.current = true; setBusy(true); setErrors({});
    try {
      if (editing) await updateAIConnection(selected.id, data);
      else await createAIConnection(data);
      if (!alive.current) return;
      setForm(emptyForm()); setVisible(false); setModal(null); setSelected(null);
      setNotice(editing ? "AI connection updated." : "AI connection saved. Test it to verify its credentials.");
      refresh();
    } catch (error) {
      if (alive.current) {
        setForm((current) => ({ ...current, api_key: "" })); setVisible(false);
        setErrors({ api: aiConnectionError(error) });
      }
    } finally { locked.current = false; if (alive.current) setBusy(false); }
  };

  const remove = async () => {
    if (locked.current || !selected) return;
    locked.current = true; setBusy(true); setErrors({});
    try {
      await deleteAIConnection(selected.id);
      if (!alive.current) return;
      setModal(null); setSelected(null); setNotice("AI connection deleted."); refresh();
    } catch (error) { if (alive.current) setErrors({ api: aiConnectionError(error) }); }
    finally { locked.current = false; if (alive.current) setBusy(false); }
  };

  const inspect = async (type, item) => {
    open(type, item);
    const id = ++requestId.current;
    try {
      const data = type === "models" ? await listAIConnectionModels(item.id) : await testAIConnection(item.id);
      if (!alive.current || id !== requestId.current) return;
      if (type === "models") {
        if (!Array.isArray(data?.models)) throw new Error("Invalid model catalog");
        setModels(data.models);
      } else {
        setResult(data?.success === true);
        if (data?.success !== true) setErrors({ api: aiConnectionError({ message: data?.message }) });
      }
    } catch (error) {
      if (alive.current && id === requestId.current) setErrors({ api: aiConnectionError(error) });
    }
  };

  return <section aria-labelledby="ai-providers-title" className="space-y-5">
    <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div><h2 id="ai-providers-title" className="text-[18px] font-semibold">AI Providers</h2><p className="mt-1 text-[13px] text-[var(--text-secondary)]">Bring your own API key to connect AI providers for your workspace.</p></div>
      <button type="button" onClick={() => open("create")} className={primaryClass}>＋ Add AI Connection</button>
    </header>
    {loading && <p role="status" className="flex items-center gap-2 py-8 text-[13px] text-[var(--text-secondary)]"><span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--border-default)] border-t-[var(--accent)]" />Loading AI connections…</p>}
    {!loading && loadError && <div role="alert" className="rounded-md border border-[var(--border-subtle)] p-8 text-center"><h3 className="text-[14px] font-semibold">Unable to load AI connections</h3><p className="mt-2 text-[13px] text-[var(--text-secondary)]">{loadError}</p><button type="button" onClick={refresh} className={`${secondaryClass} mt-4`}>Retry</button></div>}
    {!loading && !loadError && items.length === 0 && <div className="rounded-md border border-dashed border-[var(--border-default)] px-6 py-16 text-center"><h3 className="text-[16px] font-semibold">No AI providers connected yet.</h3><p className="mx-auto mt-2 max-w-md text-[13px] leading-5 text-[var(--text-secondary)]">Connect OpenAI, Gemini, or Claude using your own API key to use AI models in Relay workflows.</p><button type="button" onClick={() => open("create")} className={`${primaryClass} mt-5`}>Add Connection</button></div>}
    {!loading && !loadError && <div className="grid gap-3 sm:grid-cols-2">{items.map((item) => <article key={item.id} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] p-4 transition-colors hover:border-[var(--border-strong)]">
      <div className="flex items-start gap-3.5"><div aria-hidden="true" className="grid h-12 w-12 shrink-0 place-items-center rounded-lg border border-[var(--border-subtle)] bg-[var(--input-bg)] text-[var(--text-secondary)]"><svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6Z" /></svg></div><div className="min-w-0"><h3 className="break-words text-[14px] font-medium">{item.name}</h3><p className="mt-1 text-[12px] text-[var(--text-secondary)]">{providerName(item.provider)}</p><p className="mt-1.5 flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)]"><span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${item.status === "active" ? "bg-emerald-500" : "bg-[var(--text-disabled)]"}`} />{item.status === "active" ? "Active" : "Inactive"}</p></div></div>
      <div className="mt-4 flex flex-wrap gap-2" aria-label={`Manage ${item.name}`}><button type="button" className={secondaryClass} onClick={() => inspect("test", item)}>Test Connection</button><button type="button" className={secondaryClass} onClick={() => inspect("models", item)}>View Models</button><button type="button" className={secondaryClass} onClick={() => loadDetails(item)}>Edit</button><button type="button" className={`${buttonClass} border-red-500/30 text-red-500 hover:bg-red-500/5`} onClick={() => open("delete", item)}>Delete</button></div>
    </article>)}</div>}
    {notice && <div role="status" className="connection-toast fixed bottom-5 right-5 z-[120] max-w-[calc(100%-2.5rem)] rounded-md border border-[var(--border-default)] bg-[var(--surface)] px-4 py-2.5 text-[13px]">{notice}<button type="button" aria-label="Dismiss notification" onClick={() => setNotice("")} className="ml-3">×</button></div>}
    {(modal === "create" || modal === "edit") && <Modal title={modal === "edit" ? "Edit AI connection" : "Add AI connection"} description="Credentials are stored securely and never displayed after saving." onClose={close}>
      <form onSubmit={save} className="space-y-4" aria-busy={busy}>
        <fieldset disabled={busy} className="space-y-4">
          <Field label="Provider" htmlFor="ai-provider" error={errors.provider}><select id="ai-provider" className={inputClass} value={form.provider} disabled={modal === "edit"} onChange={(event) => setForm((current) => ({ ...current, provider: event.target.value }))}>{AI_PROVIDERS.map((provider) => <option key={provider.id} value={provider.id}>{provider.name} — {provider.description}</option>)}</select></Field>
          <Field label="Connection name" htmlFor="ai-name" error={errors.name}><input id="ai-name" className={inputClass} required maxLength={100} value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="e.g. OpenAI Production" /></Field>
          {modal === "edit" && <Field label="Status" htmlFor="ai-status" error={errors.status}><select id="ai-status" className={inputClass} value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}><option value="active">Active</option><option value="inactive">Inactive</option></select></Field>}
          <Field label={modal === "edit" ? "Replacement API key (optional)" : "API key"} htmlFor="ai-key" error={errors.api_key} helper={modal === "edit" ? "Leave empty to keep the current key." : "Saving does not verify credentials. Use Test Connection after saving."}><div className="relative"><input id="ai-key" className={`${inputClass} pr-16`} type={visible ? "text" : "password"} required={modal === "create"} autoComplete="new-password" spellCheck={false} value={form.api_key} onChange={(event) => setForm((current) => ({ ...current, api_key: event.target.value }))} /><button type="button" onClick={() => setVisible((current) => !current)} aria-label={visible ? "Hide API key" : "Show API key"} className="absolute right-2 top-1/2 -translate-y-1/2 px-1 text-[11px] text-[var(--text-tertiary)]">{visible ? "Hide" : "Show"}</button></div></Field>
        </fieldset>
        {errors.api && <p role="alert" className="text-[12px] text-red-500">{errors.api}</p>}
        <div className="flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4"><button type="button" disabled={busy} onClick={close} className={secondaryClass}>Cancel</button><button type="submit" disabled={busy} className={primaryClass}>{busy ? "Saving…" : "Save Connection"}</button></div>
      </form>
    </Modal>}
    {modal === "delete" && <Modal title={`Delete ${selected.name}?`} onClose={close}><p className="text-[13px] leading-5 text-[var(--text-secondary)]">Deleting this connection removes its stored credentials. Workflows using this connection may fail until another connection is selected.</p>{errors.api && <p role="alert" className="mt-3 text-[12px] text-red-500">{errors.api}</p>}<div className="mt-5 flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4"><button type="button" disabled={busy} onClick={close} className={secondaryClass}>Cancel</button><button type="button" disabled={busy} onClick={remove} className={`${buttonClass} border-red-500/40 bg-red-600 text-white hover:bg-red-700`}>{busy ? "Deleting…" : "Delete connection"}</button></div></Modal>}
    {["details", "models", "test"].includes(modal) && <Modal title={modal === "models" ? "Available Models" : modal === "test" ? "Test Connection" : "Edit AI connection"} description={`Connection: ${selected.name}`} onClose={close} wide={modal === "models"}>
      {errors.api ? <div role="alert"><p className="text-[13px] text-red-500">{errors.api}</p><button type="button" className={`${secondaryClass} mt-4`} onClick={() => modal === "details" ? loadDetails(selected) : inspect(modal, selected)}>Retry</button></div> : modal === "models" && models !== null ? <>
        <p className="mb-3 text-[12px] text-[var(--text-secondary)]">Informational catalog. Some models may not support text generation or future AI workflow nodes.</p>
        {models.length === 0 ? <p className="text-[13px]">No models are available for this connection.</p> : <div tabIndex={0} aria-label="Available provider models" className="max-h-80 overflow-auto rounded-md border border-[var(--border-subtle)]"><table className="w-full text-left text-[12px]"><thead className="sticky top-0 bg-[var(--elevated)]"><tr><th className="p-3">Model Name</th><th className="p-3">Model ID</th></tr></thead><tbody>{models.map((model, index) => <tr key={`${model.id}-${index}`} className="border-t border-[var(--border-subtle)]"><td className="break-words p-3">{model.name || model.id}</td><td className="break-all p-3 font-mono text-[11px] text-[var(--text-secondary)]">{model.id}</td></tr>)}</tbody></table></div>}
      </> : modal === "test" && result === true ? <div role="status"><p className="text-[14px] font-medium">Connection verified successfully.</p><p className="mt-2 text-[12px] text-[var(--text-secondary)]">This verifies credentials, not access to every model or available billing quota.</p></div> : <p role="status" className="text-[13px] text-[var(--text-secondary)]">{modal === "test" ? "Testing connection…" : modal === "models" ? "Loading models…" : "Loading connection…"}</p>}
    </Modal>}
  </section>;
}
