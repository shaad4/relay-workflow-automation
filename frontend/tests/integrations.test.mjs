import { test } from "node:test";
import assert from "node:assert/strict";
import {
  mcpEndpoint,
  announcementKey,
  assistants,
} from "../src/lib/integrations.js";
test("MCP configuration accepts only a credential-free HTTPS origin", () => {
  assert.equal(
    mcpEndpoint("https://mcp.example.test/"),
    "https://mcp.example.test/mcp",
  );
  for (const value of [
    undefined,
    "",
    "http://localhost:8001",
    "javascript:alert(1)",
    "https://user:secret@example.test",
    "https://example.test/mcp",
    "https://example.test/?token=secret",
    "https://example.test/#secret",
  ])
    assert.equal(mcpEndpoint(value), null);
});
test("announcements are versioned and isolated per user", () => {
  assert.notEqual(announcementKey("one"), announcementKey("two"));
  assert.match(announcementKey("one"), /:v1:/);
});
test("each assistant has OAuth manual setup and official help", () => {
  for (const assistant of assistants) {
    assert.match(assistant.steps.join(" "), /OAuth/);
    assert.match(assistant.steps.join(" "), /verify/);
    assert.equal(new URL(assistant.guide).protocol, "https:");
  }
});
