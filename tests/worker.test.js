/**
 * PSP Geo Worker — Unit Tests
 *
 * Tests the Cloudflare Worker logic by extracting its pure functions
 * and running them in Node.js without a Cloudflare runtime.
 *
 * Run: node tests/worker.test.js
 *
 * Tests that require a live Cloudflare Worker deployment are listed
 * in the "REQUIRES DEPLOYED WORKER" section at the bottom.
 */

'use strict';

var passed = 0;
var failed = 0;
var errors = [];

function test(name, fn) {
  try {
    fn();
    passed++;
    process.stdout.write('  PASS  ' + name + '\n');
  } catch (e) {
    failed++;
    errors.push({ name, message: e.message });
    process.stdout.write('  FAIL  ' + name + '\n       ' + e.message + '\n');
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message || 'Assertion failed');
}

function assertEqual(a, b, message) {
  if (a !== b) throw new Error((message || '') + ' — expected ' + JSON.stringify(b) + ', got ' + JSON.stringify(a));
}

// ── Pure region logic (extracted from worker) ─────────────────────────────

var EU_EEA_UK = new Set([
  'AT','BE','BG','CY','CZ','DE','DK','EE','ES','FI',
  'FR','GR','HR','HU','IE','IT','LT','LU','LV','MT',
  'NL','PL','PT','RO','SE','SI','SK',
  'IS','LI','NO',
  'GB','GG','JE','IM',
]);

function getRegion(country) {
  if (EU_EEA_UK.has(country)) return 'eu';
  if (country === '') return 'unknown';
  return 'other';
}

// ── EU member states ──────────────────────────────────────────────────────

console.log('\nEU member states → "eu"');

[
  ['AT', 'Austria'], ['BE', 'Belgium'], ['DE', 'Germany'], ['FR', 'France'],
  ['ES', 'Spain'],   ['IT', 'Italy'],   ['NL', 'Netherlands'], ['PL', 'Poland'],
  ['SE', 'Sweden'],  ['IE', 'Ireland'], ['PT', 'Portugal'],
].forEach(function (pair) {
  test(pair[1] + ' (' + pair[0] + ') is EU', function () {
    assertEqual(getRegion(pair[0]), 'eu', pair[0]);
  });
});

// ── EEA non-EU ────────────────────────────────────────────────────────────

console.log('\nEEA non-EU → "eu"');

test('Norway (NO) is EEA', function () { assertEqual(getRegion('NO'), 'eu'); });
test('Iceland (IS) is EEA', function () { assertEqual(getRegion('IS'), 'eu'); });
test('Liechtenstein (LI) is EEA', function () { assertEqual(getRegion('LI'), 'eu'); });

// ── UK and Crown Dependencies ─────────────────────────────────────────────

console.log('\nUK and Crown Dependencies → "eu"');

test('United Kingdom (GB) is UK', function () { assertEqual(getRegion('GB'), 'eu'); });
test('Guernsey (GG) is Crown Dependency', function () { assertEqual(getRegion('GG'), 'eu'); });
test('Jersey (JE) is Crown Dependency', function () { assertEqual(getRegion('JE'), 'eu'); });
test('Isle of Man (IM) is Crown Dependency', function () { assertEqual(getRegion('IM'), 'eu'); });

// ── Non-EU countries → "other" ────────────────────────────────────────────

console.log('\nNon-EU countries → "other"');

test('United States (US) is other', function () { assertEqual(getRegion('US'), 'other'); });
test('Canada (CA) is other', function () { assertEqual(getRegion('CA'), 'other'); });
test('Australia (AU) is other', function () { assertEqual(getRegion('AU'), 'other'); });
test('Japan (JP) is other', function () { assertEqual(getRegion('JP'), 'other'); });
test('Brazil (BR) is other', function () { assertEqual(getRegion('BR'), 'other'); });

// ── Unknown / empty country ───────────────────────────────────────────────

console.log('\nEmpty country string → "unknown"');

test('empty string returns "unknown"', function () { assertEqual(getRegion(''), 'unknown'); });

// ── Edge cases ────────────────────────────────────────────────────────────

console.log('\nEdge cases');

test('lowercase country code is not matched (case-sensitive)', function () {
  // Cloudflare always provides uppercase; this confirms the Set uses uppercase keys
  assertEqual(getRegion('us'), 'other', 'lowercase us should be "other" not "eu"');
  assertEqual(getRegion('de'), 'other', 'lowercase de should be "other" not "eu"');
});

test('CH (Switzerland) is not EU/EEA', function () {
  assertEqual(getRegion('CH'), 'other');
});

test('RU (Russia) is not EU/EEA', function () {
  assertEqual(getRegion('RU'), 'other');
});

// ── Summary ───────────────────────────────────────────────────────────────

console.log('\n─────────────────────────────────────────────');
console.log('Results: ' + passed + ' passed, ' + failed + ' failed');

if (errors.length) {
  console.log('\nFailed tests:');
  errors.forEach(function (e) {
    console.log('  ' + e.name + ': ' + e.message);
  });
}

console.log('\nREQUIRES DEPLOYED WORKER:');
console.log('  - HTML response contains <meta name="psp-geo" content="other"> for US IP');
console.log('  - HTML response contains <meta name="psp-geo" content="eu"> for EU IP (use VPN)');
console.log('  - Non-HTML response (CSS, JS, image) is passed through without modification');
console.log('  - Worker failure (simulated by disabling Worker) → origin page loads without meta tag');
console.log('  - analytics.js reads absent meta tag → requiresOptIn() returns true');
console.log('  - Worker handles fetch() error → origin fallback, no Cloudflare 1101 error page');

process.exit(failed > 0 ? 1 : 0);
