import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const moduleURL = source => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
process.env.NEXT_PUBLIC_AUTH_API_URL = 'https://relay.test';
const client = moduleURL(await readFile(new URL('../src/lib/api.js', import.meta.url), 'utf8'));
const source = (await readFile(new URL('../src/services/executions.js', import.meta.url), 'utf8'))
  .replace('"@/lib/api"', JSON.stringify(client))
  .replace('"@/lib/executions"', JSON.stringify(new URL('../src/lib/executions.js', import.meta.url).href));
const api = await import(moduleURL(source));
const group = { id: 'latest', workflow_id: 'workflow', execution_group_id: 'original', replay_of_execution_id: 'previous', status: 'completed', attempt_count: 3 };

test('groups and expanded attempts use distinct bounded gateway queries with cookies', async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url: new URL(url), options });
    return Response.json({ items: [group], total: 11, page: 2, page_size: 10 });
  };
  try {
    const result = await api.getExecutionGroups({ page: 2, status: 'COMPLETED' });
    assert.equal(result.items[0].attempt_count, 3);
    assert.equal(calls[0].url.searchParams.get('group_replays'), 'true');
    assert.equal(calls[0].url.searchParams.get('status'), 'completed');
    assert.equal(calls[0].url.searchParams.get('page'), '2');
    await api.getExecutionAttempts('original/encoded', { page: 2 });
    assert.equal(calls[1].url.searchParams.get('group_id'), 'original/encoded');
    assert.equal(calls[1].url.searchParams.has('status'), false);
    assert.equal(calls[1].url.searchParams.has('group_replays'), false);
    assert.equal(calls[1].url.searchParams.get('page_size'), '10');
    for (const call of calls) { assert.equal(call.options.credentials, 'include'); assert.equal(call.options.method, 'GET'); }
  } finally { globalThis.fetch = original; }
});

test('an outdated or malformed grouped response cannot silently show unrelated attempts', async () => {
  const original = globalThis.fetch;
  try {
    for (const item of [{ ...group, execution_group_id: undefined }, { ...group, attempt_count: 0 }, { ...group, attempt_count: '3' }]) {
      globalThis.fetch = async () => Response.json({ items: [item], total: 1, page: 1, page_size: 10 });
      await assert.rejects(api.getExecutionGroups(), /Unexpected execution group response/);
    }
  } finally { globalThis.fetch = original; }
});
