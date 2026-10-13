const required = (value) => String(value ?? "").trim().length > 0;
const containsExpression = (value) => /\{\{[^{}]+\}\}/.test(String(value ?? ""));

// Preserve conflicts until the user explicitly chooses a knowledge base.
export function ragKnowledgeBaseId(config = {}) {
  if (!config || typeof config !== "object") return undefined;
  return Object.hasOwn(config, "knowledge_base_id") ? config.knowledge_base_id : config.knowledge_base;
}

export function normalizeRAGConfiguration(config = {}) {
  if (!config || typeof config !== "object" || Array.isArray(config)) config = {};
  const normalized = { ...config, knowledge_base_id: ragKnowledgeBaseId(config) ?? "" };
  if (!Object.hasOwn(config, "knowledge_base_id") || !Object.hasOwn(config, "knowledge_base") || config.knowledge_base_id === config.knowledge_base) {
    delete normalized.knowledge_base;
  }
  delete normalized.workspace_id;
  return normalized;
}

export function validateNodeConfiguration(typeId, config = {}) {
  if (!config || typeof config !== "object" || Array.isArray(config)) config = {};
  const errors = [];
  const requireField = (field, label) => {
    if (!required(config[field])) errors.push({ field, message: `${label} is required.` });
  };

  switch (typeId) {
    case "trigger.webhook":
      if (!config.webhook_id) errors.push({ field: "webhook_id", message: "Set up a webhook endpoint before saving this trigger." });
      break;
    case "trigger.schedule":
      requireField("cron", "Cron expression");
      requireField("timezone", "Timezone");
      if (required(config.cron) && config.cron.trim().split(/\s+/).length !== 5) {
        errors.push({ field: "cron", message: "Cron expression must contain five fields: minute, hour, day, month, and weekday." });
      }
      if (required(config.timezone)) {
        try {
          new Intl.DateTimeFormat("en", { timeZone: config.timezone }).format();
        } catch {
          errors.push({ field: "timezone", message: "Enter a valid IANA timezone, such as UTC or America/New_York." });
        }
      }
      break;
    case "action.http_request":
      requireField("connection_id", "HTTP connection");
      requireField("method", "HTTP method");
      if (required(config.method) && !["GET", "POST", "PUT", "PATCH", "DELETE"].includes(config.method)) {
        errors.push({ field: "method", message: "Choose a supported HTTP method." });
      }
      requireField("url", "Request path");
      break;
    case "action.email":
      requireField("connection_id", "Gmail account");
      requireField("to", "Recipient email");
      if (required(config.to) && !containsExpression(config.to) && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(config.to.trim())) {
        errors.push({ field: "to", message: "Enter a valid recipient email address." });
      }
      requireField("subject", "Email subject");
      requireField("body", "Email body");
      break;
    case "action.refund":
      requireField("connection_id", "Payment connection");
      requireField("payment_id", "Payment ID");
      requireField("amount", "Refund amount");
      if (required(config.amount) && !containsExpression(config.amount)) {
        const amount = Number(config.amount);
        if (!Number.isFinite(amount) || amount <= 0) errors.push({ field: "amount", message: "Refund amount must be a positive number or a variable." });
      }
      break;
    case "ai.decision":
    case "ai.generate":
      requireField("prompt", "Prompt");
      requireField("model", "Model");
      break;
    case "ai.rag_search": {
      const kbId = ragKnowledgeBaseId(config);
      if (Object.hasOwn(config, "knowledge_base_id") && Object.hasOwn(config, "knowledge_base") && config.knowledge_base_id !== config.knowledge_base) {
        errors.push({ field: "knowledge_base_id", message: "Conflicting knowledge base IDs. Choose a knowledge base to resolve this." });
      } else if (typeof kbId !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(kbId)) {
        errors.push({ field: "knowledge_base_id", message: "Choose a knowledge base with a valid UUID." });
      }
      if (typeof config.query !== "string" || !config.query.trim()) errors.push({ field: "query", message: "Search query is required." });
      else if (config.query.length > 2000) errors.push({ field: "query", message: "Search query must be 2,000 characters or fewer." });
      if (!Number.isInteger(config.top_k) || config.top_k < 1 || config.top_k > 20) errors.push({ field: "top_k", message: "Top results must be a whole number from 1 to 20." });
      break;
    }
    case "logic.condition":
      requireField("field", "Field or variable");
      requireField("operator", "Operator");
      if (!["is_empty", "is_not_empty"].includes(config.operator)) requireField("value", "Comparison value");
      break;
    case "human.approval":
      requireField("approver_user_id", "Approver");
      requireField("message", "Approval message");
      if (config.timeout_minutes !== null && config.timeout_minutes !== undefined && config.timeout_minutes !== "" &&
        (!Number.isInteger(Number(config.timeout_minutes)) || Number(config.timeout_minutes) <= 0)) {
        errors.push({ field: "timeout_minutes", message: "Timeout must be a positive whole number of minutes." });
      }
      break;
    default:
      break;
  }

  return errors;
}

export function validateWorkflowConfiguration(nodes = [], edges = [], { includeStructure = true } = {}) {
  const errors = [];
  if (includeStructure) {
    const triggerNodes = nodes.filter((node) => node.data?.typeId?.startsWith("trigger."));
    if (triggerNodes.length === 0) {
      errors.push({ code: "NO_TRIGGER", message: "Workflow must have at least one Trigger node." });
    } else if (nodes.length > 1) {
      const reachable = new Set(triggerNodes.map((node) => node.id));
      const pending = [...reachable];
      while (pending.length) {
        const source = pending.pop();
        for (const edge of edges) {
          if (edge.source === source && !reachable.has(edge.target)) {
            reachable.add(edge.target);
            pending.push(edge.target);
          }
        }
      }
      if (reachable.size !== nodes.length) {
        const disconnected = nodes.filter((node) => !reachable.has(node.id));
        errors.push({
          code: "DISCONNECTED_NODES",
          message: `Connect every node to a trigger before saving or publishing: ${disconnected.map((node) => node.data?.label || node.data?.nodeId || node.id).join(", ")}.`,
        });
      }
    }
  }

  for (const node of nodes) {
    const typeId = node.data?.typeId ?? "custom";
    const label = node.data?.label || typeId;
    for (const error of validateNodeConfiguration(typeId, node.data?.config)) {
      errors.push({
        field: error.field,
        code: `NODE_CONFIG_${error.field.toUpperCase()}`,
        nodeId: node.data?.nodeId ?? node.id,
        message: `${label}: ${error.message}`,
      });
    }
  }
  return errors;
}
