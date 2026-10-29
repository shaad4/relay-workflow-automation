// Optional browser regression: point RELAY_DASHBOARD_URL at a local build.
// All API calls are intercepted; fixtures never reach application services.
import { test } from "node:test";
import assert from "node:assert/strict";
const enabled = Boolean(
  process.env.RELAY_DASHBOARD_URL && process.env.RELAY_PLAYWRIGHT_MODULE,
);
test(
  "dashboard browser states, navigation, and responsive themes",
  { skip: !enabled },
  async (t) => {
    const { chromium } = await import(process.env.RELAY_PLAYWRIGHT_MODULE);
    const browser = await chromium.launch({
      executablePath: process.env.RELAY_CHROME || "/usr/bin/google-chrome",
      headless: true,
      args: ["--no-sandbox"],
    });
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1100 },
    });
    const origin = new URL(process.env.RELAY_DASHBOARD_URL).origin;
    let mode = "data",
      release;
    const requests = [],
      errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const fixture = (range) => ({
      range,
      timezone: "UTC",
      window_start: "2026-10-18T00:00:00Z",
      window_end: "2026-10-24T12:00:00Z",
      total_workflows: 15,
      active_workflows: 12,
      total_executions: 128,
      completed: 100,
      failed: 8,
      running: 6,
      waiting_for_approval: 4,
      pending: 2,
      cancelled: 8,
      success_rate: 92.59,
      pending_approvals: 3,
      pending_dlq: 2,
      execution_activity: Array.from(
        { length: range === "24h" ? 24 : range === "30d" ? 30 : 7 },
        (_, i) => ({
          bucket:
            range === "24h"
              ? `2026-10-24T${String(i).padStart(2, "0")}:00:00Z`
              : new Date(Date.UTC(2026, 9, 1 + i)).toISOString().slice(0, 10),
          completed: (i % 3) * 5 + 4,
          failed: i % 3,
        }),
      ),
      recent_executions: [
        "completed",
        "failed",
        "waiting_for_approval",
        "cancelled",
        "running",
      ].map((status, i) => ({
        id: `00000000-0000-4000-8000-00000000000${i}`,
        workflow_id: "workflow-1",
        workflow_name: [
          "Order processing",
          "Invoice reconciliation",
          "Refund review",
          "Daily digest",
          "Customer onboarding",
        ][i],
        status,
        trigger_type: ["manual", "webhook", "schedule", "manual", "webhook"][i],
        started_at: i ? null : "2026-10-24T10:00:00Z",
        created_at: "2026-10-24T10:00:00Z",
        duration_ms: i ? null : 1250,
      })),
    });
    await page.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (url.origin === origin) return route.continue();
      let data = {};
      if (url.pathname === "/auth/refresh")
        data = { access_token: "test-only" };
      else if (url.pathname === "/auth/me")
        data = {
          name: "Test User",
          email: "test@example.com",
          workspace_name: "Test workspace",
        };
      else if (url.pathname === "/dashboard/overview") {
        const range = url.searchParams.get("range");
        requests.push(range);
        if (mode === "loading")
          await new Promise((resolve) => {
            release = resolve;
          });
        if (mode === "error")
          return route.fulfill({
            status: 502,
            contentType: "application/json",
            body: JSON.stringify({
              detail: "Dashboard is temporarily unavailable.",
            }),
          });
        data = fixture(range);
        if (mode === "empty") {
          for (const key of [
            "total_workflows",
            "active_workflows",
            "total_executions",
            "completed",
            "failed",
            "running",
            "waiting_for_approval",
            "pending",
            "cancelled",
            "pending_approvals",
            "pending_dlq",
          ])
            data[key] = 0;
          data.success_rate = null;
          data.recent_executions = [];
          data.execution_activity = data.execution_activity.map((x) => ({
            ...x,
            completed: 0,
            failed: 0,
          }));
        }
      } else if (url.pathname.startsWith("/approvals")) data = [];
      else data = { items: [], total: 0, page: 1, page_size: 10 };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(data),
      });
    });
    const loaded = () =>
      page
        .getByRole("heading", { name: "Recent Executions", exact: true })
        .waitFor();
    try {
      await t.test(
        "API metrics, charts, KPI links, and create dialog",
        async () => {
          await page.goto(`${origin}/dashboard`);
          await loaded();
          assert.equal(requests[0], "7d");
          assert.equal(
            await page.getByText("92.59%", { exact: true }).count(),
            1,
          );
          assert.equal(await page.locator("tbody tr").count(), 12);
          assert.equal(
            await page
              .getByRole("link", { name: /Active Workflows/ })
              .getAttribute("href"),
            "/dashboard/workflows",
          );
          assert.equal(
            await page
              .getByRole("link", { name: "Order processing", exact: true })
              .getAttribute("href"),
            "/dashboard/executions/00000000-0000-4000-8000-000000000000",
          );
          await page
            .getByRole("button", { name: "Create Workflow", exact: true })
            .click();
          await page.getByRole("dialog").waitFor();
          await page.keyboard.press("Escape");
          const chart = page
            .getByLabel("Completed and failed execution activity")
            .locator(".recharts-wrapper");
          await chart.hover({ position: { x: 200, y: 100 } });
          await page
            .locator(".recharts-tooltip-wrapper")
            .filter({ visible: true })
            .waitFor();
          await page.mouse.move(0, 0);
          await page.screenshot({
            path: "/tmp/relay-dashboard-desktop-light.png",
            fullPage: true,
          });
        },
      );
      await t.test("range switching and chart data", async () => {
        await page.getByLabel("Time range").selectOption("24h");
        await loaded();
        assert.equal(requests.at(-1), "24h");
        await page.getByText("View activity data", { exact: true }).click();
        assert.equal(await page.locator("tbody tr").count(), 29);
        await page.getByLabel("Time range").selectOption("30d");
        await loaded();
        assert.equal(requests.at(-1), "30d");
        assert.equal(await page.locator("tbody tr").count(), 35);
        await page.getByText("View activity data", { exact: true }).click();
      });
      await t.test("loading, empty state, error, retry", async () => {
        mode = "loading";
        await page.getByRole("button", { name: /Refresh overview/ }).click();
        await page.getByRole("status", { name: "Loading dashboard" }).waitFor();
        for (let i = 0; i < 100 && !release; i++)
          await new Promise((r) => setTimeout(r, 20));
        assert.ok(release);
        mode = "empty";
        release();
        await page
          .getByRole("heading", { name: "Your first run starts here" })
          .waitFor();
        assert.equal(
          await page.getByText("No executions", { exact: true }).count(),
          1,
        );
        mode = "error";
        await page.getByRole("button", { name: /Refresh overview/ }).click();
        await page
          .getByRole("heading", { name: "Overview unavailable" })
          .waitFor();
        mode = "data";
        await page.getByRole("button", { name: "Try again" }).click();
        await loaded();
      });
      await t.test("dark theme and mobile widths", async () => {
        await page.evaluate(() => {
          localStorage.setItem("relay-theme", "dark");
          document.documentElement.classList.remove("light");
          document.documentElement.classList.add("dark");
        });
        assert.match(
          await page.evaluate(() =>
            getComputedStyle(document.documentElement)
              .getPropertyValue("--canvas")
              .trim(),
          ),
          /^#000(?:000)?$/,
        );
        await page.screenshot({
          path: "/tmp/relay-dashboard-desktop-dark.png",
          fullPage: true,
        });
        for (const width of [390, 320]) {
          await page.setViewportSize({ width, height: 844 });
          assert.ok(
            await page.evaluate(
              () => document.documentElement.scrollWidth <= innerWidth,
            ),
            `overflow at ${width}`,
          );
        }
        await page.setViewportSize({ width: 390, height: 844 });
        await page.screenshot({
          path: "/tmp/relay-dashboard-mobile.png",
          fullPage: true,
        });
        assert.deepEqual(errors, []);
      });
      await t.test("recent execution navigation", async () => {
        await page
          .getByRole("link", { name: "Order processing", exact: true })
          .click();
        await page.waitForURL(
          "**/dashboard/executions/00000000-0000-4000-8000-000000000000",
        );
      });
    } finally {
      await browser.close();
    }
  },
);
