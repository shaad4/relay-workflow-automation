export const AI_PROVIDERS = [
  { id: "openai", name: "OpenAI", description: "GPT models" },
  { id: "gemini", name: "Google Gemini", description: "Gemini models" },
  { id: "anthropic", name: "Anthropic Claude", description: "Claude models" },
];

export function aiConnectionPayload(form, editing = false) {
  const errors = {};
  const name = form.name.trim();
  const apiKey = form.api_key.trim();
  if (!name || name.length > 100)
    errors.name = "Enter a name between 1 and 100 characters.";
  if (!AI_PROVIDERS.some((provider) => provider.id === form.provider))
    errors.provider = "Select a supported provider.";
  if (!editing && !apiKey) errors.api_key = "Enter an API key.";
  if (editing && !["active", "inactive"].includes(form.status))
    errors.status = "Select active or inactive.";
  const data = editing
    ? { name, status: form.status }
    : { name, provider: form.provider };
  if (apiKey) data.api_key = apiKey;
  return { data, errors };
}

// Only display known backend messages; provider errors may otherwise echo credentials.
const safeMessages = new Set([
  "AI connection not found",
  "AI connection is invalid or unavailable",
  "AI provider connection test failed",
  "Unable to retrieve provider models",
  "AI connection service unavailable",
  "Unsupported AI provider",
  "Invalid connection status",
]);
export function aiConnectionError(error) {
  if (error?.status === 401) return "Your session expired. Sign in again.";
  if (error?.status === 403)
    return "You do not have permission to manage this connection.";
  if (safeMessages.has(error?.message))
    return `${error.message}. Please retry or check the connection settings.`;
  if (error?.status === 422 || error?.status === 400)
    return "Check the connection name, provider, and API key, then retry.";
  return "Unable to complete this request. Check your connection and retry.";
}
