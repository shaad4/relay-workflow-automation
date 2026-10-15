import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { AI_PROVIDERS, aiConnectionPayload, aiConnectionError } from '../src/components/connections/aiConnectionForm.js';

const form = { name: ' Production ', provider: 'openai', api_key: ' dummy-test-key ', status: 'active' };
for (const provider of AI_PROVIDERS) {
  test(`create ${provider.name} uses exact provider identifier`, () => {
    const result = aiConnectionPayload({ ...form, provider: provider.id });
    assert.deepEqual(result.errors, {});
    assert.deepEqual(result.data, { name: 'Production', provider: provider.id, api_key: 'dummy-test-key' });
  });
}
test('invalid names, credentials and provider cannot be submitted', () => {
  for (const name of ['', '  ', 'a'.repeat(101)]) assert.ok(aiConnectionPayload({ ...form, name }).errors.name);
  for (const api_key of ['', '  ']) assert.ok(aiConnectionPayload({ ...form, api_key }).errors.api_key);
  assert.ok(aiConnectionPayload({ ...form, provider: 'unsupported' }).errors.provider);
  assert.deepEqual(aiConnectionPayload({ ...form, name: 'a'.repeat(100) }).errors, {});
});
test('rename and status changes omit blank key and immutable provider', () => {
  for (const status of ['active', 'inactive']) {
    for (const api_key of ['', '  ']) {
      const result = aiConnectionPayload({ ...form, status, api_key }, true);
      assert.deepEqual(result.errors, {});
      assert.deepEqual(result.data, { name: 'Production', status });
    }
  }
  assert.ok(aiConnectionPayload({ ...form, status: 'invalid' }, true).errors.status);
});
test('key rotation includes only the replacement key and retains input object', () => {
  const input = { ...form, api_key: ' replacement-test-key ' };
  const copy = structuredClone(input);
  assert.equal(aiConnectionPayload(input, true).data.api_key, 'replacement-test-key');
  assert.deepEqual(input, copy);
});
test('errors display safe backend messages without reflecting arbitrary credentials', () => {
  assert.match(aiConnectionError({ status: 502, message: 'AI provider connection test failed' }), /AI provider connection test failed/);
  assert.match(aiConnectionError({ status: 401 }), /Sign in/);
  for (const status of [400, 422, 500, undefined]) {
    assert.ok(!aiConnectionError({ status, message: 'dummy-secret-key in provider response' }).includes('dummy-secret-key'));
  }
});

// Exercise service functions through the real shared API client, with fetch mocked.
const moduleURL = (source) => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
process.env.NEXT_PUBLIC_AUTH_API_URL = 'https://relay.test';
const client = moduleURL(await readFile(new URL('../src/lib/api.js', import.meta.url), 'utf8'));
const source = await readFile(new URL('../src/services/aiProviderConnections.js', import.meta.url), 'utf8');
const service = await import(moduleURL(source.replace('"@/lib/api"', JSON.stringify(client))));

test('all seven gateway endpoints retain cookies, paths, methods and body contracts', async () => {
  const original = globalThis.fetch;
  const calls = [];
  const rows = [{ id: 'connection-1', name: 'Production', provider: 'openai', status: 'active' }];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    if (options.method === 'DELETE') return new Response(null, { status: 204 });
    const response = url.endsWith('/models/') ? { models: [{ id: 'from-api', name: 'API model' }] }
      : url.endsWith('/test/') ? { success: true, message: 'AI provider connection verified' }
      : options.method === 'GET' && url.endsWith('/connections/') ? rows : rows[0];
    return Response.json(response, { status: options.method === 'POST' && url.endsWith('/connections/') ? 201 : 200 });
  };
  try {
    await service.createAIConnection(aiConnectionPayload(form).data);
    assert.deepEqual(await service.listAIConnections(), rows);
    assert.deepEqual(await service.getAIConnection('connection-1'), rows[0]);
    await service.updateAIConnection('connection-1', aiConnectionPayload({ ...form, api_key: '' }, true).data);
    assert.deepEqual(await service.deleteAIConnection('connection-1'), {});
    assert.equal((await service.testAIConnection('connection-1')).success, true);
    assert.equal((await service.listAIConnectionModels('connection-1')).models[0].id, 'from-api');
    assert.deepEqual(calls.map(({ url, options }) => [url.replace('https://relay.test', ''), options.method]), [
      ['/ai/connections/', 'POST'], ['/ai/connections/', 'GET'], ['/ai/connections/connection-1/', 'GET'],
      ['/ai/connections/connection-1/', 'PATCH'], ['/ai/connections/connection-1/', 'DELETE'],
      ['/ai/connections/connection-1/test/', 'POST'], ['/ai/connections/connection-1/models/', 'GET'],
    ]);
    for (const { url, options } of calls) {
      assert.equal(options.credentials, 'include');
      assert.ok(!url.includes('dummy-test-key'));
      assert.ok(!options.body?.includes('workspace_id'));
    }
    assert.ok(!Object.hasOwn(JSON.parse(calls[3].options.body), 'api_key'));
    assert.equal(calls[5].options.body, undefined);
  } finally { globalThis.fetch = original; }
});
test('list errors propagate instead of becoming empty success responses', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => Response.json({ detail: 'AI connection service unavailable' }, { status: 502 });
  try { await assert.rejects(service.listAIConnections(), (error) => error.status === 502 && error.message === 'AI connection service unavailable'); }
  finally { globalThis.fetch = original; }
});
test('shared authentication refresh retries AI requests with cookies', async () => {
  const original = globalThis.fetch;
  const originalWindow = globalThis.window;
  const calls = [];
  globalThis.window = { dispatchEvent() {} };
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return calls.length === 1 ? Response.json({ detail: 'Expired' }, { status: 401 }) : Response.json(url.endsWith('/auth/refresh') ? { ok: true } : []);
  };
  try {
    assert.deepEqual(await service.listAIConnections(), []);
    assert.deepEqual(calls.map((call) => call.url), ['https://relay.test/ai/connections/', 'https://relay.test/auth/refresh', 'https://relay.test/ai/connections/']);
    assert.ok(calls.every((call) => call.options.credentials === 'include'));
  } finally { globalThis.fetch = original; globalThis.window = originalWindow; }
});
