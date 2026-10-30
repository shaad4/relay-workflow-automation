import PolicyPage, { privacyContact } from "@/components/legal/PolicyPage";

export const metadata = {
  title: "Privacy Policy",
  description:
    "How Relay handles account, workflow, Gmail connection, AI, and knowledge-base data, and the controls available to you.",
  alternates: { canonical: "https://relay.shaad.site/privacy" },
};

const sections = [
  {
    id: "scope",
    title: "About this policy",
    content: (
      <p>
        This policy explains how Relay handles personal information when you use
        our AI workflow automation service at{" "}
        <a href="https://relay.shaad.site">relay.shaad.site</a>. For privacy
        questions or requests, contact {privacyContact}.
      </p>
    ),
  },
  {
    id: "accounts",
    title: "Accounts and authentication",
    content: (
      <>
        <p>
          When you register, we collect your name, email address, and
          authentication information. Password-based accounts store a password
          hash. Google sign-in uses your Google account identifier, email
          address, and profile information to authenticate and maintain your
          Relay account. Signing in with Google is separate from authorizing
          Gmail sending.
        </p>
        <p>
          Relay uses session cookies to keep you signed in and browser storage
          for preferences such as your theme. Authentication records support
          email verification, password recovery, and session management.
          Information you send in support requests is used to respond to you.
        </p>
      </>
    ),
  },
  {
    id: "workflows",
    title: "Workspaces and execution data",
    content: (
      <>
        <p>
          We store workspace details, membership information, workflow
          definitions, triggers, schedules, settings, and connection references
          so you can build and operate automations. Workspace data is available
          through the service to members with the relevant access.
        </p>
        <p>
          Workflow execution records can include inputs, outputs, status,
          timestamps, errors, and step history. Depending on your configuration,
          these records may contain personal information, email recipients and
          message content, AI prompts and responses, or data returned by
          external services. We use these records to run workflows, display
          history, investigate failures, and support the service. Only include
          information you are authorized to process.
        </p>
      </>
    ),
  },
  {
    id: "connections",
    title: "Connected accounts and credentials",
    content: (
      <p>
        When you connect a third-party service, Relay stores connection details
        and the credentials needed to carry out your configured actions, such as
        API keys or OAuth refresh tokens. The Gmail connection stores your
        Google email address and an encrypted refresh token. It obtains access
        tokens from Google when needed to send messages. Connections belong to a
        workspace and may be used by workflows in that workspace; connect only
        accounts you are authorized to make available for that purpose.
      </p>
    ),
  },
  {
    id: "gmail",
    title: "Gmail permissions and use",
    content: (
      <>
        <p>
          Relay requests <code>https://www.googleapis.com/auth/gmail.send</code>{" "}
          to send email on your behalf, together with OpenID and email identity
          permissions to identify the connected account. Gmail access is used
          exclusively for user-authorized email sending, including automatic
          runs of workflows you configure and enable.
        </p>
        <p>
          Relay sends the recipient address, subject, and message body supplied
          by your workflow to the Gmail API. Google returns delivery request
          metadata, such as message and thread identifiers, which may appear in
          execution results. Relay does not read Gmail messages, retrieve inbox
          contents, or request inbox-reading permission.
        </p>
        <p>
          You control whether to connect Gmail, which workflows use it, and what
          those workflows send. Review recipients, content, and triggers before
          enabling automation. You can stop using the connection, disconnect it
          in Relay, or revoke access through Google as described below.
        </p>
      </>
    ),
  },
  {
    id: "google-data",
    title: "Google user data and Limited Use",
    content: (
      <>
        <p>
          Relay’s use of information received from Google APIs is subject to the{" "}
          <a href="https://developers.google.com/terms/api-services-user-data-policy">
            Google API Services User Data Policy
          </a>
          , including its Limited Use requirements.
        </p>
        <p>
          Google user data is used to provide the user-facing authentication and
          email-sending features you authorize. It is not sold, used for
          advertising, or used to train general-purpose AI models. Transfers are
          limited to providing these features, security purposes, applicable
          legal requirements, or a business transfer with user consent where
          required by that policy.
        </p>
        <p>
          Human access to Google user data is limited to your affirmative
          consent for specific data, necessary security investigations, legal
          obligations, or aggregated and anonymized internal operations
          permitted by Google’s policy. These restrictions also apply to data
          derived from Google user data.
        </p>
      </>
    ),
  },
  {
    id: "ai",
    title: "AI providers and external APIs",
    content: (
      <>
        <p>
          When you configure an AI step, Relay sends the prompts, inputs, and
          selected context needed for that step to the AI provider you select.
          Other action steps send the configured data to the connected service
          or API endpoint. Responses may be stored in workflow execution history
          and passed to later steps.
        </p>
        <p>
          Those providers process information under their own terms and privacy
          policies. Review their data handling and your provider account
          settings before sending sensitive information. Relay’s Gmail
          integration does not fetch inbox messages for AI processing. Email
          content that you supply or generate through an AI workflow is
          processed according to that workflow’s configuration.
        </p>
      </>
    ),
  },
  {
    id: "knowledge",
    title: "Knowledge bases and documents",
    content: (
      <>
        <p>
          When you upload knowledge-base documents, Relay stores the files and
          document metadata, extracts text, divides it into chunks, and stores
          text and numerical embeddings for retrieval-augmented generation
          (RAG). Document storage uses Supabase Storage. Relay sends document
          text and retrieval queries to OpenAI to generate embeddings; this
          processing is separate from the AI provider selected for a workflow.
        </p>
        <p>
          Relevant retrieved passages may be sent to your selected AI provider
          as context and included in workflow results. Upload only documents you
          have permission to use and share with these services. Use the
          available document and knowledge-base deletion controls to remove
          content you no longer need.
        </p>
      </>
    ),
  },
  {
    id: "security",
    title: "Storage, sharing, and security",
    content: (
      <>
        <p>
          Relay stores account, workspace, configuration, and execution records
          in service databases and uploaded files in object storage.
          Infrastructure and service providers process data as needed to host
          the service, authenticate users, process documents, and execute the
          actions you request. Data may be processed in locations where these
          providers operate.
        </p>
        <p>
          The application uses password hashing, authentication checks,
          workspace-scoped access checks, and encryption of stored Gmail refresh
          tokens. These measures reduce risk but do not guarantee that data will
          never be accessed, lost, or disclosed without authorization. Keep
          account access and API credentials secure.
        </p>
        <p>
          Information may also be disclosed when necessary to comply with
          applicable legal obligations, address abuse, or protect users and the
          service, subject to the Google user data restrictions above.
        </p>
      </>
    ),
  },
  {
    id: "retention",
    title: "Retention, deletion, and disconnection",
    content: (
      <>
        <p>
          Account, workflow, and execution data can remain stored while used to
          provide the service and its history features. Retention depends on the
          data involved, operational needs, and applicable legal obligations.
          This policy does not promise a fixed retention period or immediate
          removal from every system or backup.
        </p>
        <p>
          Disconnect Gmail from the Connections screen to delete the saved Relay
          connection and its stored credential. This does not itself revoke the
          authorization at Google. To revoke that authorization, remove Relay
          from your{" "}
          <a href="https://myaccount.google.com/connections">
            Google Account connections
          </a>
          . Disconnection does not recall emails already sent, delete
          recipients’ copies, or automatically remove past workflow execution
          records.
        </p>
        <p>
          For account deletion or removal of associated personal information,
          email {privacyContact}. We may need to verify your identity and
          clarify the scope of your request, including shared workspace records.
          Records subject to legal or legitimate security needs and data held
          independently by third-party providers may require separate handling.
        </p>
      </>
    ),
  },
  {
    id: "rights",
    title: "Your choices and rights",
    content: (
      <p>
        Depending on applicable law, you may have rights to access, correct,
        delete, or obtain a copy of personal information, object to or restrict
        processing, withdraw consent, or raise a concern with a privacy
        authority. Contact {privacyContact} to make a request or ask about
        available controls. Withdrawing access to a connected service may
        prevent workflows that depend on it from running.
      </p>
    ),
  },
  {
    id: "updates",
    title: "Policy updates and contact",
    content: (
      <p>
        We may update this policy as Relay changes. The date above identifies
        the latest revision. Material changes to Google data use require
        appropriate notice and renewed consent before data is used for a new
        purpose. For questions about this policy, contact {privacyContact}. Our{" "}
        <a href="/terms">Terms of Service</a> describe the conditions for using
        Relay.
      </p>
    ),
  },
];

export default function PrivacyPage() {
  return (
    <PolicyPage
      title="Privacy Policy"
      introduction="Your workflows connect information across tools. This policy explains what Relay processes, why it is needed, and how you can control it."
      sections={sections}
    />
  );
}
