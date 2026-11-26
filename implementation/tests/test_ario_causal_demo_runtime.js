const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const root = path.resolve(__dirname, '..', '..');
const html = fs.readFileSync(path.join(root, 'website', 'ario-causal-demo.html'), 'utf8');
const match = html.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(match, 'inline application script must exist');

function makeElement(id) {
  return {
    id,
    innerText: '',
    innerHTML: '',
    attributes: {},
    listeners: {},
    dataId: null,
    classList: { add() {}, remove() {}, contains(name) { return name === 'node-circle' && id.startsWith('node-'); } },
    focus() { document.activeElement = this; },
    addEventListener(type, callback) {
      (this.listeners[type] ||= []).push(callback);
    },
    getAttribute(name) { return this.attributes[name] || (name === 'data-id' ? this.dataId : null); },
    setAttribute(name, value) { this.attributes[name] = value; }
  };
}

const elements = new Map();
function getElementById(id) {
  if (!elements.has(id)) elements.set(id, makeElement(id));
  return elements.get(id);
}
const document = {
  documentElement: { lang: '', dir: '' },
  ready: null,
  activeElement: null,
  addEventListener(type, callback) {
    if (type === 'DOMContentLoaded') this.ready = callback;
  },
  getElementById,
  querySelectorAll(selector) {
    if (selector === '.scen-btn') return ['btn-base', 'btn-fals', 'btn-self'].map(getElementById);
    return [];
  }
};
const svg = getElementById('graphSvg');
// Model DOM replacement explicitly: detached SVG nodes lose focus.
svg.nodeElements = [];
svg.contains = function(element) { return this.nodeElements.includes(element); };
let svgMarkup = '';
Object.defineProperty(svg, 'innerHTML', {
  get() { return svgMarkup; },
  set(value) {
    if (this.contains(document.activeElement)) document.activeElement = getElementById('body');
    svgMarkup = value;
    this.nodeElements = [];
  }
});
svg.querySelectorAll = function(selector) {
  if (selector !== '.node-circle') return [];
  if (this.nodeElements.length) return this.nodeElements;
  const nodes = [...this.innerHTML.matchAll(/<g class="node-circle" data-id="([^"]+)"[^>]*aria-pressed="([^"]+)"[^>]*>/g)];
  this.nodeElements = nodes.map(([, id, pressed]) => {
    const element = makeElement('node-' + id);
    element.dataId = id;
    element.setAttribute('aria-pressed', pressed);
    return element;
  });
  return this.nodeElements;
};

const context = vm.createContext({ document });
vm.runInContext(match[1], context, { filename: 'ario-causal-demo-inline.js' });
assert.equal(typeof document.ready, 'function', 'DOMContentLoaded handler must be registered');
document.ready();

function statuses() {
  return Object.fromEntries(context.NODES.map(node => [node.id, node.status]));
}

test('scenario buttons use listeners rather than inline handlers', () => {
  for (const id of ['btn-base', 'btn-fals', 'btn-self', 'langBtn']) {
    assert.ok(getElementById(id).listeners.click?.length, id + ' must have a click listener');
  }
});

test('contested evidence blocks dependent nodes but leaves the separate observation intact', () => {
  getElementById('btn-fals').listeners.click[0]();
  const state = statuses();
  assert.equal(state.N2, 'SIMULATED_CONTESTED');
  assert.equal(state.N3, 'SIMULATED_SUPPORTED');
  assert.equal(state.N4, 'BLOCKED');
  assert.equal(state.N5, 'BLOCKED');
});

test('an unverified hypothesis suspends synthesis and blocks the proposed action', () => {
  getElementById('btn-self').listeners.click[0]();
  const state = statuses();
  assert.equal(state.N2, 'SIMULATED_SUPPORTED');
  assert.equal(state.N3, 'UNVERIFIED_HYPOTHESIS');
  assert.equal(state.N4, 'SUSPENDED');
  assert.equal(state.N5, 'BLOCKED');
});

test('baseline restores all statuses instead of retaining stale scenario state', () => {
  getElementById('btn-base').listeners.click[0]();
  const state = statuses();
  assert.equal(state.N1, 'RECORDED');
  assert.equal(state.N2, 'SIMULATED_SUPPORTED');
  assert.equal(state.N3, 'SIMULATED_SUPPORTED');
  assert.equal(state.N4, 'SIMULATED_SUPPORTED');
  assert.equal(state.N5, 'SIMULATED_READY');
});

test('SVG nodes are keyboard-operable with Enter and Space', () => {
  const n3 = svg.nodeElements.find(node => node.dataId === 'N3');
  assert.ok(n3?.listeners.keydown?.length, 'node must have keydown listener');
  let prevented = false;
  n3.listeners.keydown[0].call(n3, { key: 'Enter', preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(context.selectedNodeId, 'N3');
});


test('replacement retains focus on the same logical node on Enter and Space, not the detached node', () => {
  for (const language of ['fa', 'en']) {
    context.setLang(language);
    for (const key of ['Enter', ' ']) {
      const prior = svg.nodeElements.find(node => node.dataId === 'N1');
      prior.focus();
      let prevented = false;
      prior.listeners.keydown[0].call(prior, {key, preventDefault() { prevented = true; }});
      const current = svg.nodeElements.find(node => node.dataId === 'N1');
      assert.ok(prevented);
      assert.notEqual(current, prior);
      assert.equal(document.activeElement, current);
      assert.equal(context.selectedNodeId, 'N1');
      assert.deepEqual(svg.nodeElements.filter(n => n.getAttribute('aria-pressed') === 'true').map(n => n.dataId), ['N1']);
    }
  }
});

test('scenario selection does not steal focus; exactly one scenario and node are pressed', () => {
  for (const [scenario, selected] of [['base', 'N4'], ['fals', 'N2'], ['self', 'N3']]) {
    const button = getElementById('btn-' + scenario);
    button.focus();
    button.listeners.click[0]();
    assert.equal(document.activeElement, button);
    assert.deepEqual(document.querySelectorAll('.scen-btn').filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.id), [button.id]);
    assert.deepEqual(svg.nodeElements.filter(n => n.getAttribute('aria-pressed') === 'true').map(n => n.dataId), [selected]);
  }
});

test('graph name follows language and language button keeps focus', () => {
  const button = getElementById('langBtn');
  button.focus();
  context.setLang('fa');
  assert.equal(svg.getAttribute('aria-label'), 'گراف ساختگی وابستگی شواهد');
  button.listeners.click[0]();
  assert.equal(svg.getAttribute('aria-label'), 'Synthetic evidence dependency graph');
  assert.equal(document.activeElement, button);
});
