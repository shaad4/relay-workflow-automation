import test from 'node:test';
import assert from 'node:assert/strict';
import { workflowSaveSnapshot, workflowChangedDuringSave } from '../src/components/workflow/workflowSaveState.js';
const kb = 'fea3a93e-187a-4fe3-bb51-386a7f7e938f';
const node = (query = 'old') => ({ id: 'temp-node-1', position: { x: 10, y: 20 }, data: { nodeId: 'rag_1', typeId: 'ai.rag_search', label: 'RAG', config: { knowledge_base_id: kb, query, top_k: 5 } } });

test('edits during an asynchronous save remain unsaved until the next save', async () => {
  let current = { nodes: [node()], edges: [] };
  let revision = 1;
  const savedRevision = revision;
  const persisted = workflowSaveSnapshot(current.nodes, current.edges);
  let finish;
  const request = new Promise(resolve => { finish = resolve; });
  current = { nodes: [node('latest\n{{trigger.data.question}}')], edges: [] };
  revision++;
  finish();
  await request;
  assert.equal(workflowChangedDuringSave(persisted, current, savedRevision, revision), true);
  const nextPersisted = workflowSaveSnapshot(current.nodes, current.edges);
  assert.equal(workflowChangedDuringSave(nextPersisted, current, revision, revision), false);
  assert.equal(JSON.parse(nextPersisted).nodes[0].config.query, 'latest\n{{trigger.data.question}}');
});

test('legacy normalization does not leave an unchanged save dirty', () => {
  const legacy = node();
  legacy.data.config = { knowledge_base: kb, query: 'old', top_k: 5 };
  const saved = workflowSaveSnapshot([legacy], []);
  assert.equal(workflowChangedDuringSave(saved, { nodes: [structuredClone(legacy)], edges: [] }, 1, 1), false);
  const restored = JSON.parse(saved).nodes[0].config;
  assert.equal(restored.knowledge_base_id, kb);
  assert.equal(Object.hasOwn(restored, 'knowledge_base'), false);
  assert.equal(legacy.data.config.knowledge_base, kb);
});

test('temporary UUID replacement and selection are not configuration changes', () => {
  const original = node();
  const target = { ...node(), id: 'target', data: { ...node().data, nodeId: 'rag_2' } };
  const saved = workflowSaveSnapshot([original, target], [{ id: 'temp-edge', source: original.id, target: target.id }]);
  const remapped = { ...original, id: 'server-uuid', selected: true };
  assert.equal(workflowChangedDuringSave(saved, { nodes: [remapped, target], edges: [{ id: 'server-edge', source: remapped.id, target: target.id }] }, 3, 3), false);
});

test('revision guard detects edits before React updates the canvas ref', () => {
  const current = { nodes: [node()], edges: [] };
  assert.equal(workflowChangedDuringSave(workflowSaveSnapshot(current.nodes, current.edges), current, 1, 2), true);
});

test('live execution status changes never mark the workflow as unsaved', () => {
  const original = node();
  const saved = workflowSaveSnapshot([original], []);
  for (const executionStatus of ['pending', 'running', 'completed', 'failed', 'waiting_for_approval']) {
    const decorated = { ...original, data: { ...original.data, executionStatus } };
    assert.equal(workflowChangedDuringSave(saved, { nodes: [decorated], edges: [] }, 1, 1), false);
    assert.equal(JSON.parse(workflowSaveSnapshot([decorated], [])).nodes[0].executionStatus, undefined);
  }
  assert.equal(original.data.executionStatus, undefined);
});
