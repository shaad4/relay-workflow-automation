import Link from "next/link";

export default function PolicyLinks() {
  return (
    <span className="inline-flex flex-wrap justify-center gap-x-4 gap-y-2 text-xs">
      <Link
        className="underline underline-offset-4 hover:text-[var(--text-primary)]"
        href="/privacy"
      >
        Privacy Policy
      </Link>
      <Link
        className="underline underline-offset-4 hover:text-[var(--text-primary)]"
        href="/terms"
      >
        Terms of Service
      </Link>
    </span>
  );
}

export function GmailDisclosure() {
  return (
    <div className="space-y-2 text-xs leading-5 text-[var(--text-secondary)]">
      <p>
        Relay requests Gmail send permission (gmail.send) to send email through
        workflows you authorize, plus your Google account identity and email
        address to identify the connection. Relay does not read your messages or
        inbox.
      </p>
      <p>
        Disconnect in Connections to remove the saved connection. You can also
        revoke Relay’s access in your Google Account settings.
      </p>
      <PolicyLinks />
    </div>
  );
}
