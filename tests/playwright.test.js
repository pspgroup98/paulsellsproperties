/**
 * PSP Phase 11 — Playwright Browser Tests
 *
 * Tests consent banner rendering, responsive layout, accessibility,
 * and analytics gating across viewports.
 *
 * Run: node tests/playwright.test.js
 * (starts a local static file server, runs tests, shuts down)
 *
 * Tests that require a live deployed Worker are listed at the end
 * under "REQUIRES DEPLOYED WORKER".
 */

'use strict';

const http  = require('http');
const fs    = require('fs');
const path  = require('path');
const { chromium } = require('@playwright/test');

// ── Static file server ────────────────────────────────────────────────────────

const ROOT = path.join(__dirname, '..');
const PORT = 7777;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css':  'text/css',
  '.js':   'application/javascript',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.webp': 'image/webp',
  '.woff2':'font/woff2',
  '.woff': 'font/woff',
};

const server = http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0];
  if (urlPath === '/') urlPath = '/index.html';
  if (!urlPath.includes('.')) urlPath += '.html';

  const filePath = path.join(ROOT, urlPath);
  const ext = path.extname(filePath);

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end('Not found: ' + urlPath);
      return;
    }
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(data);
  });
});

// ── Test infrastructure ────────────────────────────────────────────────────────

let passed = 0;
let failed = 0;
const errors = [];

async function test(name, fn) {
  try {
    await fn();
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

const BASE = `http://localhost:${PORT}`;

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Open a page with a given psp-geo meta tag value injected via URL param.
 * We can't run a Cloudflare Worker locally, so we inject via a script that
 * overrides the meta tag before analytics.js reads it.
 */
async function openWithGeo(page, pagePath, geo) {
  // Inject the meta tag override before analytics.js runs by using
  // page.addInitScript — this runs before any page scripts.
  await page.addInitScript((geoValue) => {
    // Override querySelector to intercept the meta[name="psp-geo"] call
    const origQS = document.querySelector.bind(document);
    document.querySelector = function (sel) {
      if (sel === 'meta[name="psp-geo"]') {
        const fakeEl = { getAttribute: (attr) => attr === 'content' ? geoValue : null };
        return fakeEl;
      }
      return origQS(sel);
    };
  }, geo);

  await page.goto(BASE + pagePath, { waitUntil: 'domcontentloaded' });
}

async function openWithNoGeo(page, pagePath) {
  // No override — simulates Worker absent (no meta tag)
  await page.goto(BASE + pagePath, { waitUntil: 'domcontentloaded' });
}

async function clearStorage(page) {
  await page.evaluate(() => localStorage.clear());
}

// ── Responsive layout tests ───────────────────────────────────────────────────

async function runResponsiveTests(browser) {
  console.log('\nResponsive layout — 404.html');

  const viewports = [
    { name: '1440px desktop', width: 1440, height: 900 },
    { name: '768px tablet',   width: 768,  height: 1024 },
    { name: '390px mobile',   width: 390,  height: 844 },
    { name: '320px narrow',   width: 320,  height: 568 },
  ];

  for (const vp of viewports) {
    const ctx  = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
    const page = await ctx.newPage();
    await page.goto(BASE + '/404', { waitUntil: 'domcontentloaded' });

    await test(`404.html renders without horizontal scroll at ${vp.name}`, async () => {
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
      assert(scrollWidth <= clientWidth,
        `scrollWidth ${scrollWidth} > clientWidth ${clientWidth} at ${vp.width}px`);
    });

    await test(`404.html h1 is visible at ${vp.name}`, async () => {
      const h1 = page.locator('h1');
      await h1.waitFor({ state: 'visible' });
      const text = await h1.textContent();
      assert(text && text.length > 0, 'h1 has no text');
    });

    await ctx.close();
  }

  // Mobile landscape
  const ctxLandscape = await browser.newContext({ viewport: { width: 667, height: 375 } });
  const pageLandscape = await ctxLandscape.newPage();
  await pageLandscape.goto(BASE + '/404', { waitUntil: 'domcontentloaded' });
  await test('404.html renders without horizontal scroll at mobile landscape (667×375)', async () => {
    const sw = await pageLandscape.evaluate(() => document.documentElement.scrollWidth);
    const cw = await pageLandscape.evaluate(() => document.documentElement.clientWidth);
    assert(sw <= cw, `scrollWidth ${sw} > clientWidth ${cw}`);
  });
  await ctxLandscape.close();
}

// ── Consent banner tests ───────────────────────────────────────────────────────

async function runConsentBannerTests(browser) {
  console.log('\nConsent banner — EU visitor (psp-geo="eu")');

  const ctx  = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();

  // EU visitor, no prior consent → banner should appear
  await openWithGeo(page, '/404', 'eu');
  await page.waitForTimeout(300);

  await test('banner appears for EU visitor with no prior consent', async () => {
    const banner = page.locator('#psp-consent-banner');
    const visible = await banner.isVisible();
    assert(visible, 'consent banner should be visible for EU visitor');
  });

  await test('banner has Accept and Decline buttons', async () => {
    const accept  = page.locator('#psp-consent-accept');
    const decline = page.locator('#psp-consent-decline');
    assert(await accept.isVisible(),  'Accept button not visible');
    assert(await decline.isVisible(), 'Decline button not visible');
  });

  await test('banner has role="region" and aria-label', async () => {
    const role  = await page.locator('#psp-consent-banner').getAttribute('role');
    const label = await page.locator('#psp-consent-banner').getAttribute('aria-label');
    assert(role  === 'region',           `expected role="region", got "${role}"`);
    assert(label && label.length > 0,    'aria-label is missing or empty');
  });

  await test('Accept and Decline buttons have type="button"', async () => {
    const acceptType  = await page.locator('#psp-consent-accept').getAttribute('type');
    const declineType = await page.locator('#psp-consent-decline').getAttribute('type');
    assert(acceptType  === 'button', `accept type="${acceptType}"`);
    assert(declineType === 'button', `decline type="${declineType}"`);
  });

  await ctx.close();

  // US visitor — banner should NOT appear (default granted, no consent needed)
  console.log('\nConsent banner — US visitor (psp-geo="other")');
  const ctxUS  = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const pageUS = await ctxUS.newPage();
  await openWithGeo(pageUS, '/404', 'other');
  await pageUS.waitForTimeout(300);

  await test('banner does NOT appear for US visitor (default granted)', async () => {
    const banner = pageUS.locator('#psp-consent-banner');
    const visible = await banner.isVisible().catch(() => false);
    assert(!visible, 'banner should be hidden for US visitor with no prior consent');
  });

  await ctxUS.close();
}

// ── Consent action tests ───────────────────────────────────────────────────────

async function runConsentActionTests(browser) {
  console.log('\nConsent actions — Accept / Decline / returning visitor');

  // Decline flow
  const ctxDecline = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pageDecline = await ctxDecline.newPage();
  await openWithGeo(pageDecline, '/404', 'eu');
  await pageDecline.waitForTimeout(300);

  let navigationOccurred = false;
  pageDecline.on('load', () => { navigationOccurred = true; });

  await test('clicking Decline stores "denied" in localStorage', async () => {
    const btn = pageDecline.locator('#psp-consent-decline');
    // Click triggers setConsent() which writes localStorage then calls reload().
    // Catch the reload-triggered navigation, then read localStorage after.
    const [_] = await Promise.all([
      pageDecline.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 5000 }).catch(() => null),
      btn.click(),
    ]);
    const stored = await pageDecline.evaluate(() => localStorage.getItem('psp_analytics'));
    assert(stored === 'denied', `expected "denied", got "${stored}"`);
  });

  await ctxDecline.close();

  // Accept flow
  const ctxAccept = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pageAccept = await ctxAccept.newPage();
  await openWithGeo(pageAccept, '/404', 'eu');
  await pageAccept.waitForTimeout(300);

  await test('clicking Accept stores "granted" with version key in localStorage (EU)', async () => {
    const btn = pageAccept.locator('#psp-consent-accept');
    // Click triggers reload; wait for navigation then read localStorage
    const [_] = await Promise.all([
      pageAccept.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 5000 }).catch(() => null),
      btn.click(),
    ]);
    const stored    = await pageAccept.evaluate(() => localStorage.getItem('psp_analytics'));
    const verStored = await pageAccept.evaluate(() => localStorage.getItem('psp_analytics_ver'));
    assert(stored === 'granted',    `expected "granted", got "${stored}"`);
    assert(verStored === '2',       `expected version "2", got "${verStored}"`);
  });

  await ctxAccept.close();

  // Returning EU visitor who previously accepted → banner should NOT appear
  const ctxReturn = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    storageState: {
      origins: [{
        origin: BASE,
        localStorage: [
          { name: 'psp_analytics',     value: 'granted' },
          { name: 'psp_analytics_ver', value: '2' },
        ],
      }],
    },
  });
  const pageReturn = await ctxReturn.newPage();
  await openWithGeo(pageReturn, '/404', 'eu');
  await pageReturn.waitForTimeout(300);

  await test('returning EU visitor (prev accepted) does not see banner', async () => {
    const banner = pageReturn.locator('#psp-consent-banner');
    const visible = await banner.isVisible().catch(() => false);
    assert(!visible, 'banner should not appear for returning EU visitor who accepted');
  });

  await ctxReturn.close();

  // Returning EU visitor who previously declined → banner should NOT appear
  const ctxDenied = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    storageState: {
      origins: [{
        origin: BASE,
        localStorage: [
          { name: 'psp_analytics', value: 'denied' },
        ],
      }],
    },
  });
  const pageDenied = await ctxDenied.newPage();
  await openWithGeo(pageDenied, '/404', 'eu');
  await pageDenied.waitForTimeout(300);

  await test('returning EU visitor (prev declined) does not see banner', async () => {
    const banner = pageDenied.locator('#psp-consent-banner');
    const visible = await banner.isVisible().catch(() => false);
    assert(!visible, 'banner should not reappear for returning EU visitor who declined');
  });

  await ctxDenied.close();
}

// ── Analytics gating tests ────────────────────────────────────────────────────

async function runAnalyticsGatingTests(browser) {
  console.log('\nAnalytics gating — GA4/Clarity only load when consent granted');

  // EU visitor, denied → no GA4 or Clarity scripts
  const ctxDenied = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pageDenied = await ctxDenied.newPage();

  const networkRequests = [];
  pageDenied.on('request', req => networkRequests.push(req.url()));

  await openWithGeo(pageDenied, '/404', 'eu'); // No prior consent = denied for EU
  await pageDenied.waitForTimeout(500);

  await test('GA4 gtag script does NOT load when consent is denied (EU, no prior consent)', async () => {
    const ga4Loaded = networkRequests.some(url =>
      url.includes('googletagmanager.com') || url.includes('google-analytics.com')
    );
    assert(!ga4Loaded, 'GA4 script loaded despite consent being denied');
  });

  await test('Microsoft Clarity does NOT load when consent is denied', async () => {
    const clarityLoaded = networkRequests.some(url =>
      url.includes('clarity.ms') || url.includes('c.bing.com')
    );
    assert(!clarityLoaded, 'Clarity script loaded despite consent being denied');
  });

  await ctxDenied.close();

  // US visitor, default granted → GA4 and Clarity should load
  const ctxGranted = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pageGranted = await ctxGranted.newPage();

  const grantedRequests = [];
  pageGranted.on('request', req => grantedRequests.push(req.url()));

  await openWithGeo(pageGranted, '/404', 'other'); // US = default granted
  await pageGranted.waitForTimeout(1000);

  await test('GA4 gtag script loads when consent is granted (US default)', async () => {
    const ga4Loaded = grantedRequests.some(url =>
      url.includes('googletagmanager.com') || url.includes('google-analytics.com')
    );
    assert(ga4Loaded, 'GA4 script did not load for US visitor (expected default-granted)');
  });

  await test('Microsoft Clarity loads when consent is granted (US default)', async () => {
    const clarityLoaded = grantedRequests.some(url =>
      url.includes('clarity.ms') || url.includes('c.bing.com')
    );
    assert(clarityLoaded, 'Clarity did not load for US visitor (expected default-granted)');
  });

  await ctxGranted.close();
}

// ── Privacy page preferences modal ────────────────────────────────────────────

async function runPrivacyModalTests(browser) {
  console.log('\nPrivacy page — Manage Analytics Preferences button');

  const ctx  = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await openWithGeo(page, '/privacy', 'eu');
  await page.waitForTimeout(300);

  await test('"Manage Analytics Preferences" button is visible on privacy.html', async () => {
    // Look for a button with PSP.showPrivacyChoices or showConsentBanner in its onclick
    const btn = page.locator('button[onclick*="PSP"]');
    const count = await btn.count();
    assert(count > 0, 'No PSP preferences button found on privacy.html');
  });

  await ctx.close();
}

// ── Responsive banner layout (narrow/landscape) ───────────────────────────────

async function runBannerResponsiveTests(browser) {
  console.log('\nConsent banner responsive layout');

  // ≤479px — banner should stack to column
  const ctxNarrow = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const pageNarrow = await ctxNarrow.newPage();
  await openWithGeo(pageNarrow, '/404', 'eu');
  await pageNarrow.waitForTimeout(300);

  await test('banner button row stacks at 390px', async () => {
    const banner = await pageNarrow.locator('#psp-consent-banner').isVisible();
    assert(banner, 'banner not visible at 390px');
    // Check the banner is present without horizontal overflow
    const sw = await pageNarrow.evaluate(() => document.documentElement.scrollWidth);
    const cw = await pageNarrow.evaluate(() => document.documentElement.clientWidth);
    assert(sw <= cw, `banner causes horizontal scroll at 390px: scrollWidth ${sw} > ${cw}`);
  });

  await ctxNarrow.close();

  // Mobile landscape (max-height 400px) → banner should be compact
  const ctxLandscape = await browser.newContext({ viewport: { width: 667, height: 375 } });
  const pageLandscape = await ctxLandscape.newPage();
  await openWithGeo(pageLandscape, '/404', 'eu');
  await pageLandscape.waitForTimeout(300);

  await test('banner is compact at mobile landscape (667×375, max-height ≤400px)', async () => {
    const bannerHeight = await pageLandscape.locator('#psp-consent-banner').evaluate(
      el => el.getBoundingClientRect().height
    );
    const viewportHeight = 375;
    // Banner should not occupy more than 60% of a 375px tall viewport
    assert(bannerHeight < viewportHeight * 0.6,
      `banner height ${bannerHeight}px seems too tall for a ${viewportHeight}px landscape viewport`);
  });

  await ctxLandscape.close();
}

// ── Accessibility — focus-visible on consent buttons ─────────────────────────

async function runAccessibilityTests(browser) {
  console.log('\nAccessibility — keyboard focus on consent buttons');

  const ctx  = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await openWithGeo(page, '/404', 'eu');
  await page.waitForTimeout(300);

  await test('Decline button is focusable (interactive and not hidden from tab order)', async () => {
    // The banner buttons are native <button> elements appended to <body>.
    // Verify they are keyboard-reachable: not disabled, not tabindex=-1.
    const declineTabIndex = await page.locator('#psp-consent-decline').getAttribute('tabindex');
    const acceptTabIndex  = await page.locator('#psp-consent-accept').getAttribute('tabindex');
    const declineDisabled = await page.locator('#psp-consent-decline').getAttribute('disabled');
    const acceptDisabled  = await page.locator('#psp-consent-accept').getAttribute('disabled');
    assert(declineTabIndex !== '-1', 'Decline button has tabindex="-1"');
    assert(acceptTabIndex  !== '-1', 'Accept button has tabindex="-1"');
    assert(declineDisabled === null, 'Decline button is disabled');
    assert(acceptDisabled  === null, 'Accept button is disabled');

    // Programmatic focus works (focus-visible outline is defined in CSS)
    await page.locator('#psp-consent-decline').focus();
    const focused = await page.evaluate(() =>
      document.activeElement && document.activeElement.id === 'psp-consent-decline'
    );
    assert(focused, 'Decline button could not receive programmatic focus');
  });

  await ctx.close();
}

// ── Utility pages load without JS errors ─────────────────────────────────────

async function runPageLoadTests(browser) {
  console.log('\nPage load — 404, privacy, terms');

  const pages = ['/404', '/privacy', '/terms'];
  for (const p of pages) {
    const ctx  = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();

    const jsErrors = [];
    page.on('pageerror', err => jsErrors.push(err.message));

    await page.goto(BASE + p, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);

    await test(`${p}.html loads with no JS console errors`, async () => {
      assert(jsErrors.length === 0,
        'JS errors: ' + jsErrors.slice(0, 3).join(' | '));
    });

    await test(`${p}.html has psp-interior body class`, async () => {
      const cls = await page.locator('body').getAttribute('class');
      assert(cls && cls.includes('psp-interior'),
        `body class "${cls}" missing "psp-interior"`);
    });

    await ctx.close();
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────

(async () => {
  await new Promise(resolve => server.listen(PORT, resolve));
  console.log(`Static server running at ${BASE}`);

  const browser = await chromium.launch({ headless: true });

  try {
    await runPageLoadTests(browser);
    await runResponsiveTests(browser);
    await runConsentBannerTests(browser);
    await runConsentActionTests(browser);
    await runAnalyticsGatingTests(browser);
    await runPrivacyModalTests(browser);
    await runBannerResponsiveTests(browser);
    await runAccessibilityTests(browser);
  } finally {
    await browser.close();
    server.close();
  }

  console.log('\n─────────────────────────────────────────────');
  console.log(`Results: ${passed} passed, ${failed} failed`);

  if (errors.length) {
    console.log('\nFailed tests:');
    errors.forEach(e => console.log(`  ${e.name}: ${e.message}`));
  }

  console.log('\nREQUIRES DEPLOYED WORKER (not testable locally):');
  console.log('  - Worker injects correct psp-geo meta tag for US IP → "other"');
  console.log('  - Worker injects correct psp-geo meta tag for EU IP → "eu"  (use VPN)');
  console.log('  - Worker sets s-maxage=0 on HTML responses (verify via curl -I)');
  console.log('  - Non-HTML assets (CSS/JS/images) are NOT modified by Worker');
  console.log('  - Worker failure (route deleted) → analytics.js falls back to opt-in mode');

  process.exit(failed > 0 ? 1 : 0);
})();
