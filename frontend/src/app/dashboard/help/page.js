"use client";

import Link from "next/link";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";

const sections = [
  {
    id: "getting-started", title: "Getting started", href: "/workflows", link: "Open workflows",
    introduction: "Relay connects triggers, actions, AI, and human decisions into workflows. A workflow describes the process; an execution is one run of that process. Your workspace contains its workflows, connections, knowledge bases, and execution history.",
    topics: [
      ["Build your first workflow", "Create a workflow and give it a recognizable name and description. Start with a Manual Trigger and one simple action. Select each node to configure it, then connect the nodes in the order they should run."],
      ["Prepare your dependencies", "Add any required service or AI connection before configuring the action that uses it. For document-based answers, create a knowledge base, upload documents, and wait for them to become Ready."],
      ["Save, publish, and run", "Save your draft, review validation messages, and fix missing settings or connections. Publish the version you want to run. Use Run with a manual trigger, send an event to a webhook, or enable a schedule. Inspect the resulting execution before adding more steps."],
      ["A useful first example", "Create Manual Trigger → HTTP Request. Use an endpoint you control and provide a small JSON input such as an order ID. Configure the HTTP request, publish, run, and expand both steps in Execution History to compare the input with the response."],
    ],
  },
  {
    id: "dashboard", title: "Dashboard and activity", href: "/dashboard", link: "Open dashboard",
    introduction: "The overview summarizes workflow activity and provides shortcuts to requests and failures that need attention.",
    topics: [
      ["Choose a reporting period", "Use the range selector to view activity for the available time periods. Execution charts count runs created in that period. Their time buckets use UTC; the current bucket is incomplete and can keep changing."],
      ["Read the metrics", "Active Workflows shows enabled workflows. Total Executions counts runs created in the selected period. Success Rate compares completed runs with completed plus failed runs; waiting and running executions are not successful completions."],
      ["Follow up on attention items", "Open pending approvals, failed executions, or dead-letter events to investigate. These are separate categories and may overlap. Pending approval and dead-letter backlogs can include older items outside the reporting period."],
      ["Inspect the charts", "Hover over activity points for values and use the available data view for exact counts. Open a recent execution to inspect its timeline and errors rather than relying only on aggregate totals."],
    ],
  },
  {
    id: "builder", title: "Workflow builder and versions", href: "/workflows", link: "Manage workflows",
    introduction: "The workflow list supports searching and status filtering. Open a workflow to edit its graph, configure nodes, and manage versions.",
    topics: [
      ["Arrange and connect steps", "Choose nodes from the library, select a node to open its inspector, and fill in the required settings. Connect output handles to the next node. A node’s position on the canvas does not determine execution order; its connections do."],
      ["Map data between steps", "Use the variable picker in supported fields to insert trigger data or outputs from earlier connected nodes. For example, {{trigger.data.order_id}} reads an order ID supplied to a manual trigger. Check the actual output in an execution before choosing a nested field. A missing field is not the same as an empty value."],
      ["Save and validate", "Watch the save indicator and use Save or Retry if needed. Review validation before publishing. Undo and redo help correct canvas edits; they do not reverse actions already performed by an execution."],
      ["Understand versions", "A draft is editable; published versions represent saved workflow definitions. Use the version selector to inspect the desired version. Publishing selects the definition for new runs. Verify which version is published after editing; saving a draft alone does not publish it."],
      ["Activate, deactivate, and delete", "Activation controls whether the workflow can run. Deactivation applies to the whole workflow, not only the version being viewed. Deletion is available for eligible draft or inactive workflows. Read the confirmation before deleting a version: deleting the live version leaves the workflow inactive until another version is explicitly published."],
    ],
  },
  {
    id: "triggers", title: "Manual, webhook, and scheduled triggers",
    introduction: "A trigger defines how a run starts and which data enters the workflow. Choose the trigger that matches the source of your event.",
    topics: [
      ["Manual Trigger", "Use this for on-demand runs and controlled checks. Configure the input schema if your workflow needs structured input. Publish, choose Run, and supply valid JSON matching the expected fields. Downstream steps can reference those fields through the variable picker."],
      ["Webhook Trigger", "Configure the webhook endpoint and connect it to the intended workflow. Keep the endpoint active. Send an HTTP POST with a JSON body and Content-Type: application/json. If secret authentication is enabled, include X-Relay-Secret with the saved secret. Copy the endpoint from Relay instead of constructing it yourself."],
      ["Test a webhook", "Use the webhook’s Test environment to obtain a temporary test URL. Send a request before the session expires and inspect the captured payload. Use that payload to configure variables. A temporary test URL is separate from the endpoint used for ongoing events."],
      ["Scheduled Trigger", "Choose an interval or configure a cron expression, then select the intended time zone. Confirm that the schedule is enabled and the correct workflow version is published and active. Check Execution History after a scheduled time to verify the run and its inputs."],
    ],
  },
  {
    id: "actions", title: "HTTP, email, and payment actions",
    introduction: "Actions perform work in connected systems. Configure each action with the correct connection and map its input from the trigger or an earlier step.",
    topics: [
      ["HTTP Request", "Choose the HTTP method, destination URL, headers, body, and timeout. Select the appropriate API connection when required. Use valid JSON when the destination expects JSON. Inspect status_code, body, headers, and success in the step output to understand the response."],
      ["Send Email", "Connect a Gmail account, then configure the recipient, subject, body, and body format. Insert variables for personalized content. Confirm recipient values before running. The output can include the message ID, thread ID, labels, and success status."],
      ["Refund Payment", "Configure a Stripe connection, select it on the refund node, and provide the payment ID, amount, and reason. Use the payment identifier expected by the connection and confirm the amount format before running. Inspect the returned refund ID, payment ID, amount, and status. A replay may contact the payment service again, so check the existing payment and refund before retrying."],
      ["Handle external errors", "Authentication errors usually require checking the connection. Invalid-input responses require correcting the request or mappings. A timeout may leave the external outcome uncertain; inspect the external system before repeating a write such as an email, order update, or refund."],
    ],
  },
  {
    id: "ai", title: "AI generation, decisions, and retrieval",
    introduction: "AI nodes use configured providers and models. Retrieval adds relevant document context; decision nodes turn structured input into one of your allowed outcomes.",
    topics: [
      ["AI Generate", "Select an AI connection and model. Write instructions describing the desired output and a prompt containing the input to process. Map retrieved context into the RAG context field when needed. The output includes generated content and may include model and token usage information."],
      ["AI Decision", "Select a connection and model, write clear decision rules, map the input fields, and define the allowed decisions. For example, use APPROVE, REJECT, and HUMAN_REVIEW. Inspect the decision and reason outputs. Connect a Condition node to route the result to the appropriate next step."],
      ["RAG Search", "Select a knowledge base, provide a search query, and choose the number of results with top_k. Use a specific query based on the incoming request. The output exposes matching chunks and context, which can be passed into AI Generate or AI Decision."],
      ["Improve the result", "First inspect the incoming data and retrieved chunks. If retrieval is empty, check the selected knowledge base and document readiness. If an AI response is unsuitable, refine the instructions, allowed decisions, or context. Use an Approval Gate when a person should review the proposed action."],
    ],
  },
  {
    id: "branches", title: "Conditions and human approval", href: "/approvals", link: "Open approval inbox",
    introduction: "Conditions route work automatically. Approval Gates pause a run until the assigned person makes a decision.",
    topics: [
      ["Configure a Condition", "Set the value to evaluate, often an AI decision or a prior step’s output. Configure the outgoing branches to match the possible values. Connect each intended outcome to its next step and review validation before publishing. Check capitalization and spelling when matching text values."],
      ["Configure an Approval Gate", "Choose the approver and write a message that gives them enough context to decide. Include relevant values through variables, such as the order, amount, and reason. Configure a timeout if appropriate. Connect the approval and rejection paths to their intended actions."],
      ["Review an inbox request", "Open Approvals, read the pending request, and use View request to inspect the linked run. Choose Approve or Reject once you understand the consequences. Rejection follows the configured rejection path; it does not necessarily mean the entire workflow should fail."],
      ["Understand stale and cancelled requests", "A request may change while it is open. Refresh if another decision or cancellation has already occurred. Cancelled requests are historical records, not pending decisions. If the service says the execution is not waiting for approval, inspect its current status before trying again."],
    ],
  },
  {
    id: "executions", title: "Execution history and cancellation", href: "/dashboard/executions", link: "Open execution history",
    introduction: "Use execution details to understand what actually ran, which version it used, and where work succeeded, paused, or failed.",
    topics: [
      ["Find the run", "Open Execution History and use the available filters to narrow the list. Select an execution to view its trigger, workflow and version IDs, timestamps, overall status, and recorded steps. Keep the execution ID when reporting a problem."],
      ["Read the timeline", "Expand a step to inspect its inputs, outputs, timing, and error details. Check earlier outputs when a later step receives an unexpected value. The count of completed steps describes recorded steps; it is not a substitute for the overall execution status."],
      ["Understand status", "Queued runs are waiting to start; running runs are being processed; waiting approvals need a human decision. Completed, failed, and cancelled runs are terminal outcomes. Live refresh is useful while a run is active; use Refresh to request the latest state."],
      ["Cancel an active run", "Use Cancel when the execution is still eligible and confirm the action. Cancellation stops further processing where possible; it does not undo work already completed in an external system. Finished executions do not need a cancellation action."],
      ["Investigate a stuck run", "Refresh and compare the overall state with the step timeline. If steps are finished but the run remains active, preserve the execution ID, version ID, timestamps, and error details. A worker-interrupted or lease-expired error indicates a processing interruption, even when some actions have completed."],
    ],
  },
  {
    id: "recovery", title: "Failures, replay, and dead-letter events", href: "/dashboard/executions/dead-letter", link: "Open dead-letter queue",
    introduction: "Recovery starts with understanding the original failure. A new attempt should address its cause and account for actions that may already have happened.",
    topics: [
      ["Inspect before retrying", "Read the execution error and failed step output. Check credentials, input mappings, service responses, and the selected workflow version. Correct the relevant configuration before starting another attempt."],
      ["Review dead-letter items", "Open the Dead-Letter Queue to inspect events that could not be processed successfully. Review their failure information and linked execution when available. Use the recovery controls offered for that item; available actions depend on its current state."],
      ["Follow replay history", "When replay is available, review the chosen source and confirm the action. Open the resulting attempt and follow replay history to compare it with the original. A replay is a separate attempt and does not erase the original failure."],
      ["Avoid repeating side effects", "Before replaying, check whether an external request succeeded despite a timeout or worker interruption. In particular, confirm emails, payments, and refunds in the connected service. Keep the original and new execution IDs together when investigating repeated failures."],
    ],
  },
  {
    id: "connections", title: "Service and AI connections", href: "/connections", link: "Open connections",
    introduction: "Connections store the configuration needed to access services. Create them once, then select them in the nodes that need them.",
    topics: [
      ["HTTP APIs", "Choose Add connection and configure an HTTP API. Enter a recognizable name, base URL, and authentication method: no authentication, bearer token, API key in a header, or API key in a query parameter. Provide the header or parameter name required by that service."],
      ["Test and inspect", "Add a test URL when appropriate and use Test connection. Inspect the result and response payload. A successful connection check verifies that request; it does not guarantee that every workflow action has the right URL, permissions, or body."],
      ["Gmail and Stripe", "Use Gmail’s connection flow to authorize the account that will send email. Use Stripe’s configuration flow for payment actions. Confirm the intended account and environment before assigning a connection to a workflow."],
      ["AI providers", "Open the AI providers tab and configure a supported provider using the credentials and settings requested by its form. Select that connection and an available model in AI nodes. If a model call fails, check provider access, credentials, limits, and the node’s configuration."],
      ["Maintain connections", "Use the connection menu to view configuration, edit supported settings, test, or disconnect. Stored credentials are not shown in the configuration view. Before removing a connection, check workflows that depend on it and select a replacement where needed."],
    ],
  },
  {
    id: "knowledge", title: "Knowledge bases and documents", href: "/dashboard/knowledge-bases", link: "Open knowledge bases",
    introduction: "A knowledge base groups source documents that RAG Search can retrieve. Keep each library focused on a topic so workflows can choose the right source.",
    topics: [
      ["Create a library", "Choose Create Knowledge Base, enter a clear name, and add a description of its contents. Open the library to manage documents. Use names such as Product Documentation or Refund Policies so node configuration remains easy to understand."],
      ["Upload documents", "Browse or drag files into the upload area. Supported formats are PDF, TXT, and Markdown (.md). Select up to five files per batch; each must be non-empty and no larger than 10 MiB. Review the selected files and start the upload."],
      ["Wait for readiness", "Uploading is followed by queued processing, text extraction, chunk preparation, and embedding generation. Wait for Ready before relying on a document in retrieval. Uploaded does not necessarily mean searchable yet."],
      ["Handle failed processing", "Inspect the document’s failure information and use retry when available. Check the document list before uploading again after an uncertain upload response: the original may already be saved. For a poor search result, check document content as well as its status."],
      ["Use and remove content", "Select this library in a RAG Search node, map a query, then pass the returned context into an AI node. Delete obsolete documents when they should no longer be used. Deleting a knowledge base removes associated database document and chunk records; physical external files are not confirmed to be deleted."],
    ],
  },
  {
    id: "preferences", title: "Navigation, appearance, and account",
    introduction: "Relay’s workspace navigation stays available across the application. The header’s How to use link returns to this guide.",
    topics: [
      ["Move around the workspace", "Use the sidebar to open Dashboard, Workflows, Execution History, Dead-Letter Queue, Approvals, Connections, or Knowledge Bases. Collapse the sidebar for more canvas space. On smaller screens, use the navigation menu button."],
      ["Change appearance", "Open the profile menu from your avatar and choose Light, Dark, or System. System follows your device preference. The theme applies throughout the workspace."],
      ["Sign out", "Use Log out in the profile menu when you are finished. Save pending workflow edits first and confirm the saved indicator before leaving the builder."],
    ],
  },
];

export default function HelpPage() {
  return (
    <ProtectedRoute>
      <DashboardShell pageTitle="How to use Relay">
        <div className="execution-workspace">
          <header className="execution-page-header">
            <div>
              <p className="execution-eyebrow">Relay guide</p>
              <h1>How to use Relay</h1>
              <p className="execution-header-description">From your first workflow to approvals, AI, and execution recovery.</p>
            </div>
          </header>
          <div className="grid items-start gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
            <nav aria-label="Guide contents" className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] p-4 lg:sticky lg:top-20">
              <h2 className="mb-3 text-[13px] font-semibold">In this guide</h2>
              <ol className="space-y-1">
                {sections.map((section, index) => (
                  <li key={section.id}>
                    <a href={`#${section.id}`} className="flex gap-2 rounded-md px-2 py-2 text-[12px] leading-5 text-[var(--text-secondary)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-[var(--accent)]">
                      <span className="font-mono text-[var(--text-tertiary)]">{String(index + 1).padStart(2, "0")}</span>
                      {section.title}
                    </a>
                  </li>
                ))}
              </ol>
            </nav>
            <div className="min-w-0 space-y-5">
              {sections.map((section, index) => (
                <section key={section.id} id={section.id} aria-labelledby={`${section.id}-title`} className="scroll-mt-20 rounded-[10px] border border-[var(--border-subtle)] bg-[var(--surface)] p-5 sm:p-6">
                  <p className="mb-2 font-mono text-[11px] text-[var(--text-tertiary)]">{String(index + 1).padStart(2, "0")}</p>
                  <h2 id={`${section.id}-title`} className="text-xl font-semibold tracking-tight">{section.title}</h2>
                  <p className="mt-3 max-w-4xl text-[14px] leading-7 text-[var(--text-secondary)]">{section.introduction}</p>
                  <div className="mt-5 space-y-5 border-t border-[var(--border-subtle)] pt-5">
                    {section.topics.map(([title, description]) => (
                      <div key={title}>
                        <h3 className="text-[14px] font-semibold">{title}</h3>
                        <p className="mt-1 max-w-4xl break-words text-[13px] leading-6 text-[var(--text-secondary)]">{description}</p>
                      </div>
                    ))}
                  </div>
                  {section.href && <Link href={section.href} className="mt-5 inline-flex rounded-md border border-[var(--border-default)] px-3 py-2 text-[12px] font-medium hover:bg-[var(--elevated)] focus-visible:outline-2 focus-visible:outline-[var(--accent)]">{section.link} <span aria-hidden="true" className="ml-2">→</span></Link>}
                </section>
              ))}
            </div>
          </div>
        </div>
      </DashboardShell>
    </ProtectedRoute>
  );
}
