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
          headers: "",
          body: "",
        },
      },
      {
        typeId: "action.email",
        name: "Send Email",
        category: "Actions",
        icon: "✉",
        description: "Send an automated notification email",
        defaultConfig: {
          to: "",
          subject: "",
          body: "",
        },
      },
      {
        typeId: "action.refund",
        name: "Refund Payment",
        category: "Actions",
        icon: "💳",
        description: "Process a payment refund",
        defaultConfig: {
          connection_id: "",
          payment_id: "",
          amount: "",
          reason: "",
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
          prompt: "",
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
          knowledge_base: "",
          query: "",
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
          prompt: "",
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
          field: "",
          operator: "equals",
          value: "",
        },
      },
      {
        typeId: "human.approval",
        name: "Approval Gate",
        category: "Human",
        icon: "👤",
        description: "Pause the workflow until a human approves or rejects the request",
        defaultConfig: {
          approver_user_id: null,
          message: "",
          timeout_minutes: null,
        },
      },
    ],
  },
];

const exampleValuesByType = {
  "action.http_request": { headers: "Content-Type: application/json", body: "{}" },
  "action.email": {
    to: "user@example.com",
    subject: "Workflow Alert",
    body: "Your workflow step completed.",
  },
  "action.refund": { payment_id: "ch_12345" },
  "ai.decision": { prompt: "Classify incoming customer request priority" },
  "ai.rag_search": { knowledge_base: "kb_customer_docs", query: "{{input.message}}" },
  "ai.generate": { prompt: "Generate summary of customer ticket" },
  "logic.condition": { field: "status_code", value: "200" },
};

export function clearExampleNodeConfig(typeId, config) {
  const examples = exampleValuesByType[typeId];
  if (!config || typeof config !== "object") return config;

  let cleaned = config;

  // Older Refund Payment nodes used `charge_id`; normalize them to the
  // payment connector's input field so saving the node persists the new shape.
  if (typeId === "action.refund" && Object.hasOwn(config, "charge_id")) {
    cleaned = { ...config, payment_id: config.payment_id ?? config.charge_id };
    delete cleaned.charge_id;
  }

  if (!examples) return cleaned;
  for (const [key, example] of Object.entries(examples)) {
    if (cleaned[key] === example) {
      if (cleaned === config) cleaned = { ...config };
      cleaned[key] = "";
    }
  }
  return cleaned;
}

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
