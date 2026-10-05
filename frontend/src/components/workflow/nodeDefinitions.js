// Relay MVP Node Definitions Catalog

export const NODE_CATEGORIES = [
  {
    id: "triggers",
    name: "Triggers",
    nodes: [
      {
        typeId: "trigger.webhook",
        name: "Webhook",
        category: "Triggers",
        icon: "⚡",
        description: "Trigger workflow on incoming HTTP POST",
        defaultConfig: {
          method: "POST",
          path: "/hooks/webhook_1",
        },
      },
      {
        typeId: "trigger.schedule",
        name: "Scheduled",
        category: "Triggers",
        icon: "🕒",
        description: "Trigger on a recurring cron schedule",
        defaultConfig: {
          cron: "0 0 * * *",
          timezone: "UTC",
        },
      },
      {
        typeId: "trigger.manual",
        name: "Manual",
        category: "Triggers",
        icon: "▶",
        description: "Trigger manually via dashboard or API",
        defaultConfig: {
          description: "Triggered manually by user",
        },
      },
    ],
  },
  {
    id: "actions",
    name: "Actions",
    nodes: [
      {
        typeId: "action.http_request",
        name: "HTTP Request",
        category: "Actions",
        icon: "🌐",
        description: "Make an outbound HTTP API request",
        defaultConfig: {
          method: "POST",
          url: "",
          headers: "Content-Type: application/json",
          body: "{}",
        },
      },
      {
        typeId: "action.email",
        name: "Send Email",
        category: "Actions",
        icon: "✉",
        description: "Send an automated notification email",
        defaultConfig: {
          to: "user@example.com",
          subject: "Workflow Alert",
          body: "Your workflow step completed.",
        },
      },
      {
        typeId: "action.refund",
        name: "Refund Payment",
        category: "Actions",
        icon: "💳",
        description: "Process a payment refund",
        defaultConfig: {
          charge_id: "ch_12345",
          reason: "requested_by_customer",
        },
      },
    ],
  },
  {
    id: "ai",
    name: "AI",
    nodes: [
      {
        typeId: "ai.decision",
        name: "AI Decision",
        category: "AI",
        icon: "🧠",
        description: "Classify inputs or route logic using AI",
        defaultConfig: {
          prompt: "Classify incoming customer request priority",
          model: "gemini-2.5-flash",
        },
      },
      {
        typeId: "ai.rag_search",
        name: "RAG Search",
        category: "AI",
        icon: "🔍",
        description: "Search connected vector knowledge bases",
        defaultConfig: {
          knowledge_base: "kb_customer_docs",
          query: "{{input.message}}",
          top_k: 5,
        },
      },
      {
        typeId: "ai.generate",
        name: "AI Generate",
        category: "AI",
        icon: "✨",
        description: "Generate structured text response using AI",
        defaultConfig: {
          prompt: "Generate summary of customer ticket",
          model: "gemini-2.5-flash",
        },
      },
    ],
  },
  {
    id: "logic_human",
    name: "Logic & Human",
    nodes: [
      {
        typeId: "logic.condition",
        name: "Condition",
        category: "Logic",
        icon: "🔀",
        description: "Branch execution based on boolean condition",
        defaultConfig: {
          field: "status_code",
          operator: "equals",
          value: "200",
        },
      },
      {
        typeId: "human.approval",
        name: "Approval Gate",
        category: "Human",
        icon: "👤",
        description: "Pause workflow for human reviewer approval",
        defaultConfig: {
          approver: "admin@company.com",
          timeout_hours: 24,
          message: "Please approve refund request",
        },
      },
    ],
  },
];

export function getNodeDefinition(typeId) {
  for (const cat of NODE_CATEGORIES) {
    const found = cat.nodes.find((n) => n.typeId === typeId);
    if (found) return found;
  }
  return {
    typeId: typeId || "custom.node",
    name: typeId ? typeId.split(".").pop() : "Node",
    category: "Custom",
    icon: "⚙",
    description: "Workflow node",
    defaultConfig: {},
  };
}
