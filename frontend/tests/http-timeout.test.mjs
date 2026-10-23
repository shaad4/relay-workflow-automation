import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { getNodeDefinition } from '../src/components/workflow/nodeDefinitions.js';
import { validateNodeConfiguration, validateWorkflowConfiguration } from '../src/components/workflow/configValidation.js';
import { workflowSaveSnapshot } from '../src/components/workflow/workflowSaveState.js';
const config = { connection_id: 'existing', method: 'GET', url: '/delay-10', headers: 'X-Test: yes', body: '{}' };
test('HTTP defaults and timeout validation apply to nodes and publishing', () => {
  assert.equal(getNodeDefinition('action.http_request').defaultConfig.timeout, 10);
  for (const timeout of [undefined, 1, 10, 20, 120]) assert.deepEqual(validateNodeConfiguration('action.http_request', { ...config, timeout }), []);
  for (const timeout of ['', null, 0, -1, 1.5, 121, '20', NaN, Infinity]) {
    const node = { id: 'http', data: { typeId: 'action.http_request', config: { ...config, timeout } } };
    assert.ok(validateNodeConfiguration('action.http_request', node.data.config).some(e => e.field === 'timeout'));
    assert.ok(validateWorkflowConfiguration([node], [], { includeStructure: false }).some(e => e.field === 'timeout'));
  }
});
test('HTTP timeout input saves numbers, restores them and prevents read-only changes', async () => {
  const require = createRequire(import.meta.url);
  const React = require('react');
  const { renderToStaticMarkup } = require('react-dom/server');
  const { transform, loadBindings } = await import('next/dist/build/swc/index.js');
  await loadBindings();
  const compile = async (source, filename, imports) => {
    const compiled = await transform(source, { filename, jsc: { parser: { syntax: 'ecmascript', jsx: true }, transform: { react: { runtime: 'automatic' } } }, module: { type: 'commonjs' } });
    const exports = {};
    new Function('require', 'exports', compiled.code)(imports, exports);
    return exports;
  };
  const controls = await compile(await readFile(new URL('../src/components/workflow/InspectorControls.jsx', import.meta.url), 'utf8'), 'InspectorControls.jsx', require);
  const source = await readFile(new URL('../src/components/workflow/NodeInspector.jsx', import.meta.url), 'utf8');
  let isReadOnly = false;
  const inspector = await compile(`${source}\nexport { HttpRequestConfig };`, 'NodeInspector.jsx', (name) => {
    if (name === 'react') return { ...React, useState: (initial) => [initial, () => {}], useEffect: () => {}, useContext: () => isReadOnly };
    if (name === './InspectorControls') return controls;
    if (name === './configValidation') return { validateNodeConfiguration };
    if (name === 'react/jsx-runtime') return require(name);
    return {};
  });
  const walk = (element) => {
    if (!element || typeof element !== 'object') return [];
    return [element, ...React.Children.toArray(element.props?.children).flatMap(walk)];
  };
  let saved = { ...config };
  const render = () => inspector.HttpRequestConfig({ config: saved, onChange: (field, value) => { saved = { ...saved, [field]: value }; }, variableContext: {} });
  const input = () => walk(render()).find(e => e.props?.['aria-label'] === 'Timeout (seconds)');
  assert.equal(input().props.value, 10);
  assert.equal(input().props.type, 'number');
  for (const value of ['', '0', '-1', '1.5', '121']) {
    input().props.onChange({ target: { value, valueAsNumber: Number(value) } });
    assert.equal(input().props['aria-invalid'], true);
  }
  input().props.onChange({ target: { value: '20', valueAsNumber: 20 } });
  const node = { id: 'http', position: { x: 0, y: 0 }, data: { typeId: 'action.http_request', config: saved } };
  saved = JSON.parse(workflowSaveSnapshot([node], [])).nodes[0].config;
  assert.deepEqual(saved, { ...config, timeout: 20 });
  assert.equal(input().props.value, 20);
  isReadOnly = true;
  input().props.onChange({ target: { value: '30', valueAsNumber: 30 } });
  assert.equal(saved.timeout, 20);
  assert.match(renderToStaticMarkup(React.createElement(controls.InspectorReadOnly.Provider, { value: true }, input())), /readonly/i);
  const builder = await readFile(new URL('../src/components/workflow/WorkflowBuilder.jsx', import.meta.url), 'utf8');
  assert.match(builder, /\["ai.rag_search", "ai.decision", "action.http_request"\]\.includes/);
  assert.match(builder, /configuration: node.data.config/);
});
