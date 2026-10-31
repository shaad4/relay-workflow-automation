"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useAuth } from "@/context/AuthContext";
import { Modal } from "@/components/connections/ConnectionUI";
import { assistants, announcementKey } from "@/lib/integrations";
import { AssistantMark } from "./IntegrationsPage";
const dismissedInSession = new Set();

export default function IntegrationAnnouncement({ enabled }) {
  const { user, isInitializing } = useAuth();
  // Remount on account changes so one account never inherits another's open dialog.
  return enabled && !isInitializing && user?.id && user?.workspace_id ? (
    <Announcement key={user.id} userId={user.id} />
  ) : null;
}
function Announcement({ userId }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const key = announcementKey(userId);
  useEffect(() => {
    try {
      if (localStorage.getItem(key) || dismissedInSession.has(key)) return;
    } catch {
      return;
    } // Do not repeatedly interrupt users when persistence is blocked.
    const timer = setTimeout(() => {
      // Only introduce the feature while the dashboard is idle, without stealing focus.
      if (
        document.visibilityState !== "visible" ||
        document.querySelector('[role="dialog"], dialog[open]') ||
        ![document.body, document.documentElement].includes(
          document.activeElement,
        )
      )
        return;
      setOpen(true);
    }, 900);
    const sync = (event) => {
      if (event.key === key && event.newValue) setOpen(false);
    };
    window.addEventListener("storage", sync);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("storage", sync);
    };
  }, [key]);
  function dismiss() {
    dismissedInSession.add(key);
    try {
      localStorage.setItem(key, "dismissed");
    } catch {
      /* Session fallback. */
    }
    setOpen(false);
  }
  if (!open) return null;
  return (
    <Modal
      wide
      title="Relay is now available in ChatGPT & Claude!"
      onClose={dismiss}
      className="integration-announcement"
      hideTitle
    >
      <div className="integration-announcement-art" aria-hidden="true">
        <span className="integration-announcement-eyebrow">
          INTRODUCING AI INTEGRATIONS
        </span>
        <div className="integration-brand-network">
          <div className="integration-brand-node">
            <AssistantMark assistant={assistants[0]} />
            <span>ChatGPT</span>
          </div>
          <span className="integration-brand-link">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m10 13 4-4m-6 6-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 2 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0" />
            </svg>
          </span>
          <div className="integration-brand-node integration-brand-node--relay">
            <div className="integration-relay-mark">
              <Image
                src="/brand/relay/relay-light.png"
                alt=""
                width={198}
                height={79}
                priority
              />
            </div>
            <span>Relay</span>
          </div>
          <span className="integration-brand-link">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m10 13 4-4m-6 6-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 2 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0" />
            </svg>
          </span>
          <div className="integration-brand-node">
            <AssistantMark assistant={assistants[1]} />
            <span>Claude</span>
          </div>
        </div>
        <span className="integration-announcement-art-caption">
          Your favorite AI. Your Relay workspace.
        </span>
      </div>
      <div className="integration-announcement-content">
        <h3>
          Your workflows.
          <br />
          <span>Just a conversation away.</span>
        </h3>
        <p className="integration-announcement-description">
          Bring Relay into ChatGPT and Claude. Run automations, check results,
          and manage your workflows — all from the conversation.
        </p>
        <div className="integration-announcement-features">
          <span>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m13 3-9 11h7l-1 7 10-12h-7l1-6Z" />
            </svg>
            Run workflows
          </span>
          <span>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 19V5m0 14h16M8 15l4-5 4 3 4-7" />
            </svg>
            Explore results
          </span>
          <span>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z" />
              <path d="m8 12 3 3 5-6" />
            </svg>
            You control access
          </span>
        </div>
        <div className="integration-announcement-actions">
          <button
            type="button"
            className="integration-announcement-primary"
            onClick={() => {
              dismiss();
              router.push("/integrations");
            }}
          >
            Explore Integrations
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 12h14m-6-6 6 6-6 6" />
            </svg>
          </button>
          <button
            type="button"
            className="integration-announcement-later"
            onClick={dismiss}
          >
            Maybe Later
          </button>
        </div>
        <p className="integration-announcement-footnote">
          Connect securely with your Relay account.
        </p>
      </div>
    </Modal>
  );
}
