import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { getNodeDefinition } from '../src/components/workflow/nodeDefinitions.js';
import { validateNodeConfiguration } from '../src/components/workflow/configValidation.js';
import { workflowSaveSnapshot } from '../src/components/workflow/workflowSaveState.js';

const config = { connection_id: 'existing', to: '{{trigger.data.recipient_email}}', subject: 'Student Report - {{trigger.data.student_name}}', body: '{{nodes.generate_1.content}}' };

test('email formats validate and legacy configurations stay valid', () => {
  assert.equal(getNodeDefinition('action.email').defaultConfig.body_format, 'plain');
  for (const format of [undefined, 'plain', 'html']) {
    assert.deepEqual(validateNodeConfiguration('action.email', { ...config, ...(format === undefined ? {} : { body_format: format }) }), []);
  }
  for (const format of ['HTML', 'markdown', '', null]) {
    assert.ok(validateNodeConfiguration('action.email', { ...config, body_format: format }).some((error) => error.field === 'body_format'));
  }
});

test('email inspector selects, saves, and restores Body Format, including read-only inspection', async () => {
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
  const inspector = await compile(`${source}\nexport { EmailConfig };`, 'NodeInspector.jsx', (name) => {
    if (name === 'react') return { ...React, useState: (initial) => [initial, () => {}], useEffect: () => {}, useContext: () => isReadOnly };
    if (name === './InspectorControls') return controls;
    if (name === 'react/jsx-runtime') return require(name);
    return {};
  });
  const findFormat = (element) => {
    if (!element || typeof element !== 'object') return null;
    if (element.type === 'fieldset') return element;
    return React.Children.toArray(element.props?.children).map(findFormat).find(Boolean);
  };
  let saved = { ...config };
  const render = () => inspector.EmailConfig({ config: saved, onChange: (field, value) => { saved = { ...saved, [field]: value }; }, variableContext: {} });
  const radios = () => React.Children.toArray(findFormat(render()).props.children[1].props.children).map((label) => label.props.children[0]);
  assert.equal(radios().find((radio) => radio.props.checked).props.value, 'plain');
  assert.deepEqual(radios().map((radio) => radio.props.value), ['plain', 'html']);
  for (const format of ['html', 'plain']) {
    radios().find((radio) => radio.props.value === format).props.onChange();
    const node = { id: 'email', position: { x: 0, y: 0 }, data: { nodeId: 'email', typeId: 'action.email', config: saved } };
    saved = JSON.parse(workflowSaveSnapshot([node], [])).nodes[0].config;
    assert.equal(saved.body_format, format);
    assert.equal(saved.body, config.body);
    assert.equal(radios().find((radio) => radio.props.checked).props.value, format);
    isReadOnly = true;
    assert.ok(radios().every((radio) => radio.props.disabled));
    radios().find((radio) => radio.props.value !== format).props.onChange();
    assert.equal(saved.body_format, format);
    const markup = renderToStaticMarkup(findFormat(render()));
    assert.match(markup, /Plain Text/);
    assert.match(markup, /HTML/);
    assert.equal((markup.match(/type="radio"/g) || []).length, 2);
    isReadOnly = false;
  }
});
