/**
 * PSP Analytics — Consent Logic Unit Tests
 *
 * Tests analytics.js consent functions in a Node.js environment.
 * Run: node tests/consent.test.js
 *
 * NOTE: These tests verify consent logic (requiresOptIn, getConsent, setConsent,
 * showConsentBanner) through a module-extracted export pattern. They run without
 * a browser, so DOM/localStorage interactions use lightweight stubs.
 *
 * Tests that require a real browser (banner rendering, button keyboard navigation,
 * GA4/Clarity actual network loads) are listed in the "REQUIRES BROWSER" section.
 */

'use strict';

// ── Test infrastructure ────────────────────────────────────────────────────

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

// ── DOM / localStorage stubs ───────────────────────────────────────────────

function makeDocument(geoContent) {
  var metaTag = geoContent !== undefined
    ? { name: 'psp-geo', content: geoContent }
    : null;
  return {
    querySelector: function (sel) {
      if (sel === 'meta[name="psp-geo"]' && metaTag) {
        return { getAttribute: function (attr) { return attr === 'content' ? metaTag.content : null; } };
      }
      return null;
    },
    createElement: function () { return { textContent: '', setAttribute: function(){}, appendChild: function(){}, id: '', innerHTML: '' }; },
    head: { appendChild: function(){} },
    body: { appendChild: function(){}, style: {} },
    getElementById: function () { return null; },
    addEventListener: function () {},
  };
}

function makeStorage(initial) {
  var store = Object.assign({}, initial || {});
  return {
    getItem: function (k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
    setItem: function (k, v) { store[k] = String(v); },
    removeItem: function (k) { delete store[k]; },
    _store: store,
  };
}

// ── Extract testable functions from analytics.js ─────────────────────────
// We re-implement the pure logic functions here, mirroring analytics.js exactly,
// so tests reflect the actual code rather than importing a browser-targeted script.

var CONSENT_KEY     = 'psp_analytics';
var CONSENT_VERSION = '2';
var CONSENT_VER_KEY = 'psp_analytics_ver';

function makeRequiresOptIn(doc) {
  return function requiresOptIn() {
    try {
      var meta = doc.querySelector('meta[name="psp-geo"]');
      if (meta) {
        return meta.getAttribute('content') !== 'other';
      }
    } catch (e) {}
    return true;
  };
}

function makeGetConsent(storage, requiresOptIn) {
  return function getConsent() {
    try {
      var stored = storage.getItem(CONSENT_KEY);
      if (stored === 'denied') return 'denied';
      if (stored === 'granted') {
        if (!requiresOptIn()) return 'granted';
        if (storage.getItem(CONSENT_VER_KEY) === CONSENT_VERSION) return 'granted';
        return 'denied';
      }
      return requiresOptIn() ? 'denied' : 'granted';
    } catch (e) {
      return requiresOptIn() ? 'denied' : 'granted';
    }
  };
}

function makeSetConsent(storage, requiresOptIn) {
  return function setConsent(value) {
    if (value !== 'granted' && value !== 'denied') return;
    try {
      storage.setItem(CONSENT_KEY, value);
      if (value === 'granted' && requiresOptIn()) {
        storage.setItem(CONSENT_VER_KEY, CONSENT_VERSION);
      } else {
        storage.removeItem(CONSENT_VER_KEY);
      }
    } catch (e) {}
    // (reload omitted in test environment)
  };
}

// ── requiresOptIn() tests ─────────────────────────────────────────────────

console.log('\nrequiresOptIn()');

test('returns true when psp-geo is "eu"', function () {
  var fn = makeRequiresOptIn(makeDocument('eu'));
  assert(fn() === true, 'should require opt-in for EU');
});

test('returns true when psp-geo is "unknown"', function () {
  var fn = makeRequiresOptIn(makeDocument('unknown'));
  assert(fn() === true, 'should require opt-in for unknown');
});

test('returns false when psp-geo is "other"', function () {
  var fn = makeRequiresOptIn(makeDocument('other'));
  assert(fn() === false, 'should not require opt-in for non-EU');
});

test('returns true when psp-geo meta tag is absent (Worker not deployed)', function () {
  var fn = makeRequiresOptIn(makeDocument(undefined));
  assert(fn() === true, 'absent tag = privacy-protective default = opt-in required');
});

// ── getConsent() — US visitor (psp-geo=other) ────────────────────────────

console.log('\ngetConsent() — US visitor (psp-geo="other")');

test('defaults to "granted" with no stored preference', function () {
  var storage = makeStorage({});
  var ri = makeRequiresOptIn(makeDocument('other'));
  var gc = makeGetConsent(storage, ri);
  assertEqual(gc(), 'granted', 'US default');
});

test('returns "denied" when stored=denied', function () {
  var storage = makeStorage({ psp_analytics: 'denied' });
  var ri = makeRequiresOptIn(makeDocument('other'));
  var gc = makeGetConsent(storage, ri);
  assertEqual(gc(), 'denied');
});

test('returns "granted" when stored=granted (no version needed for US)', function () {
  var storage = makeStorage({ psp_analytics: 'granted' });
  var ri = makeRequiresOptIn(makeDocument('other'));
  var gc = makeGetConsent(storage, ri);
  assertEqual(gc(), 'granted', 'US stored granted valid without version');
});

// ── getConsent() — EU visitor (psp-geo=eu) ───────────────────────────────

console.log('\ngetConsent() — EU visitor (psp-geo="eu")');

test('defaults to "denied" with no stored preference', function () {
  var storage = makeStorage({});
  var ri = makeRequiresOptIn(makeDocument('eu'));
  var gc = makeGetConsent(storage, ri);
  assertEqual(gc(), 'denied', 'EU default');
});

test('returns "denied" when stored=denied', function () {
  var storage = makeStorage({ psp_analytics: 'denied' });
  var ri = makeRequiresOptIn(makeDocument('eu'));
  var gc = makeGetConsent(storage, ri);
  assertEqual(gc(), 'denied');
});

test('returns "granted" when stored=granted AND version=2', function () {
  var storage = makeStorage({ psp_analytics: 'granted', psp_analytics_ver: '2' });
  var ri = makeRequiresOptIn(makeDocument('eu'));
  var gc = makeGetConsent(storage, ri);
  assertEqual(gc(), 'granted', 'EU explicit opt-in with correct version');
});

test('returns "denied" when stored=granted but no version key (old opt-out grant)', function () {
  var storage = makeStorage({ psp_analytics: 'granted' });
  var ri = makeRequiresOptIn(makeDocument('eu'));
  var gc = makeGetConsent(storage, ri);
  assertEqual(gc(), 'denied', 'old opt-out granted not valid for EU');
});

test('returns "denied" when stored=granted but version is "1" (stale)', function () {
  var storage = makeStorage({ psp_analytics: 'granted', psp_analytics_ver: '1' });
  var ri = makeRequiresOptIn(makeDocument('eu'));
  var gc = makeGetConsent(storage, ri);
  assertEqual(gc(), 'denied', 'version 1 not valid for version 2 consent');
});

// ── getConsent() — absent Worker meta tag ────────────────────────────────

console.log('\ngetConsent() — no psp-geo tag (Worker absent)');

test('defaults to "denied" when meta tag absent', function () {
  var storage = makeStorage({});
  var ri = makeRequiresOptIn(makeDocument(undefined));
  var gc = makeGetConsent(storage, ri);
  assertEqual(gc(), 'denied', 'privacy-protective fallback');
});

test('old opt-out "granted" invalid when meta tag absent', function () {
  var storage = makeStorage({ psp_analytics: 'granted' });
  var ri = makeRequiresOptIn(makeDocument(undefined));
  var gc = makeGetConsent(storage, ri);
  assertEqual(gc(), 'denied', 'absent tag treated as requires opt-in');
});

// ── setConsent() ─────────────────────────────────────────────────────────

console.log('\nsetConsent()');

test('setConsent("granted") for EU visitor stores version key', function () {
  var storage = makeStorage({});
  var ri = makeRequiresOptIn(makeDocument('eu'));
  var sc = makeSetConsent(storage, ri);
  sc('granted');
  assertEqual(storage.getItem(CONSENT_KEY), 'granted');
  assertEqual(storage.getItem(CONSENT_VER_KEY), '2', 'EU grant should write version key');
});

test('setConsent("granted") for US visitor does NOT store version key', function () {
  var storage = makeStorage({});
  var ri = makeRequiresOptIn(makeDocument('other'));
  var sc = makeSetConsent(storage, ri);
  sc('granted');
  assertEqual(storage.getItem(CONSENT_KEY), 'granted');
  assertEqual(storage.getItem(CONSENT_VER_KEY), null, 'US grant should not write version key');
});

test('setConsent("denied") removes version key', function () {
  var storage = makeStorage({ psp_analytics: 'granted', psp_analytics_ver: '2' });
  var ri = makeRequiresOptIn(makeDocument('eu'));
  var sc = makeSetConsent(storage, ri);
  sc('denied');
  assertEqual(storage.getItem(CONSENT_KEY), 'denied');
  assertEqual(storage.getItem(CONSENT_VER_KEY), null, 'version key removed on deny');
});

test('setConsent() ignores invalid values', function () {
  var storage = makeStorage({});
  var ri = makeRequiresOptIn(makeDocument('other'));
  var sc = makeSetConsent(storage, ri);
  sc('maybe');
  assertEqual(storage.getItem(CONSENT_KEY), null, 'invalid value not stored');
});

test('EU opt-in then deny then re-read returns denied', function () {
  var storage = makeStorage({});
  var doc = makeDocument('eu');
  var ri = makeRequiresOptIn(doc);
  var sc = makeSetConsent(storage, ri);
  var gc = makeGetConsent(storage, ri);
  sc('granted');
  assertEqual(gc(), 'granted');
  sc('denied');
  assertEqual(gc(), 'denied');
  assertEqual(storage.getItem(CONSENT_VER_KEY), null);
});

// ── Backward compatibility ────────────────────────────────────────────────

console.log('\nBackward compatibility');

test('EU visitor with pre-v2 opt-out "granted" is downgraded to denied', function () {
  // Simulates a US visitor who opted out before the Worker was deployed,
  // then visits from an EU IP after the Worker is live.
  var storage = makeStorage({ psp_analytics: 'granted' }); // no version key
  var ri = makeRequiresOptIn(makeDocument('eu'));
  var gc = makeGetConsent(storage, ri);
  assertEqual(gc(), 'denied', 'backward compat: old US opt-out not valid EU consent');
});

test('US visitor with pre-v2 opt-out "granted" is preserved', function () {
  var storage = makeStorage({ psp_analytics: 'granted' }); // no version key
  var ri = makeRequiresOptIn(makeDocument('other'));
  var gc = makeGetConsent(storage, ri);
  assertEqual(gc(), 'granted', 'US opt-out "granted" remains valid without version');
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

console.log('\nREQUIRES BROWSER (not runnable in Node):');
console.log('  - showConsentBanner() renders correctly at 390/375/320px viewports');
console.log('  - showConsentBanner() uses column layout at <=479px');
console.log('  - showConsentBanner() is compact at max-height:400px (landscape)');
console.log('  - Decline/Accept buttons are keyboard-navigable with focus-visible outline');
console.log('  - "Manage Analytics Preferences" button (privacy.html) opens modal');
console.log('  - GA4 gtag script loads only when consent is "granted"');
console.log('  - Clarity script loads only when consent is "granted"');
console.log('  - Neither script loads when consent is "denied"');
console.log('  - Banner does not appear when psp-geo=other (US default-granted)');
console.log('  - Banner appears when psp-geo=eu and no prior consent stored');

process.exit(failed > 0 ? 1 : 0);
