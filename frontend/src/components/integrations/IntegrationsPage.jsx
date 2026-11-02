"use client";
import { useState } from "react";
import Image from "next/image";
import {
  Modal,
  primaryClass,
  secondaryClass,
} from "@/components/connections/ConnectionUI";
import { assistants, capabilities, prompts } from "@/lib/integrations";

export function AssistantMark({ assistant }) {
  return (
    <span
      aria-hidden="true"
      className={`integration-assistant-mark integration-assistant-mark--${assistant.id}`}
    >
      <Image
        src={
          assistant.id === "claude" ? "/brand/claude.svg" : "/brand/openai.svg"
        }
        width={28}
        height={28}
        alt=""
      />
    </span>
  );
}
export function CopyButton({ text, label = "Copy" }) {
  const [status, setStatus] = useState("");
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setStatus("Copied");
    } catch {
      setStatus("Copy unavailable. Select and copy the text manually.");
    }
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" className={secondaryClass} onClick={copy}>
        {label}
      </button>
      <span role="status" className="text-xs text-[var(--text-secondary)]">
        {status}
      </span>
    </div>
  );
}
export default function IntegrationsPage({ endpoint }) {
  const [assistant, setAssistant] = useState(null);
  return (
    <div className="integrations-page space-y-8 text-[var(--text-primary)]">
      <header className="integrations-page-header">
        <div>
          <h1 className="text-[28px] font-semibold tracking-tight">
            Integrations
          </h1>
          <p className="mt-2 max-w-2xl text-[13px] leading-6 text-[var(--text-secondary)]">
            Your Relay workflows, inside your favorite AI assistant.
          </p>
        </div>
        <span className="integrations-protocol-label">
          MCP integrations <span aria-hidden="true">/</span> OAuth access
        </span>
      </header>
      {!endpoint && (
        <p
          role="status"
          className="rounded-lg border border-[var(--border-default)] bg-[var(--surface)] p-4 text-sm"
        >
          Connection setup is not available yet. Your administrator needs to
          configure Relay’s public MCP endpoint. You can still explore the setup
          guides below.
        </p>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {assistants.map((item) => (
          <article key={item.id} className="integration-provider-card">
            <div className="integration-provider-heading">
              <AssistantMark assistant={item} />
              <div>
                <h2 className="text-[16px] font-semibold">{item.name}</h2>
                <p className="mt-1 text-[12px] text-[var(--text-tertiary)]">
                  {item.id === "claude" ? "Anthropic" : "OpenAI"}
                </p>
              </div>
              <span className="integration-provider-tag">AI assistant</span>
            </div>
            <p className="integration-provider-description">
              {item.description}
            </p>
            <div className="integration-provider-actions">
              <button
                disabled={!endpoint}
                className={primaryClass}
                onClick={() => setAssistant(item)}
              >
                Connect to {item.name}
              </button>
              <button
                className={secondaryClass}
                aria-label={`${item.name} Setup Guide`}
                onClick={() => setAssistant(item)}
              >
                Setup Guide
              </button>
            </div>
          </article>
        ))}
      </div>
      <section aria-labelledby="capabilities" className="integration-section">
        <div className="integration-section-heading">
          <span aria-hidden="true">01</span>
          <h2 id="capabilities" className="text-[14px] font-semibold">
            What you can do
          </h2>
        </div>
        <p className="mt-2 text-[12px] leading-6 text-[var(--text-secondary)]">
          Available tools depend on the OAuth permissions you authorize. Read
          access is the default.
        </p>
        <div className="integration-capabilities-grid">
          {capabilities.map(([title, body, scope]) => (
            <article key={title} className="integration-capability">
              <h3 className="text-sm font-semibold">{title}</h3>
              <p className="mt-2 text-[12px] leading-6 text-[var(--text-secondary)]">
                {body}
              </p>
              <p className="integration-scope">{scope}</p>
            </article>
          ))}
        </div>
      </section>
      <section aria-labelledby="prompts" className="integration-section">
        <div className="integration-section-heading">
          <span aria-hidden="true">02</span>
          <h2 id="prompts" className="text-[14px] font-semibold">
            Try a conversation
          </h2>
        </div>
        <p className="mt-2 text-[12px] leading-6 text-[var(--text-secondary)]">
          Once connected, start with one of these prompts.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {prompts.map((prompt) => (
            <div key={prompt} className="integration-prompt">
              <p className="select-text text-[13px] leading-6">{prompt}</p>
              <CopyButton text={prompt} label="Copy prompt" />
            </div>
          ))}
        </div>
      </section>
      <p className="text-xs leading-5 text-[var(--text-tertiary)]">
        Setup is completed in your assistant. Relay cannot verify whether
        ChatGPT or Claude is connected; verify access by listing workflows
        there. These integrations are not an endorsement by OpenAI or Anthropic.
      </p>
      {assistant && (
        <IntegrationSetupGuide
          assistant={assistant}
          endpoint={endpoint}
          onClose={() => setAssistant(null)}
        />
      )}
    </div>
  );
}

function IntegrationSetupGuide({ assistant, endpoint, onClose }) {
  const isChatGPT = assistant.id === "chatgpt";
  return (
    <Modal
      wide
      title={`Connect to ${assistant.name}`}
      description="Follow these three steps in a new tab."
      onClose={onClose}
      className="integration-setup-guide"
    >
      <ol className="integration-setup-steps">
        <li>
          <span className="integration-step-number" aria-hidden="true">
            1
          </span>
          <div>
            <h3>Open {assistant.name}</h3>
            <p>{assistant.steps[0]}</p>
            <a
              className={`${secondaryClass} mt-3`}
              href={assistant.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open {assistant.name} ↗
            </a>
          </div>
        </li>
        <li>
          <span className="integration-step-number" aria-hidden="true">
            2
          </span>
          <div>
            <h3>Enter these details</h3>
            <dl className="integration-setup-fields">
              <div>
                <dt>Name</dt>
                <dd>Relay</dd>
              </div>
              <div className="integration-setup-url">
                <dt>{isChatGPT ? "Server URL" : "MCP server URL"}</dt>
                <dd>
                  {endpoint ? (
                    <>
                      <code>{endpoint}</code>
                      <CopyButton text={endpoint} label="Copy URL" />
                    </>
                  ) : (
                    <span role="status">
                      Not configured yet. Ask your Relay administrator for the
                      URL.
                    </span>
                  )}
                </dd>
              </div>
              {isChatGPT && (
                <div>
                  <dt>Authentication</dt>
                  <dd>OAuth</dd>
                </div>
              )}
            </dl>
            {isChatGPT ? (
              <>
                <p>
                  Icon and description are optional. If asked for an OAuth
                  client method, choose automatic registration (DCR).
                </p>
                <p>
                  Review the warning, tick{" "}
                  <strong>I understand and want to continue</strong>, then click{" "}
                  <strong>Create as a plugin</strong>.
                </p>
              </>
            ) : (
              <p>
                Click <strong>Continue</strong>. Choose{" "}
                <strong>Sign in now</strong> and{" "}
                <strong>Register automatically</strong> when asked, then click{" "}
                <strong>Add</strong>.
              </p>
            )}
          </div>
        </li>
        <li>
          <span className="integration-step-number" aria-hidden="true">
            3
          </span>
          <div>
            <h3>Sign in and try Relay</h3>
            <p>{assistant.steps[2]}</p>
            <div className="integration-setup-prompt">
              <p>Send this message:</p>
              <code>List all my Relay workflows.</code>
            </div>
          </div>
        </li>
      </ol>
      <div className="integration-setup-help">
        <details>
          <summary>Troubleshooting</summary>
          <div className="space-y-3 pt-3">
            <p>
              <strong>Can’t see Add?</strong> Ask your workspace administrator
              to allow custom {isChatGPT ? "plugins" : "connectors"}.
            </p>
            <p>
              <strong>Sign-in error?</strong> Use OAuth with automatic client
              registration (DCR). In ChatGPT, look under Advanced OAuth
              settings. Reconnect if your session has expired.
            </p>
            <p>
              <strong>Server unreachable?</strong> Ask your Relay administrator
              to check the public MCP URL.
            </p>
            <p>
              <strong>Can list but can’t run?</strong> Read access is the
              default. Running or editing workflows needs additional
              permissions. Your assistant can access the workflow data you
              authorize.
            </p>
            <a
              href={assistant.guide}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-4"
            >
              Official {assistant.name} guide ↗
            </a>
          </div>
        </details>
      </div>
    </Modal>
  );
}
