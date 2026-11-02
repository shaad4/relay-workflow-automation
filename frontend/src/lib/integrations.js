// Public configuration only; never pass the environment object to a client.
export function mcpEndpoint(origin) {
  try {
    const url = new URL(origin);
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      url.pathname !== "/"
    )
      return null;
    return `${url.origin}/mcp`;
  } catch {
    return null;
  }
}

export const assistants = [
  {
    id: "chatgpt",
    name: "ChatGPT",
    description:
      "Access and execute your Relay workflows directly from ChatGPT.",
    url: "https://chatgpt.com/plugins",
    guide: "https://developers.openai.com/api/docs/guides/custom-mcp-server",
    steps: [
      "Plugins → Add → Add custom MCP server.",
      "Select OAuth for Authentication. Icon and description are optional.",
      "Sign in to Relay and review the permissions. Install the Relay plugin, then type @ in a new chat and select Relay to verify access.",
    ],
  },
  {
    id: "claude",
    name: "Claude",
    description:
      "Connect Relay to Claude and manage your automations through natural conversations.",
    url: "https://claude.ai/customize/connectors",
    guide:
      "https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp",
    steps: [
      "Customize → Connectors → Add → Add custom connector.",
      "Click Continue. For OAuth, choose Sign in now and Register automatically, then finish with Add.",
      "Sign in to Relay and review the permissions. In a new chat, open + → Connectors and enable Relay to verify access.",
    ],
  },
];
export const capabilities = [
  [
    "Discover workflows",
    "List workflows in your authorized workspace.",
    "relay:read",
  ],
  [
    "Run automations",
    "Execute published manual-trigger workflows with input data.",
    "relay:execute",
  ],
  [
    "Monitor executions",
    "List recent executions and their statuses.",
    "relay:read",
  ],
  ["Inspect results", "Read execution steps and outputs.", "relay:read"],
  [
    "Build workflows",
    "Create and edit drafts, add nodes and edges, and validate workflows.",
    "relay:write",
  ],
  [
    "Manage lifecycle",
    "Publish or deactivate with execute access; delete with separate delete access. Review changes before approval.",
    "relay:execute / relay:delete",
  ],
];
export const prompts = [
  "List all my Relay workflows.",
  "Run my Student Performance Report workflow with sample data after I review the inputs.",
  "Show my recent workflow executions.",
  "Show the steps and outputs for my latest workflow execution.",
];
export const announcementKey = (userId) =>
  `relay:mcp-announcement:v1:${userId}`;
