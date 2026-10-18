import { validateSchedule } from "./scheduleTrigger.js";
import { previousNodesFor } from "./workflowVariables.js";
import { branchOptions } from "./branchOptions.js";

export const AI_DECISION_FIELDS = ["connection_id", "model", "instructions", "input_mappings", "rag_context", "allowed_decisions"];
export const AI_GENERATE_FIELDS = ["connection_id", "model", "instructions", "prompt", "rag_context"];
export function normalizeDecisionConfiguration(config = {}) {
  return { ...config, ...(Array.isArray(config.allowed_decisions) ? {
    allowed_decisions: config.allowed_decisions.map((value) => typeof value === "string" ? value.trim().toUpperCase() : value),
  } : {}) };
}
export function upgradeDecisionConfiguration(config = {}) {
  return {
    connection_id: "", model: "", input_mappings: {}, rag_context: "", allowed_decisions: [],
    ...Object.fromEntries(Object.entries(config).filter(([key]) => AI_DECISION_FIELDS.includes(key))),
    instructions: config.instructions || config.prompt || "",
  };
}
const required = (value) => String(value ?? "").trim().length > 0;
const containsExpression = (value) => /\{\{[^{}]+\}\}/.test(String(value ?? ""));

export function isLegacyConditionConfiguration(config = {}) {
  return !!config && typeof config === "object" && !Array.isArray(config) &&
    Object.keys(config).some((key) => key !== "value");
}

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
    case "trigger.manual":
      if (config.description !== undefined && (typeof config.description !== "string" || config.description.length > 500)) errors.push({ field: "description", message: "Description must be 500 characters or fewer." });
      if (config.input_schema !== undefined && (config.input_schema?.type !== "object" || Object.keys(config.input_schema).length !== 1)) errors.push({ field: "input_schema", message: "Input type must be JSON Object." });
      break;
    case "trigger.webhook":
      if (!config.webhook_id) errors.push({ field: "webhook_id", message: "Set up a webhook endpoint before saving this trigger." });
      break;
    case "trigger.schedule":
      errors.push(...validateSchedule(config));
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
    case "ai.decision": {
      if (typeof config.connection_id !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(config.connection_id)) errors.push({ field: "connection_id", message: "Choose an active AI provider connection." });
      for (const [field, label, max] of [["model", "Model", 150], ["instructions", "AI instructions", 10000]]) {
        if (typeof config[field] !== "string" || !config[field].trim()) errors.push({ field, message: `${label} is required.` });
        else if (config[field].length > max) errors.push({ field, message: `${label} must be ${max.toLocaleString("en-US")} characters or fewer.` });
      }
      if (config.rag_context !== undefined && (typeof config.rag_context !== "string" || config.rag_context.length > 2000)) errors.push({ field: "rag_context", message: "RAG context must be text with at most 2,000 characters." });
      if (config.input_mappings !== undefined && (!config.input_mappings || typeof config.input_mappings !== "object" || Array.isArray(config.input_mappings))) errors.push({ field: "input_mappings", message: "Input mappings must be an object." });
      else if (Object.keys(config.input_mappings || {}).some((key) => !key.trim())) errors.push({ field: "input_mappings", message: "Input mapping names cannot be empty." });
      const decisions = config.allowed_decisions;
      if (!Array.isArray(decisions) || decisions.length < 2 || decisions.length > 20) errors.push({ field: "allowed_decisions", message: "Add between 2 and 20 allowed decisions." });
      if (Array.isArray(decisions)) {
        const normalized = decisions.map((value) => typeof value === "string" ? value.trim().toUpperCase() : "");
        if (normalized.some((value) => !/^[A-Z][A-Z0-9_]*$/.test(value) || value.length > 100)) errors.push({ field: "allowed_decisions", message: "Use up to 100 letters, numbers, or underscores per decision, starting with a letter." });
        if (new Set(normalized).size !== normalized.length) errors.push({ field: "allowed_decisions", message: "Allowed decisions must be unique (case insensitive)." });
      }
      const unsupported = Object.keys(config).filter((field) => !AI_DECISION_FIELDS.includes(field));
      if (unsupported.length) errors.push({ field: "legacy", message: `Review and upgrade legacy AI settings before saving: ${unsupported.join(", ")}.` });
      break;
    }
    case "ai.generate": {
      if (typeof config.connection_id !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(config.connection_id)) errors.push({ field: "connection_id", message: "Choose an active AI provider connection." });
      for (const [field, label, max] of [["model", "Model", 150], ["prompt", "Prompt", 10000]]) {
        if (typeof config[field] !== "string" || !config[field].trim()) errors.push({ field, message: `${label} is required.` });
        else if (config[field].length > max) errors.push({ field, message: `${label} must be ${max.toLocaleString("en-US")} characters or fewer.` });
      }
      for (const [field, label, max] of [["instructions", "Instructions", 10000], ["rag_context", "RAG context", 2000]]) {
        if (config[field] !== undefined && (typeof config[field] !== "string" || config[field].length > max)) errors.push({ field, message: `${label} must be text with at most ${max.toLocaleString("en-US")} characters.` });
      }
      const unsupported = Object.keys(config).filter((field) => !AI_GENERATE_FIELDS.includes(field));
      if (unsupported.length) errors.push({ field: "legacy", message: `Unsupported AI Generate fields: ${unsupported.join(", ")}. Review this configuration before publishing.` });
      break;
    }
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
      if (isLegacyConditionConfiguration(config)) errors.push({ field: "legacy", message: "This Condition uses older comparison settings. Update it to exact-value routing before publishing." });
      if (typeof config.value !== "string" || !config.value.trim()) errors.push({ field: "value", message: "Value to Evaluate is required." });
      else if (config.value.length > 2000) errors.push({ field: "value", message: "Value to Evaluate must be 2,000 characters or fewer." });
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
    } else if (triggerNodes.length > 1) {
      errors.push({ code: "MULTIPLE_TRIGGERS", message: "Workflow must have exactly one Trigger node." });
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
    const nodeErrors = validateNodeConfiguration(typeId, node.data?.config);
    if (typeId === "ai.decision") nodeErrors.push(...validateDecisionReferences(node.data?.config, nodes, edges, node.id));
    if (typeId === "ai.generate") nodeErrors.push(...validateGenerateReferences(node.data?.config, nodes, edges, node.id));
    if (typeId === "logic.condition") nodeErrors.push(...validateConditionReferences(node.data?.config, nodes, edges, node.id));
    for (const error of nodeErrors) {
      errors.push({
        field: error.field,
        code: `NODE_CONFIG_${error.field.toUpperCase()}`,
        nodeId: node.data?.nodeId ?? node.id,
        message: `${label}: ${error.message}`,
      });
    }
  }
  errors.push(...validateConditionBranches(nodes, edges));
  return errors;
}

export function validateConditionReferences(config = {}, nodes = [], edges = [], currentNodeId) {
  return validateDecisionReferences({ input_mappings: { value: config?.value } }, nodes, edges, currentNodeId)
    .map((error) => ({ ...error, field: "value" }));
}

export function validateGenerateReferences(config = {}, nodes = [], edges = [], currentNodeId) {
  return validateDecisionReferences({
    instructions: config?.instructions,
    input_mappings: { prompt: config?.prompt },
    rag_context: config?.rag_context,
  }, nodes, edges, currentNodeId).map((error) => ({ ...error, field: error.field === "input_mappings" ? "prompt" : error.field }));
}

export function validateConditionBranches(nodes = [], edges = []) {
  const errors = [];
  for (const node of nodes.filter((item) => ["logic.condition", "human.approval"].includes(item.data?.typeId))) {
    const outgoing = edges.filter((edge) => edge.source === node.id);
    const nodeId = node.data?.nodeId ?? node.id;
    const label = node.data?.label || nodeId;
    const options = branchOptions(node, nodes, edges);
    const branchType = node.data.typeId === "human.approval" ? "Human Approval" : "Condition";
    const code = node.data.typeId === "human.approval" ? "APPROVAL_BRANCH_LABEL" : "CONDITION_BRANCH_LABEL";
    if (!outgoing.length && branchType === "Condition") errors.push({ code: "CONDITION_NO_BRANCHES", nodeId, message: `${label}: Connect at least one outgoing branch.` });
    const seen = new Map();
    for (const edge of outgoing) {
      const value = edge.data?.condition;
      let message;
      if (typeof value !== "string" || !value.trim()) message = `Choose an outcome for this ${branchType} branch.`;
      else if (value !== value.trim()) message = "Branch labels cannot begin or end with spaces.";
      else if (value.length > 255) message = "Branch labels must be 255 characters or fewer.";
      else if (options !== null && !options.some((option) => option.value === value)) message = `Outcome '${value}' is not available. Choose a current outcome.`;
      else if (seen.has(value)) {
        message = `Outcome '${value}' is already used on this ${branchType}.`;
        if (!errors.some((error) => error.edgeId === seen.get(value))) {
          errors.push({ code, nodeId, edgeId: seen.get(value), message: `${label}: ${message}` });
        }
      }
      if (message) errors.push({ code, nodeId, edgeId: edge.id, message: `${label}: ${message}` });
      if (typeof value === "string" && !seen.has(value)) seen.set(value, edge.id);
    }
  }
  return errors;
}

export function validateDecisionReferences(config = {}, nodes = [], edges = [], currentNodeId) {
  const upstream = previousNodesFor(nodes, edges, currentNodeId, true);
  const ids = new Set(upstream.map((node) => node.data?.nodeId || node.id));
  const errors = [];
  const visit = (value, field) => {
    if (Array.isArray(value)) return value.forEach((item) => visit(item, field));
    if (value && typeof value === "object") return Object.values(value).forEach((item) => visit(item, field));
    if (typeof value !== "string") return;
    for (const match of value.matchAll(/\{\{\s*nodes\.([^\s.{}]+)(?:\.[^{}]*)?\s*\}\}/g)) {
      if (!ids.has(match[1])) errors.push({ field, message: `Referenced node '${match[1]}' is missing or not upstream. Reconnect it or update this expression.` });
    }
    if (/\{\{\s*trigger\./.test(value) && !upstream.some((node) => node.data?.typeId?.startsWith("trigger."))) errors.push({ field, message: "Connect an upstream trigger before using trigger variables." });
  };
  for (const field of ["instructions", "input_mappings", "rag_context"]) visit(config?.[field], field);
  return errors;
}

export function renameDecisionInput(mappings, oldName, newName) {
  if (Object.keys(mappings).some((name) => name !== oldName && name.trim() === newName.trim())) return null;
  return Object.fromEntries(Object.entries(mappings).map(([key, value]) => [key === oldName ? newName : key, value]));
}
