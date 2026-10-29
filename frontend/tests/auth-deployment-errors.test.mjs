import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { setImmediate } from "node:timers/promises";

const require = createRequire(import.meta.url);
const React = require("react");
const { transform, loadBindings } =
  await import("next/dist/build/swc/index.js");
await loadBindings();

async function componentHarness(
  path,
  overrides,
  error,
  exportName = "default",
) {
  const states = [];
  const effects = [];
  let cursor = 0;
  const source = await readFile(
    new URL(`../src/${path}`, import.meta.url),
    "utf8",
  );
  const compiled = await transform(
    source + (exportName === "default" ? "" : `\nexport { ${exportName} };`),
    {
      filename: path,
      jsc: {
        parser: { syntax: "ecmascript", jsx: true },
        transform: { react: { runtime: "automatic" } },
      },
      module: { type: "commonjs" },
    },
  );
  const exports = {};
  const imports = (name) => {
    if (name === "react")
      return {
        ...React,
        useState(initial) {
          const index = cursor++;
          states[index] = Object.hasOwn(overrides, index)
            ? overrides[index]
            : initial;
          return [
            states[index],
            (value) => {
              states[index] =
                typeof value === "function" ? value(states[index]) : value;
            },
          ];
        },
        useEffect(callback) {
          effects.push(callback);
        },
        useRef: () => ({ current: null }),
      };
    if (name === "react/jsx-runtime") return require(name);
    if (name === "next/navigation")
      return {
        useSearchParams: () => new URLSearchParams("token=synthetic"),
        useRouter: () => ({ push() {} }),
      };
    if (name === "@/services/auth")
      return new Proxy(
        {},
        {
          get: () => async () => {
            throw error;
          },
        },
      );
    if (name === "next/link") return { __esModule: true, default: "a" };
    return { __esModule: true, default: () => null };
  };
  new Function("require", "exports", compiled.code)(imports, exports);
  const element = exports[exportName]({
    open: true,
    email: "synthetic@example.test",
    onClose() {},
  });
  return { element, states, effects };
}

function find(element, predicate) {
  if (!element || typeof element !== "object") return null;
  if (predicate(element)) return element;
  return React.Children.toArray(element.props?.children)
    .map((child) => find(child, predicate))
    .find(Boolean);
}

for (const error of [
  new TypeError("Failed to fetch"),
  Object.assign(new Error("API service unavailable"), { status: 502 }),
]) {
  const kind = error instanceof TypeError ? "network outage" : "gateway outage";
  test(`forgot password does not claim email delivery after ${kind}`, async () => {
    const { element, states } = await componentHarness(
      "components/auth/ForgotPasswordForm.js",
      { 0: "synthetic@example.test" },
      error,
    );
    await find(element, (node) => node.type === "form").props.onSubmit({
      preventDefault() {},
    });
    assert.equal(states[4], false);
    assert.match(states[5], /Unable to process/);
    assert.equal(states[2], false);
  });
  test(`password reset does not claim credential changes after ${kind}`, async () => {
    const { element, states } = await componentHarness(
      "components/auth/ResetPasswordForm.js",
      {
        0: {
          password: "Synthetic-Test-123!",
          confirmPassword: "Synthetic-Test-123!",
        },
      },
      error,
    );
    await find(element, (node) => node.type === "form").props.onSubmit({
      preventDefault() {},
    });
    assert.equal(states[6], false);
    assert.match(states[8], /Unable to reset/);
    assert.equal(states[5], false);
  });
  test(`registration does not display verification success after ${kind}`, async () => {
    const { element, states } = await componentHarness(
      "components/auth/RegisterForm.js",
      {
        0: 3,
        1: {
          name: "Synthetic User",
          email: "synthetic@example.test",
          workspace_name: "Test Workspace",
          password: "Synthetic-Test-123!",
          confirmPassword: "Synthetic-Test-123!",
        },
      },
      error,
    );
    await find(element, (node) => node.type === "form").props.onSubmit({
      preventDefault() {},
    });
    assert.equal(states[8], false);
    assert.match(states[7], /Unable to create|API service unavailable/);
    assert.equal(states[6], false);
  });
  test(`resend verification does not claim email delivery after ${kind}`, async () => {
    const { element, states } = await componentHarness(
      "components/auth/EmailVerificationModal.js",
      {},
      error,
    );
    const button = find(
      element,
      (node) =>
        node.type === "button" && node.props.onClick?.name === "handleResend",
    );
    await button.props.onClick();
    assert.equal(states[2], "");
    assert.notEqual(states[3], "");
    assert.equal(states[1], 0);
    assert.equal(states[0], false);
  });
  test(`email verification does not report success after ${kind}`, async () => {
    const { states, effects } = await componentHarness(
      "app/(auth)/verify-email/page.js",
      {},
      error,
      "VerifyEmailContent",
    );
    effects[0]();
    await setImmediate();
    assert.equal(states[0], "error");
    assert.notEqual(states[1], "");
  });
}
