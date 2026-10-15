import test from 'node:test';
import assert from 'node:assert/strict';

import { getNodeDefinition, clearExampleNodeConfig } from '../src/components/workflow/nodeDefinitions.js';
import { validateNodeConfiguration, validateWorkflowConfiguration, validateGenerateReferences } from '../src/components/workflow/configValidation.js';
import { outputsByType, previousNodesFor } from '../src/components/workflow/workflowVariables.js';
import { workflowSaveSnapshot } from '../src/components/workflow/workflowSaveState.js';

const id = 'fea3a93e-187a-4fe3-bb51-386a7f7e938f';
const config = { connection_id: id, model: 'catalog-model', instructions: 'Be helpful.', prompt: 'Reply to {{trigger.data.message}}', rag_context: '{{nodes.knowledge.context}}' };
const node = (id, logical, typeId, config) => ({ id, position: { x: 0, y: 0 }, data: { nodeId: logical, typeId, label: logical, config } });
const nodes = [
  node('webhook-ui', 'webhook', 'trigger.webhook', { webhook_id: id }),
  node('rag-ui', 'knowledge', 'ai.rag_search', { knowledge_base_id: id, query: 'Policy', top_k: 5 }),
  node('generate-ui', 'generate_1', 'ai.generate', config),
  node('gmail-ui', 'gmail', 'action.email', { connection_id: id, to: 'test@example.com', subject: 'Reply', body: '{{nodes.generate_1.content}}' }),
];
const edges = [
  { source: 'webhook-ui', target: 'rag-ui' },
  { source: 'rag-ui', target: 'generate-ui' },
  { source: 'generate-ui', target: 'gmail-ui' },
];

test('AI Generate defaults and backend field names have no provider or model assumption', () => {
  assert.deepEqual(getNodeDefinition('ai.generate').defaultConfig, { connection_id: '', model: '', instructions: '', prompt: '', rag_context: '' });
  assert.deepEqual(validateNodeConfiguration('ai.generate', config), []);
  assert.deepEqual(validateNodeConfiguration('ai.generate', { ...config, rag_context: '', instructions: '' }), []);
});

test('required fields, limits, and unsupported fields block validation', () => {
  for (const [field, value] of [['connection_id', ''], ['connection_id', 'bad-id'], ['model', ''], ['model', 'x'.repeat(151)], ['prompt', ' '], ['prompt', 'x'.repeat(10001)], ['instructions', 'x'.repeat(10001)], ['rag_context', 'x'.repeat(2001)]]) {
    assert.ok(validateNodeConfiguration('ai.generate', { ...config, [field]: value }).some((error) => error.field === field), field);
  }
  assert.ok(validateNodeConfiguration('ai.generate', { ...config, api_key: 'secret' }).some((error) => error.field === 'legacy'));
});

test('prompt and RAG expressions accept only upstream logical node IDs', () => {
  assert.deepEqual(validateGenerateReferences(config, nodes, edges, 'generate-ui'), []);
  assert.deepEqual(previousNodesFor(nodes, edges, 'generate-ui').map((item) => item.data.nodeId), ['knowledge']);
  assert.ok(validateGenerateReferences({ ...config, prompt: '{{nodes.gmail.message_id}}' }, nodes, edges, 'generate-ui').some((error) => error.field === 'prompt'));
  assert.ok(validateGenerateReferences({ ...config, rag_context: '{{nodes.deleted.context}}' }, nodes, edges, 'generate-ui').some((error) => error.field === 'rag_context'));
  assert.deepEqual(validateWorkflowConfiguration(nodes, edges), []);
});

test('model, instructions, prompt, and RAG context survive draft snapshot and reload', () => {
  const restored = JSON.parse(workflowSaveSnapshot(nodes, edges));
  assert.deepEqual(restored.nodes.find((item) => item.nodeId === 'generate_1').config, config);
  assert.deepEqual(outputsByType['ai.generate'], ['content', 'model', 'input_tokens', 'output_tokens']);
  assert.ok(previousNodesFor(nodes, edges, 'gmail-ui').some((item) => item.data.nodeId === 'generate_1'));
});

test('legacy prompt and model remain unchanged until a connection is selected', () => {
  const legacy = { prompt: 'Generate summary of customer ticket', model: 'gemini-2.5-flash' };
  assert.deepEqual(clearExampleNodeConfig('ai.generate', legacy), legacy);
  assert.ok(validateNodeConfiguration('ai.generate', legacy).some((error) => error.field === 'connection_id'));
  const draft = nodes.map((item) => item.id === 'generate-ui' ? { ...item, data: { ...item.data, config: legacy } } : item);
  assert.deepEqual(JSON.parse(workflowSaveSnapshot(draft, edges)).nodes.find((item) => item.nodeId === 'generate_1').config, legacy);
  assert.deepEqual(validateNodeConfiguration('ai.decision', { connection_id: id, model: 'test', instructions: 'Classify', input_mappings: {}, allowed_decisions: ['ONE', 'TWO'] }), []);
  assert.deepEqual(validateNodeConfiguration('ai.rag_search', nodes[1].data.config), []);
});
