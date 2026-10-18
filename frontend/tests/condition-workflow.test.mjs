import test from 'node:test';
import assert from 'node:assert/strict';

import { getNodeDefinition, clearExampleNodeConfig } from '../src/components/workflow/nodeDefinitions.js';
import { validateNodeConfiguration, validateWorkflowConfiguration, validateConditionReferences, validateConditionBranches, isLegacyConditionConfiguration } from '../src/components/workflow/configValidation.js';
import { outputsByType, previousNodesFor } from '../src/components/workflow/workflowVariables.js';
import { workflowSaveSnapshot } from '../src/components/workflow/workflowSaveState.js';

const id = 'fea3a93e-187a-4fe3-bb51-386a7f7e938f';
const node = (id, logical, typeId, config) => ({ id, position: { x: 0, y: 0 }, data: { nodeId: logical, typeId, label: logical, config } });
const nodes = [
  node('webhook-ui', 'webhook', 'trigger.webhook', { webhook_id: id }),
  node('decision-ui', 'classify', 'ai.decision', { connection_id: id, model: 'test-model', instructions: 'Classify', input_mappings: {}, rag_context: '', allowed_decisions: ['TECHNICAL', 'BILLING', 'GENERAL'] }),
  node('condition-ui', 'route', 'logic.condition', { value: '{{nodes.classify.decision}}' }),
  ...['technical', 'billing', 'general'].map((name) => node(`email-${name}`, `email_${name}`, 'action.email', { connection_id: id, to: `${name}@example.test`, subject: 'Result', body: 'Handled' })),
];
const edges = [
  { id: 'to-decision', source: 'webhook-ui', target: 'decision-ui' },
  { id: 'to-condition', source: 'decision-ui', target: 'condition-ui' },
  ...['TECHNICAL', 'BILLING', 'GENERAL'].map((label) => ({ id: `branch-${label}`, source: 'condition-ui', target: `email-${label.toLowerCase()}`, data: { condition: label }, label })),
];

test('Condition defaults and edits use only the exact-value backend contract', () => {
  assert.deepEqual(getNodeDefinition('logic.condition').defaultConfig, { value: '' });
  assert.deepEqual(validateNodeConfiguration('logic.condition', { value: '{{nodes.classify.decision}}' }), []);
  assert.deepEqual(validateNodeConfiguration('logic.condition', { value: 'TECHNICAL' }), []);
  assert.ok(validateNodeConfiguration('logic.condition', { value: '' }).some((error) => error.field === 'value'));
  assert.ok(validateNodeConfiguration('logic.condition', { value: 'x'.repeat(2001) }).some((error) => error.field === 'value'));
});

test('AI Decision picker source uses the actual upstream logical node ID', () => {
  const previous = previousNodesFor(nodes, edges, 'condition-ui');
  assert.deepEqual(previous.map((item) => item.data.nodeId), ['classify']);
  assert.ok(outputsByType['ai.decision'].includes('decision'));
  assert.deepEqual(validateConditionReferences({ value: '{{nodes.classify.decision}}' }, nodes, edges, 'condition-ui'), []);
  assert.ok(validateConditionReferences({ value: '{{nodes.email_technical.message_id}}' }, nodes, edges, 'condition-ui').some((error) => error.field === 'value'));
  assert.ok(validateConditionReferences({ value: '{{nodes.missing.decision}}' }, nodes, edges, 'condition-ui').some((error) => error.field === 'value'));
});

test('three case-sensitive Condition labels validate and preserve their exact values', () => {
  assert.deepEqual(validateConditionBranches(nodes, edges), []);
  assert.deepEqual(validateWorkflowConfiguration(nodes, edges), []);
  const restored = JSON.parse(workflowSaveSnapshot(nodes, edges));
  assert.equal(restored.nodes.find((item) => item.nodeId === 'route').config.value, '{{nodes.classify.decision}}');
  assert.deepEqual(restored.edges.filter((edge) => edge.source === 'route').map((edge) => edge.condition).sort(), ['BILLING', 'GENERAL', 'TECHNICAL']);
});

test('empty, duplicate and padded Condition labels block validation before publishing', () => {
  const empty = edges.map((edge) => edge.id === 'branch-BILLING' ? { ...edge, data: { condition: null }, label: '' } : edge);
  assert.ok(validateConditionBranches(nodes, empty).some((error) => error.edgeId === 'branch-BILLING'));
  const duplicate = edges.map((edge) => edge.id === 'branch-BILLING' ? { ...edge, data: { condition: 'TECHNICAL' }, label: 'TECHNICAL' } : edge);
  assert.deepEqual(new Set(validateConditionBranches(nodes, duplicate).map((error) => error.edgeId)), new Set(['branch-TECHNICAL', 'branch-BILLING']));
  assert.ok(validateWorkflowConfiguration(nodes, duplicate).some((error) => error.code === 'CONDITION_BRANCH_LABEL'));
  const padded = edges.map((edge) => edge.id === 'branch-GENERAL' ? { ...edge, data: { condition: ' GENERAL' } } : edge);
  assert.ok(validateConditionBranches(nodes, padded).some((error) => error.edgeId === 'branch-GENERAL'));
  const cased = edges.map((edge) => edge.id === 'branch-BILLING' ? { ...edge, data: { condition: 'technical' }, label: 'technical' } : edge);
  assert.ok(validateConditionBranches(nodes, cased).some((error) => error.edgeId === 'branch-BILLING'));
});

test('legacy Condition settings survive draft load and save until explicit replacement', () => {
  const legacy = { field: '{{nodes.classify.decision}}', operator: 'equals', value: 'TECHNICAL' };
  assert.equal(isLegacyConditionConfiguration(legacy), true);
  assert.deepEqual(clearExampleNodeConfig('logic.condition', legacy), legacy);
  assert.ok(validateNodeConfiguration('logic.condition', legacy).some((error) => error.field === 'legacy'));
  const draft = nodes.map((item) => item.id === 'condition-ui' ? { ...item, data: { ...item.data, config: legacy } } : item);
  assert.deepEqual(JSON.parse(workflowSaveSnapshot(draft, edges)).nodes.find((item) => item.nodeId === 'route').config, legacy);
  assert.deepEqual(validateNodeConfiguration('logic.condition', { value: '{{nodes.classify.decision}}' }), []);
});

test('Human Approval labels and existing RAG/AI Decision configuration remain valid', () => {
  const approval = node('approval-ui', 'approval', 'human.approval', { approver_user_id: id, message: 'Review', timeout_minutes: null });
  const approvalEdges = [
    { id: 'approve', source: 'approval-ui', target: 'email-technical', data: { condition: 'approved' }, label: 'approved' },
    { id: 'reject', source: 'approval-ui', target: 'email-billing', data: { condition: 'rejected' }, label: 'rejected' },
  ];
  assert.deepEqual(validateNodeConfiguration('human.approval', approval.data.config), []);
  assert.deepEqual(validateConditionBranches([approval, ...nodes], approvalEdges), [{ code: 'CONDITION_NO_BRANCHES', nodeId: 'route', message: 'route: Connect at least one outgoing branch.' }]);
  assert.deepEqual(JSON.parse(workflowSaveSnapshot([approval, ...nodes], approvalEdges)).edges.map((edge) => edge.condition).sort(), ['approved', 'rejected']);
  assert.deepEqual(validateNodeConfiguration('ai.decision', nodes[1].data.config), []);
  assert.deepEqual(validateNodeConfiguration('ai.rag_search', { knowledge_base_id: id, query: 'Policy', top_k: 5 }), []);
});
