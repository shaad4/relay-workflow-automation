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
        name: "Scheduled Trigger",
        category: "Triggers",
        icon: "🕒",
        description: "Automatically run this workflow at scheduled times.",
        defaultConfig: {
          schedule_type: "interval",
          interval_minutes: 30,
          cron_expression: null,
          timezone: "Asia/Kolkata",
          enabled: true,
        },
      },
      {
        typeId: "trigger.manual",
        name: "Manual Trigger",
        category: "Triggers",
        icon: "▶",
        description: "Start this workflow manually with custom input data.",
        defaultConfig: {
          description: "",
          input_schema: { type: "object" },
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
          timeout: 10,
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
          body_format: "plain",
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
        description: "Classify structured inputs into defined decisions",
        defaultConfig: {
          connection_id: "",
          model: "",
          instructions: "",
          input_mappings: {},
          rag_context: "",
          allowed_decisions: [],
        },
      },
      {
        typeId: "ai.rag_search",
        name: "RAG Search",
        category: "AI",
        icon: "🔍",
        description: "Search connected vector knowledge bases",
        defaultConfig: {
          knowledge_base_id: "",
          query: "",
          top_k: 5,
        },
      },
      {
        typeId: "ai.generate",
        name: "AI Generate",
        category: "AI",
        icon: "✨",
        description: "Generate text with a connected AI provider",
        defaultConfig: {
          connection_id: "",
          model: "",
          instructions: "",
          prompt: "",
          rag_context: "",
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
        description: "Route to the branch matching an evaluated value",
        defaultConfig: { value: "" },
      },
      {
        typeId: "human.approval",
        name: "Approval Gate",
        category: "Human",
        icon: "👤",
        description:
          "Pause the workflow until a human approves or rejects the request",
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
  "action.http_request": {
    headers: "Content-Type: application/json",
    body: "{}",
  },
  "action.email": {
    to: "user@example.com",
    subject: "Workflow Alert",
    body: "Your workflow step completed.",
  },
  "action.refund": { payment_id: "ch_12345" },
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
