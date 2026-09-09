// Contract checks for the map maker's boundary layers and name aliases.
// Run with: node --test tests/
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

const DATA = path.join(__dirname, '..', 'docs', 'maps', 'data');
const Core = require('../docs/assets/js/maps-core.js');

function layer(name) {
  const topo = JSON.parse(fs.readFileSync(path.join(DATA, name + '.topo.json'), 'utf8'));
  return topo.objects[name].geometries;
}
function compact(s) {
  return String(s).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/&/g, ' and ').replace(/\b(district|dist|distt|dt)\b\.?/g, '')
    .replace(/\b(state|u\.?t\.?|union territory|the)\b\.?/g, '').replace(/[^a-z0-9]+/g, '');
}

const REQUIRED = {
  states: ['name', 'lgd', 'census'],
  districts: ['name', 'lgd', 'census', 'state', 'state_lgd'],
  subdistricts: ['name', 'lgd', 'census', 'district', 'dist_lgd', 'state', 'state_lgd'],
  blocks: ['name', 'lgd', 'census', 'district', 'dist_lgd', 'state', 'state_lgd'],
  parliament: ['name', 'lgd', 'census', 'state', 'state_lgd'],
  assembly: ['name', 'lgd', 'census', 'district', 'dist_lgd', 'state', 'state_lgd']
};

for (const name of Object.keys(REQUIRED)) {
  test(`${name}: ids are unique and properties complete`, () => {
    const geoms = layer(name);
    assert.ok(geoms.length > 0);
    const ids = new Set();
    for (const g of geoms) {
      assert.ok(g.id !== undefined && g.id !== null, 'every geometry has an id');
      assert.ok(!ids.has(String(g.id)), `duplicate id ${g.id}`);
      ids.add(String(g.id));
      for (const p of REQUIRED[name]) assert.ok(p in g.properties, `${name} ${g.id} lacks ${p}`);
      assert.ok(String(g.properties.name).trim().length > 0, `${name} ${g.id} has an empty name`);
      assert.ok(!/\*$/.test(g.properties.name), `${name} ${g.id} keeps a stray asterisk`);
    }
  });
}

test('feature counts match the published boundaries', () => {
  assert.strictEqual(layer('states').length, 36);
  assert.strictEqual(layer('districts').length, 785);
  assert.ok(layer('subdistricts').length > 6000);
  assert.strictEqual(layer('parliament').length, 543);
  assert.ok(layer('assembly').length > 4000);
  assert.ok(layer('blocks').length > 7000);
});

test('every alias target is a real state or district name', () => {
  const targets = Object.keys(Core.ALIASES).map(k => Core.ALIASES[k]);
  const known = new Set();
  for (const name of ['states', 'districts']) for (const g of layer(name)) known.add(compact(g.properties.name));
  const missing = [...new Set(targets)].filter(t => !known.has(t));
  assert.deepStrictEqual(missing, [], 'alias targets with no matching region');
});
