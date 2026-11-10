// Run with: node --test tests/*.test.js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../docs/assets/js/maps.js'), 'utf8');
const markup = fs.readFileSync(path.join(__dirname, '../docs/maps/index.html'), 'utf8');

// Exercise the production file reader without depending on a browser or boundary downloads.
function reader({ contents, storageError, readError } = {}) {
  const calls = { writes: [], cleared: [], reloads: 0, status: '' };
  const context = {
    FileReader: function () {
      this.readAsText = function () {
        if (readError) return this.onerror();
        this.result = contents;
        this.onload();
      };
    },
    localStorage: { setItem(key, value) {
      if (storageError) throw new Error('Storage unavailable');
      calls.writes.push({ key, value });
    } },
    location: { reload() { calls.reloads++; } },
    setStatus(message) { calls.status = message; },
    clearTimeout(timer) { calls.cleared.push(timer); },
    STORE_KEY: 'igd-mapmaker-v1', saveTimer: 12, renderTimer: 34
  };
  vm.createContext(context);
  const start = source.indexOf('  function openProject(file) {');
  const end = source.indexOf("  $('openProject').addEventListener", start);
  assert.ok(start !== -1 && end > start);
  vm.runInContext(source.slice(start, end), context);
  context.openProject({ name: 'saved.mapmaker.json' });
  return calls;
}

test('project import preserves settings and data and cancels pending autosaves', () => {
  const project = { app: 'india-map-maker', version: 1, settings: { level: 'districts', labelColour: '#123456' },
    region: { state: '29', district: '' }, values: { districts: { 1: 10 } } };
  const calls = reader({ contents: JSON.stringify(project) });
  assert.deepEqual(JSON.parse(calls.writes[0].value), project);
  assert.equal(calls.writes[0].key, 'igd-mapmaker-v1');
  assert.deepEqual(calls.cleared, [12, 34]);
  assert.equal(calls.reloads, 1);
});

for (const contents of ['{}', 'null', '{invalid']) {
  test('invalid project leaves the current saved map untouched: ' + contents, () => {
    const calls = reader({ contents });
    assert.equal(calls.writes.length, 0);
    assert.equal(calls.reloads, 0);
    assert.equal(calls.cleared.length, 0);
    assert.ok(calls.status);
  });
}

test('storage failure reports the problem without reloading or cancelling autosave', () => {
  const calls = reader({ contents: '{"app":"india-map-maker","version":1}', storageError: true });
  assert.match(calls.status, /Storage unavailable/);
  assert.equal(calls.reloads, 0);
  assert.equal(calls.cleared.length, 0);
});

test('file read errors are reported without replacing the map', () => {
  const calls = reader({ readError: true });
  assert.match(calls.status, /Could not read/);
  assert.equal(calls.writes.length, 0);
  assert.equal(calls.reloads, 0);
});

test('Open project uses its own JSON picker and supports reopening the same file', () => {
  assert.match(markup, /id="openProject"[^>]*>Open project/);
  assert.match(markup, /id="projectInput" accept="\.json,application\/json"/);
  const events = {};
  const input = { files: [], value: '', addEventListener(type, fn) { events[type] = fn; }, click() { this.clicked = true; } };
  const button = { addEventListener(type, fn) { events['button-' + type] = fn; } };
  const opened = [];
  const start = source.indexOf("  $('openProject').addEventListener");
  const end = source.indexOf("  document.querySelectorAll('[data-export]')", start);
  vm.runInNewContext(source.slice(start, end), { $: id => id === 'projectInput' ? input : button, openProject: file => opened.push(file) });
  events['button-click']();
  assert.equal(input.clicked, true);
  events.change.call(input);
  assert.equal(opened.length, 0, 'cancel is harmless');
  const file = { name: 'saved.mapmaker.json' };
  for (let i = 0; i < 2; i++) {
    input.files = [file]; input.value = file.name;
    events.change.call(input);
    assert.equal(input.value, '');
  }
  assert.deepEqual(opened, [file, file]);
});
