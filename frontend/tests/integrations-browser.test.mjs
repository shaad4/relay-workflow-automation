import { test } from "node:test";
import assert from "node:assert/strict";
const enabled = Boolean(
  process.env.RELAY_INTEGRATIONS_URL && process.env.RELAY_PLAYWRIGHT_MODULE,
);
test(
  "integrations setup, clipboard, keyboard, responsive layouts and announcement persistence",
  { skip: !enabled },
  async () => {
    const { chromium } = await import(process.env.RELAY_PLAYWRIGHT_MODULE);
    const browser = await chromium.launch({
      executablePath: process.env.RELAY_CHROME,
      headless: true,
      args: ["--no-sandbox"],
    });
    try {
      const context = await browser.newContext();
      const page = await context.newPage();
      const origin = process.env.RELAY_INTEGRATIONS_URL;
      const errors = [];
      page.on("pageerror", (error) => errors.push(error.message));
      await page.route("**/api/relay/**", (route) => {
        const path = new URL(route.request().url()).pathname;
        const data = path.endsWith("/auth/me")
          ? {
              id: "integration-user",
              workspace_id: "workspace-1",
              name: "Test User",
              email: "test@example.test",
            }
          : path.endsWith("/auth/refresh")
            ? {}
            : { workflows: [], executions: [], approvals: [], total: 0 };
        return route.fulfill({ json: data });
      });
      await page.addInitScript(() => {
        Object.defineProperty(navigator, "clipboard", {
          value: {
            writeText: async (text) => {
              window.copiedText = text;
            },
          },
        });
      });
      await page.goto(`${origin}/integrations`);
      await page
        .getByRole("heading", { name: "Connect Relay to Your AI" })
        .waitFor();
      for (const name of ["ChatGPT", "Claude"]) {
        const trigger = page.getByRole("button", {
          name: `Connect to ${name}`,
          exact: true,
        });
        await trigger.click();
        const dialog = page.getByRole("dialog");
        await dialog.waitFor();
        await dialog.getByRole("button", { name: "Copy URL" }).click();
        assert.equal(
          await page.evaluate(() => window.copiedText),
          "https://mcp.example.test/mcp",
        );
        assert.match(await dialog.textContent(), /Copied/);
        for (let i = 0; i < 9; i++) {
          await page.keyboard.press("Tab");
          assert.equal(
            await page.evaluate(
              () => !!document.activeElement.closest('[role="dialog"]'),
            ),
            true,
          );
        }
        await page.keyboard.press("Escape");
        assert.equal(await page.getByRole("dialog").count(), 0);
        assert.equal(
          await trigger.evaluate((el) => el === document.activeElement),
          true,
        );
      }
      await page
        .getByRole("button", { name: "Copy prompt", exact: true })
        .first()
        .click();
      assert.equal(
        await page.evaluate(() => window.copiedText),
        "List all my Relay workflows.",
      );
      for (const width of [320, 768, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        assert.equal(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
          true,
        );
        await page.getByRole("button", { name: "Claude Setup Guide" }).click();
        assert.equal(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
          true,
        );
        await page.keyboard.press("Escape");
      }
      await page.goto(`${origin}/dashboard`);
      await page.getByRole("dialog").waitFor();
      await page.getByRole("button", { name: "Maybe Later" }).click();
      assert.equal(
        await page.evaluate(() =>
          localStorage.getItem("relay:mcp-announcement:v1:integration-user"),
        ),
        "dismissed",
      );
      await page.reload();
      await page.waitForTimeout(1400);
      assert.equal(await page.getByRole("dialog").count(), 0);
      await page.evaluate(() =>
        localStorage.removeItem("relay:mcp-announcement:v1:integration-user"),
      );
      await page.reload();
      await page.getByRole("dialog").waitFor();
      await page.getByRole("button", { name: "Explore Integrations" }).click();
      await page.waitForURL("**/integrations");
      assert.deepEqual(errors, []);
    } finally {
      await browser.close();
    }
  },
);
