// Unit tests for the pure helpers behind name matching and number formatting.
// Run with: node --test tests/
const test = require('node:test');
const assert = require('node:assert');
const Core = require('../docs/assets/js/maps-core.js');

test('compact() normalises names the way regions are indexed', () => {
  assert.strictEqual(Core.compact('Andaman & Nicobar Islands'), 'andamanandnicobarislands');
  assert.strictEqual(Core.compact('Bilaspur District'), 'bilaspur');
  assert.strictEqual(Core.compact('Jammu & Kashmir (UT)'), 'jammuandkashmir');
  assert.strictEqual(Core.compact('  Tamil Nadu state '), 'tamilnadu');
  assert.strictEqual(Core.compact('Chhattīsgarh'), 'chhattisgarh');
});

test('tokenKey() ignores word order', () => {
  assert.strictEqual(Core.tokenKey('North 24 Parganas'), Core.tokenKey('24 Parganas North'));
  assert.notStrictEqual(Core.tokenKey('North Delhi'), Core.tokenKey('South Delhi'));
});

test('aliases resolve common variants', () => {
  assert.strictEqual(Core.ALIASES[Core.compact('Orissa')], 'odisha');
  assert.strictEqual(Core.ALIASES[Core.compact('Kerela')], 'kerala');
  assert.strictEqual(Core.ALIASES[Core.compact('NCT of Delhi')], 'delhi');
  assert.strictEqual(Core.ALIASES[Core.compact('Bangalore Urban')], 'bengaluruurban');
  assert.strictEqual(Core.ALIASES[Core.compact('Twenty Four Parganas North')], '24paraganasnorth');
});

test('similarity() ranks close spellings above unrelated names', () => {
  const s = Core.similarity;
  assert.ok(s('uttarpardesh', 'uttarpradesh') > 0.8);
  assert.ok(s('kerela', 'kerala') > s('kerela', 'karnataka'));
  assert.strictEqual(s('goa', 'goa'), 1);
  assert.ok(s('north', 'north24parganas') < 0.75, 'a short name is not a strong match for a long one');
});

test('levenshtein() rejects very different lengths quickly', () => {
  assert.strictEqual(Core.levenshtein('abc', 'abcdefgh'), 99);
  assert.strictEqual(Core.levenshtein('kerela', 'kerala'), 1);
});

test('toNumber() accepts the ways people write figures', () => {
  assert.strictEqual(Core.toNumber('1,23,456'), 123456);
  assert.strictEqual(Core.toNumber('94%'), 94);
  assert.strictEqual(Core.toNumber('₹ 2,500'), 2500);
  assert.strictEqual(Core.toNumber('Rs. 500'), 500);
  assert.strictEqual(Core.toNumber('(300)'), -300);
  assert.strictEqual(Core.toNumber('−5.5'), -5.5);
  assert.ok(Number.isNaN(Core.toNumber('n/a')));
  assert.ok(Number.isNaN(Core.toNumber('')));
});

test('isEmptyToken() treats placeholders as missing', () => {
  for (const t of ['', ' ', 'NA', 'n/a', 'N.A', 'N.A.', '--', '—', '..', '#N/A', 'nil']) assert.ok(Core.isEmptyToken(t), t);
  assert.ok(!Core.isEmptyToken('0'));
  assert.ok(!Core.isEmptyToken('Nagaland'));
});

test('parseText() handles tabs, commas and typed lines', () => {
  const parsers = {
    tsvParseRows: (s) => s.split('\n').map((l) => l.split('\t')),
    csvParseRows: (s) => s.split('\n').map((l) => l.split(','))
  };
  assert.deepStrictEqual(Core.parseText('Kerala\t94\nBihar\t61', parsers), [['Kerala', '94'], ['Bihar', '61']]);
  assert.deepStrictEqual(Core.parseText('Kerala,94\nBihar,61', parsers), [['Kerala', '94'], ['Bihar', '61']]);
  assert.deepStrictEqual(Core.parseText('Kerala 94\nTamil Nadu 80\nGoa', parsers), [['Kerala', '94'], ['Tamil Nadu', '80'], ['Goa']]);
});

test('fmtNumber() formats Indian, lakh, metric and plain styles', () => {
  assert.strictEqual(Core.fmtNumber(1234567, 0, 'indian'), '12,34,567');
  assert.strictEqual(Core.fmtNumber(99999, 0, 'lakh'), '99,999');
  assert.strictEqual(Core.fmtNumber(12500000, 0, 'lakh'), '1.3 Cr');
  assert.strictEqual(Core.fmtNumber(640000, 1, 'lakh'), '6.4 L');
  assert.strictEqual(Core.fmtNumber(1234567, 0, 'metric'), '1.2M');
  assert.strictEqual(Core.fmtNumber(-1234.5, 1, 'plain'), '-1234.5');
});

test('computeAutoDecimals() separates breaks and keeps a lone value as typed', () => {
  assert.strictEqual(Core.computeAutoDecimals([1, 2, 3]), 0);
  assert.strictEqual(Core.computeAutoDecimals([1.25, 1.5, 1.75], [1.25, 1.5, 1.75]), 1);
  assert.strictEqual(Core.computeAutoDecimals([0.001, 0.002], [0.001, 0.002]), 3);
  assert.strictEqual(Core.computeAutoDecimals([94.25]), 2);
});

test('wrapText() breaks long titles and keeps short ones whole', () => {
  assert.deepStrictEqual(Core.wrapText('Literacy rate', 34, 'sans', 700, 900), ['Literacy rate']);
  const lines = Core.wrapText('A very long title that should wrap onto more than one line for sure', 48, 'sans', 700, 600);
  assert.ok(lines.length >= 3);
  assert.ok(lines.every((l) => l.length <= Math.floor(600 / (48 * 0.52 * 1.07))));
});
