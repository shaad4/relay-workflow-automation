"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  createAIConnection,
  listAIConnections,
  getAIConnection,
  updateAIConnection,
  deleteAIConnection,
  testAIConnection,
  listAIConnectionModels,
} from "@/services/aiProviderConnections";
import {
  Modal,
  Field,
  inputClass,
  buttonClass,
  secondaryClass,
} from "./ConnectionUI";
import {
  AI_PROVIDERS,
  aiConnectionPayload,
  aiConnectionError,
} from "./aiConnectionForm";

const actionClass = `${buttonClass} border-[var(--text-primary)] bg-[var(--text-primary)] text-[var(--surface)] hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--text-primary)]`;
const emptyForm = () => ({
  name: "",
  provider: "openai",
  api_key: "",
  status: "active",
});
const providerName = (id) =>
  AI_PROVIDERS.find((provider) => provider.id === id)?.name || id;

function ProviderLogo({ provider, size = 24 }) {
  const asset = { openai: "openai", gemini: "gemini", anthropic: "claude" }[
    provider
  ];
  return (
    <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-black/5 bg-white shadow-sm">
      {asset ? (
        <Image src={`/brand/${asset}.svg`} alt="" width={size} height={size} />
      ) : (
        <span className="text-black">AI</span>
      )}
    </span>
  );
}

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
    return () => {
      alive.current = false;
    };
  }, []);

  useEffect(() => {
    let current = true;
    listAIConnections()
      .then((data) => {
        if (!Array.isArray(data)) throw new Error("Invalid connection list");
        if (current) {
          setItems(data);
          setLoadError("");
        }
      })
      .catch((error) => {
        if (current) setLoadError(aiConnectionError(error));
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [reload]);

  const refresh = () => {
    setLoading(true);
    setReload((value) => value + 1);
  };
  const close = useCallback(() => {
    if (locked.current) return;
    requestId.current++;
    setModal(null);
    setSelected(null);
    setForm(emptyForm());
    setVisible(false);
    setErrors({});
    setModels(null);
    setResult(null);
  }, []);

  const open = (type, item = null) => {
    setSelected(item);
    setForm(emptyForm());
    setVisible(false);
    setErrors({});
    setModels(null);
    setResult(null);
    setModal(type);
    setNotice("");
  };

  const loadDetails = async (item) => {
    open("details", item);
    const id = ++requestId.current;
    try {
      const data = await getAIConnection(item.id);
      if (!data?.id || data.id !== item.id)
        throw new Error("Invalid connection details");
      if (!alive.current || id !== requestId.current) return;
      setSelected(data);
      setForm({
        name: data.name,
        provider: data.provider,
        status: data.status,
        api_key: "",
      });
      setModal("edit");
    } catch (error) {
      if (alive.current && id === requestId.current)
        setErrors({ api: aiConnectionError(error) });
    }
  };

  const save = async (event) => {
    event.preventDefault();
    if (locked.current) return;
    const editing = modal === "edit";
    const { data, errors: validation } = aiConnectionPayload(form, editing);
    if (Object.keys(validation).length) {
      setErrors(validation);
      return;
    }
    locked.current = true;
    setBusy(true);
    setErrors({});
    try {
      if (editing) await updateAIConnection(selected.id, data);
      else await createAIConnection(data);
      if (!alive.current) return;
      setForm(emptyForm());
      setVisible(false);
      setModal(null);
      setSelected(null);
      setNotice(
        editing
          ? "AI connection updated."
          : "AI connection saved. Test it to verify its credentials.",
      );
      refresh();
    } catch (error) {
      if (alive.current) {
        setForm((current) => ({ ...current, api_key: "" }));
        setVisible(false);
        setErrors({ api: aiConnectionError(error) });
      }
    } finally {
      locked.current = false;
      if (alive.current) setBusy(false);
    }
  };

  const remove = async () => {
    if (locked.current || !selected) return;
    locked.current = true;
    setBusy(true);
    setErrors({});
    try {
      await deleteAIConnection(selected.id);
      if (!alive.current) return;
      setModal(null);
      setSelected(null);
      setNotice("AI connection deleted.");
      refresh();
    } catch (error) {
      if (alive.current) setErrors({ api: aiConnectionError(error) });
    } finally {
      locked.current = false;
      if (alive.current) setBusy(false);
    }
  };

  const inspect = async (type, item) => {
    open(type, item);
    const id = ++requestId.current;
    try {
      const data =
        type === "models"
          ? await listAIConnectionModels(item.id)
          : await testAIConnection(item.id);
      if (!alive.current || id !== requestId.current) return;
      if (type === "models") {
        if (!Array.isArray(data?.models))
          throw new Error("Invalid model catalog");
        setModels(data.models);
      } else {
        setResult(data?.success === true);
        if (data?.success !== true)
          setErrors({ api: aiConnectionError({ message: data?.message }) });
      }
    } catch (error) {
      if (alive.current && id === requestId.current)
        setErrors({ api: aiConnectionError(error) });
    }
  };

  return (
    <section aria-labelledby="ai-providers-title" className="space-y-5 pt-2">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2
            id="ai-providers-title"
            className="flex items-center gap-2.5 text-[16px] font-semibold"
          >
            AI Providers
            {!loading && !loadError && (
              <span className="rounded-md border border-[var(--border-subtle)] px-1.5 py-0.5 text-[10px] font-normal tabular-nums text-[var(--text-tertiary)]">
                {items.length}
              </span>
            )}
          </h2>
          <p className="mt-1 text-[13px] text-[var(--text-secondary)]">
            Manage the provider connections available to your workspace.
          </p>
        </div>
        <button
          type="button"
          onClick={() => open("create")}
          className={`${actionClass} self-start sm:self-auto`}
        >
          ＋ Add connection
        </button>
      </header>
      {loading && (
        <div
          role="status"
          className="rounded-lg border border-[var(--border-default)] bg-[var(--surface)]"
        >
          <span className="sr-only">Loading AI connections…</span>
          <div aria-hidden="true">
            <div className="hidden items-center justify-between border-b border-[var(--border-subtle)] px-5 py-2.5 text-[11px] text-[var(--text-tertiary)] sm:flex">
              <span>Connection</span>
              <span>Manage</span>
            </div>
            <div className="divide-y divide-[var(--border-subtle)]">
              {[0, 1, 2].map((row) => (
                <div
                  key={row}
                  className="flex animate-pulse flex-col gap-4 px-4 py-5 motion-reduce:animate-none sm:flex-row sm:items-center sm:justify-between sm:px-5"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="h-11 w-11 shrink-0 rounded-xl bg-[var(--elevated)]" />
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        <div className="h-3.5 w-28 rounded bg-[var(--elevated)]" />
                        <div className="h-5 w-14 rounded-full bg-[var(--elevated)]" />
                      </div>
                      <div className="h-3 w-24 rounded bg-[var(--elevated)]" />
                    </div>
                  </div>
                  <div className="flex items-center gap-2 self-end sm:self-auto">
                    <div className="h-8 w-20 rounded-md bg-[var(--elevated)]" />
                    <div className="h-8 w-28 rounded-md bg-[var(--elevated)]" />
                    <div className="h-8 w-8 rounded-md bg-[var(--elevated)]" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      {!loading && loadError && (
        <div
          role="alert"
          className="rounded-md border border-[var(--border-subtle)] p-8 text-center"
        >
          <h3 className="text-[14px] font-semibold">
            Unable to load AI connections
          </h3>
          <p className="mt-2 text-[13px] text-[var(--text-secondary)]">
            {loadError}
          </p>
          <button
            type="button"
            onClick={refresh}
            className={`${secondaryClass} mt-4`}
          >
            Retry
          </button>
        </div>
      )}
      {!loading && !loadError && items.length === 0 && (
        <div className="flex flex-col items-center rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] px-6 py-12 text-center">
          <div className="mb-5 flex -space-x-2">
            {AI_PROVIDERS.map((provider) => (
              <div
                key={provider.id}
                className="rounded-xl ring-4 ring-[var(--surface)]"
              >
                <ProviderLogo provider={provider.id} size={22} />
              </div>
            ))}
          </div>
          <h3 className="text-[16px] font-semibold">
            Connect your first AI provider
          </h3>
          <p className="mx-auto mt-2 max-w-sm text-[13px] leading-6 text-[var(--text-secondary)]">
            Bring your OpenAI, Gemini, or Claude API key. Your team can manage
            connections together in this workspace.
          </p>
          <button
            type="button"
            onClick={() => open("create")}
            className={`${actionClass} mt-5`}
          >
            ＋ Add connection
          </button>
          <p className="mt-4 text-[11px] text-[var(--text-tertiary)]">
            Keys are stored securely and never shown after saving.
          </p>
        </div>
      )}
      {!loading && !loadError && items.length > 0 && (
        <div className="rounded-lg border border-[var(--border-default)] bg-[var(--surface)]">
          <div className="hidden items-center justify-between border-b border-[var(--border-subtle)] px-5 py-2.5 text-[11px] text-[var(--text-tertiary)] sm:flex">
            <span>Connection</span>
            <span>Manage</span>
          </div>
          <div className="divide-y divide-[var(--border-subtle)]">
            {items.map((item) => (
              <article
                key={item.id}
                className="flex flex-col gap-4 px-4 py-5 transition-colors hover:bg-[var(--elevated)]/40 sm:flex-row sm:items-center sm:justify-between sm:px-5"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <ProviderLogo provider={item.provider} size={22} />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <h3 className="break-all text-[13px] font-medium">
                        {item.name}
                      </h3>
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] text-[var(--text-secondary)]">
                        <span
                          aria-hidden="true"
                          className={`h-1.5 w-1.5 rounded-full ${item.status === "active" ? "bg-emerald-500" : "bg-[var(--text-disabled)]"}`}
                        />
                        {item.status === "active" ? "Active" : "Inactive"}
                      </span>
                    </div>
                    <p className="mt-1 text-[12px] text-[var(--text-tertiary)]">
                      {providerName(item.provider)}
                      <span className="mx-2 text-[var(--border-strong)]">
                        /
                      </span>
                      API key
                    </p>
                  </div>
                </div>
                <div
                  className="flex shrink-0 items-center gap-2 self-end sm:self-auto"
                  aria-label={`Manage ${item.name}`}
                >
                  <button
                    type="button"
                    className="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-[12px] text-[var(--text-secondary)] transition-colors hover:bg-[var(--elevated)] hover:text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
                    onClick={() => inspect("models", item)}
                  >
                    Models
                    <svg
                      aria-hidden="true"
                      width="13"
                      height="13"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    >
                      <path d="m9 5 7 7-7 7" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    className={`${secondaryClass} h-8 px-3 text-[12px]`}
                    onClick={() => inspect("test", item)}
                  >
                    Test connection
                  </button>
                  <details
                    className="group relative"
                    onKeyDown={(event) => {
                      if (event.key === "Escape") {
                        event.currentTarget.open = false;
                        event.currentTarget.querySelector("summary").focus();
                      }
                    }}
                    onBlur={(event) => {
                      if (!event.currentTarget.contains(event.relatedTarget))
                        event.currentTarget.open = false;
                    }}
                  >
                    <summary
                      aria-label={`More actions for ${item.name}`}
                      className="grid h-8 w-8 cursor-pointer list-none place-items-center rounded-md text-[var(--text-tertiary)] transition-colors hover:bg-[var(--elevated)] hover:text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-[var(--accent)] [&::-webkit-details-marker]:hidden"
                    >
                      <svg
                        aria-hidden="true"
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <circle cx="5" cy="12" r="1.5" />
                        <circle cx="12" cy="12" r="1.5" />
                        <circle cx="19" cy="12" r="1.5" />
                      </svg>
                    </summary>
                    <div className="absolute right-0 top-10 z-20 w-44 rounded-lg border border-[var(--border-default)] bg-[var(--surface)] p-1 shadow-xl">
                      <button
                        type="button"
                        className="w-full rounded-md px-3 py-2 text-left text-[12px] hover:bg-[var(--elevated)]"
                        onClick={(event) => {
                          event.currentTarget.closest("details").open = false;
                          loadDetails(item);
                        }}
                      >
                        Edit connection
                      </button>
                      <div className="my-1 h-px bg-[var(--border-subtle)]" />
                      <button
                        type="button"
                        className="w-full rounded-md px-3 py-2 text-left text-[12px] text-red-500 hover:bg-red-500/5"
                        onClick={(event) => {
                          event.currentTarget.closest("details").open = false;
                          open("delete", item);
                        }}
                      >
                        Delete connection
                      </button>
                    </div>
                  </details>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}
      {!loading && !loadError && items.length > 0 && (
        <p className="text-[11px] text-[var(--text-tertiary)]">
          Connections are shared with your workspace. API keys are encrypted and
          never displayed.
        </p>
      )}
      {notice && (
        <div
          role="status"
          className="connection-toast fixed bottom-5 right-5 z-[120] max-w-[calc(100%-2.5rem)] rounded-md border border-[var(--border-default)] bg-[var(--surface)] px-4 py-2.5 text-[13px]"
        >
          {notice}
          <button
            type="button"
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
            className="ml-3"
          >
            ×
          </button>
        </div>
      )}
      {(modal === "create" || modal === "edit") && (
        <Modal
          title={modal === "edit" ? "Edit AI connection" : "Add AI connection"}
          description="Choose a provider and bring your own API key."
          onClose={close}
          wide
        >
          <form onSubmit={save} className="space-y-5" aria-busy={busy}>
            <fieldset disabled={busy} className="space-y-4">
              <fieldset disabled={modal === "edit"} className="space-y-2.5">
                <legend className="mb-2.5 text-[11px] font-semibold uppercase tracking-[.1em] text-[var(--text-tertiary)]">
                  Choose your provider
                </legend>
                <div className="grid grid-cols-3 gap-2">
                  {AI_PROVIDERS.map((provider) => (
                    <label
                      key={provider.id}
                      className="relative cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="ai-provider"
                        value={provider.id}
                        checked={form.provider === provider.id}
                        onChange={() =>
                          setForm((current) => ({
                            ...current,
                            provider: provider.id,
                          }))
                        }
                        className="peer sr-only"
                      />
                      <span className="flex h-full flex-col items-center gap-2 rounded-xl border border-[var(--border-default)] bg-[var(--input-bg)] px-2 py-4 text-center transition-all peer-checked:border-[var(--accent)] peer-checked:bg-[var(--accent)]/5 peer-checked:ring-1 peer-checked:ring-[var(--accent)] peer-focus-visible:outline-2 peer-focus-visible:outline-offset-4 peer-focus-visible:outline-[var(--accent)] peer-disabled:cursor-default hover:bg-[var(--elevated)]">
                        <ProviderLogo provider={provider.id} />
                        <span className="text-[12px] font-semibold">
                          {provider.id === "gemini"
                            ? "Gemini"
                            : provider.id === "anthropic"
                              ? "Claude"
                              : "OpenAI"}
                        </span>
                        <span className="hidden text-[10px] text-[var(--text-tertiary)] sm:block">
                          {provider.description}
                        </span>
                      </span>
                      {form.provider === provider.id && (
                        <span
                          aria-hidden="true"
                          className="absolute right-2 top-2 grid h-4 w-4 place-items-center rounded-full bg-[var(--accent)] text-[10px] text-[var(--accent-foreground)]"
                        >
                          ✓
                        </span>
                      )}
                    </label>
                  ))}
                </div>
                {errors.provider && (
                  <p role="alert" className="text-[12px] text-red-500">
                    {errors.provider}
                  </p>
                )}
              </fieldset>
              <div className="flex items-center gap-3 pt-2">
                <span className="text-[11px] font-semibold uppercase tracking-[.1em] text-[var(--text-tertiary)]">
                  Connection details
                </span>
                <span className="h-px flex-1 bg-[var(--border-subtle)]" />
              </div>
              <Field
                label="Connection name"
                htmlFor="ai-name"
                error={errors.name}
              >
                <input
                  id="ai-name"
                  className={`${inputClass} h-11 rounded-lg`}
                  required
                  maxLength={100}
                  value={form.name}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      name: event.target.value,
                    }))
                  }
                  placeholder={`e.g. ${providerName(form.provider)} Production`}
                />
              </Field>
              {modal === "edit" && (
                <Field label="Status" htmlFor="ai-status" error={errors.status}>
                  <select
                    id="ai-status"
                    className={inputClass}
                    value={form.status}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        status: event.target.value,
                      }))
                    }
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </Field>
              )}
              <Field
                label={
                  modal === "edit"
                    ? "Replacement API key (optional)"
                    : "API key"
                }
                htmlFor="ai-key"
                error={errors.api_key}
                helper={
                  modal === "edit"
                    ? "Leave empty to keep the current key."
                    : "Saving does not verify credentials. Use Test Connection after saving."
                }
              >
                <div className="relative">
                  <input
                    id="ai-key"
                    className={`${inputClass} h-11 rounded-lg pr-16 font-mono`}
                    placeholder="Enter your API key"
                    type={visible ? "text" : "password"}
                    required={modal === "create"}
                    autoComplete="new-password"
                    spellCheck={false}
                    value={form.api_key}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        api_key: event.target.value,
                      }))
                    }
                  />
                  <button
                    type="button"
                    onClick={() => setVisible((current) => !current)}
                    aria-label={visible ? "Hide API key" : "Show API key"}
                    className="absolute right-2 top-1/2 -translate-y-1/2 px-1 text-[11px] text-[var(--text-tertiary)]"
                  >
                    {visible ? "Hide" : "Show"}
                  </button>
                </div>
              </Field>
            </fieldset>
            <div className="flex items-start gap-2.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--elevated)] p-3">
              <svg
                aria-hidden="true"
                className="mt-0.5 h-4 w-4 shrink-0 text-[var(--text-tertiary)]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <rect x="5" y="10" width="14" height="11" rx="2" />
                <path d="M8 10V7a4 4 0 0 1 8 0v3" />
              </svg>
              <p className="text-[11px] leading-5 text-[var(--text-secondary)]">
                Your API key is encrypted and stored securely. It will never be
                displayed after saving.
              </p>
            </div>
            {errors.api && (
              <p role="alert" className="text-[12px] text-red-500">
                {errors.api}
              </p>
            )}
            <div className="flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4">
              <button
                type="button"
                disabled={busy}
                onClick={close}
                className={secondaryClass}
              >
                Cancel
              </button>
              <button type="submit" disabled={busy} className={actionClass}>
                {busy ? "Saving…" : "Save Connection"}
              </button>
            </div>
          </form>
        </Modal>
      )}
      {modal === "delete" && (
        <Modal title={`Delete ${selected.name}?`} onClose={close}>
          <p className="text-[13px] leading-5 text-[var(--text-secondary)]">
            Deleting this connection removes its stored credentials. Workflows
            using this connection may fail until another connection is selected.
          </p>
          {errors.api && (
            <p role="alert" className="mt-3 text-[12px] text-red-500">
              {errors.api}
            </p>
          )}
          <div className="mt-5 flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4">
            <button
              type="button"
              disabled={busy}
              onClick={close}
              className={secondaryClass}
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={remove}
              className={`${buttonClass} border-red-500/40 bg-red-600 text-white hover:bg-red-700`}
            >
              {busy ? "Deleting…" : "Delete connection"}
            </button>
          </div>
        </Modal>
      )}
      {["details", "models", "test"].includes(modal) && (
        <Modal
          title={
            modal === "models"
              ? "Available Models"
              : modal === "test"
                ? "Test Connection"
                : "Edit AI connection"
          }
          description={`Connection: ${selected.name}`}
          onClose={close}
          wide={modal === "models"}
        >
          {errors.api ? (
            <div role="alert">
              <p className="text-[13px] text-red-500">{errors.api}</p>
              <button
                type="button"
                className={`${secondaryClass} mt-4`}
                onClick={() =>
                  modal === "details"
                    ? loadDetails(selected)
                    : inspect(modal, selected)
                }
              >
                Retry
              </button>
            </div>
          ) : modal === "models" && models !== null ? (
            <>
              <p className="mb-3 text-[12px] text-[var(--text-secondary)]">
                Informational catalog. Some models may not support text
                generation or future AI workflow nodes.
              </p>
              {models.length === 0 ? (
                <p className="text-[13px]">
                  No models are available for this connection.
                </p>
              ) : (
                <div
                  tabIndex={0}
                  aria-label="Available provider models"
                  className="max-h-80 overflow-auto rounded-md border border-[var(--border-subtle)]"
                >
                  <table className="w-full text-left text-[12px]">
                    <thead className="sticky top-0 bg-[var(--elevated)]">
                      <tr>
                        <th className="p-3">Model Name</th>
                        <th className="p-3">Model ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {models.map((model, index) => (
                        <tr
                          key={`${model.id}-${index}`}
                          className="border-t border-[var(--border-subtle)]"
                        >
                          <td className="break-words p-3">
                            {model.name || model.id}
                          </td>
                          <td className="break-all p-3 font-mono text-[11px] text-[var(--text-secondary)]">
                            {model.id}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : modal === "test" && result === true ? (
            <div role="status">
              <p className="text-[14px] font-medium">
                Connection verified successfully.
              </p>
              <p className="mt-2 text-[12px] text-[var(--text-secondary)]">
                This verifies credentials, not access to every model or
                available billing quota.
              </p>
            </div>
          ) : (
            <p
              role="status"
              className="text-[13px] text-[var(--text-secondary)]"
            >
              {modal === "test"
                ? "Testing connection…"
                : modal === "models"
                  ? "Loading models…"
                  : "Loading connection…"}
            </p>
          )}
        </Modal>
      )}
    </section>
  );
}
