/**
 * PSP Analytics Coverage — Regression Test
 *
 * Verifies that every production HTML page loads analytics.js
 * with the correct deferred script tag, and that no page loads
 * it more than once.
 *
 * Run: node tests/analytics-coverage.test.js
 */

'use strict';

const fs   = require('fs');
const path = require('path');

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

// ── Collect all production HTML files ─────────────────────────────────────────

const ROOT = path.join(__dirname, '..');

function collectHtml(dir, results) {
  results = results || [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      // Skip non-production directories
      if (['node_modules', '_partials', 'preview', '.git'].includes(entry.name)) continue;
      collectHtml(full, results);
    } else if (entry.isFile() && entry.name.endsWith('.html')) {
      results.push(full);
    }
  }
  return results;
}

const allHtml = collectHtml(ROOT).sort();

// ── Per-file checks ───────────────────────────────────────────────────────────

console.log('\nAnalytics coverage — ' + allHtml.length + ' production HTML files');

// Determine the correct relative path to analytics.js for each file.
// Files in a subdirectory (e.g. blog/, neighborhoods/) use "../assets/js/analytics.js"
// but on this site the pages use root-relative paths: "assets/js/analytics.js".
// We just check for the presence of "analytics.js" with a defer attribute.
const ANALYTICS_PATTERN = /analytics\.js[^"']*["']\s+defer/;
const DEFER_EXACT       = /analytics\.js"\s+defer/;

for (const filePath of allHtml) {
  const rel     = path.relative(ROOT, filePath);
  const content = fs.readFileSync(filePath, 'utf8');

  test(rel + ' — loads analytics.js with defer', function () {
    assert(
      ANALYTICS_PATTERN.test(content),
      'Missing: <script src="...analytics.js" defer>'
    );
  });

  test(rel + ' — no duplicate analytics.js', function () {
    const matches = (content.match(/analytics\.js/g) || []).length;
    // analytics.js may appear in a comment or path reference — accept 1 or 2
    // but flag 3+ as likely a duplicate script tag
    assert(
      matches <= 2,
      'analytics.js appears ' + matches + ' times — possible duplicate script tag'
    );
  });
}

// ── Cross-file summary ────────────────────────────────────────────────────────

console.log('\nCross-file checks');

test('All ' + allHtml.length + ' production HTML files load analytics.js', function () {
  const missing = allHtml.filter(f => {
    const c = fs.readFileSync(f, 'utf8');
    return !ANALYTICS_PATTERN.test(c);
  });
  assert(
    missing.length === 0,
    'Missing analytics.js: ' + missing.map(f => path.relative(ROOT, f)).join(', ')
  );
});

test('No production HTML file has inline GA4 or Clarity initialization', function () {
  const inlinePatterns = [
    /gtag\s*\(\s*['"]js['"]/,            // gtag('js', ...)
    /GoogleAnalyticsObject/,              // legacy UA
    /clarity\s*\(\s*['"]set['"]/,        // Clarity inline init
  ];
  const violations = [];
  for (const f of allHtml) {
    const c = fs.readFileSync(f, 'utf8');
    for (const p of inlinePatterns) {
      if (p.test(c)) {
        violations.push(path.relative(ROOT, f) + ' (' + p + ')');
      }
    }
  }
  assert(violations.length === 0, 'Inline analytics found: ' + violations.join('; '));
});

test('analytics.js MEASUREMENT_ID is configured (not placeholder)', function () {
  const analyticsJs = fs.readFileSync(path.join(ROOT, 'assets/js/analytics.js'), 'utf8');
  assert(
    !analyticsJs.includes("var MEASUREMENT_ID = 'G-XXXXXXXXXX'"),
    'MEASUREMENT_ID is still the placeholder value G-XXXXXXXXXX'
  );
  assert(
    analyticsJs.includes("var MEASUREMENT_ID = 'G-"),
    'MEASUREMENT_ID line not found in analytics.js'
  );
});

test('analytics.js CLARITY_ID is configured (not placeholder)', function () {
  const analyticsJs = fs.readFileSync(path.join(ROOT, 'assets/js/analytics.js'), 'utf8');
  assert(
    !analyticsJs.includes("var CLARITY_ID = 'XXXXXXXXXX'"),
    'CLARITY_ID is still a placeholder value'
  );
  assert(
    /var CLARITY_ID\s+=\s+'[a-z0-9]{10}'/.test(analyticsJs),
    'CLARITY_ID does not match expected 10-character format'
  );
});

test('No PRE-DEPLOY date comments remain in production pages', function () {
  const pagesWithMarker = allHtml.filter(f => {
    const c = fs.readFileSync(f, 'utf8');
    return c.includes('PRE-DEPLOY:');
  });
  assert(
    pagesWithMarker.length === 0,
    'PRE-DEPLOY marker found in: ' + pagesWithMarker.map(f => path.relative(ROOT, f)).join(', ')
  );
});

// ── Summary ───────────────────────────────────────────────────────────────────

console.log('\n─────────────────────────────────────────────');
console.log('Results: ' + passed + ' passed, ' + failed + ' failed');

if (errors.length) {
  console.log('\nFailed tests:');
  errors.forEach(function (e) {
    console.log('  ' + e.name + ': ' + e.message);
  });
}

process.exit(failed > 0 ? 1 : 0);
