/**
 * PSP Geo Worker — Geographic consent detection for GA4 Consent Mode v2
 *
 * WHAT THIS DOES
 * ──────────────
 * Injects a <meta name="psp-geo"> tag into every HTML response with one of:
 *   content="eu"      — visitor is in EU/EEA/UK (opt-in consent required)
 *   content="other"   — visitor is outside EU/EEA/UK (opt-out/default-granted)
 *   content="unknown" — country could not be determined (treated as opt-in)
 *
 * analytics.js reads this tag in requiresOptIn() to determine the consent model.
 * If the tag is absent (Worker not deployed, or uncaught error), analytics.js
 * treats ALL visitors as requiring consent (privacy-protective default).
 *
 * DEPLOYMENT STEPS
 * ────────────────
 * 1. Log in to dash.cloudflare.com > Workers & Pages > Create Worker
 * 2. Name it "psp-geo" and deploy this code
 * 3. Add a Route in the Worker's Settings > Triggers:
 *    Route: paulsellsproperties.com/* (matches all pages)
 *    Zone: paulsellsproperties.com
 *    Fail open: ON  (serves origin if daily limit exceeded — error 1027)
 * 4. Test: visit the site and check <head> for the psp-geo meta tag
 *
 * ROLLBACK STEPS
 * ──────────────
 * Option A — Disable: Workers > psp-geo > Settings > Triggers > delete the route
 * Option B — Remove: Workers > psp-geo > three-dot menu > Delete Worker
 * analytics.js degrades safely: absent tag = all visitors require opt-in consent.
 *
 * FREE TIER LIMITS (as of 2026)
 * ──────────────────────────────
 * Cloudflare Workers free tier: 100,000 requests/day
 * This Worker adds one HTMLRewriter pass per HTML page request.
 * A site serving ~1,000 HTML pages/day is well within limits.
 * "Fail open" route setting handles the 1027 (daily limit exceeded) case.
 *
 * CACHING NOTE
 * ────────────
 * This Worker does NOT set cache headers — it inherits origin caching.
 * The injected meta tag reflects the visitor's country at request time.
 * Cloudflare's edge cache is bypassed for authenticated or no-cache requests.
 * For cached HTML pages (Cache-Control: public), the geo tag in the cached
 * copy reflects the country of the first visitor who populated that cache slot.
 * This is acceptable because the consent decision is binary (EU vs. non-EU)
 * and conservative (unknown → opt-in); a cached "other" tag that reaches an EU
 * visitor is unlikely for a site primarily serving US traffic.
 *
 * SECURITY
 * ────────
 * The injected meta content is validated to one of three safe literals.
 * No user-controlled input is reflected into the page.
 */

const EU_EEA_UK = new Set([
  // EU member states
  'AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI',
  'FR', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT',
  'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK',
  // EEA non-EU
  'IS', 'LI', 'NO',
  // UK and Crown Dependencies
  'GB', 'GG', 'JE', 'IM',
]);

export default {
  async fetch(request, env, ctx) {
    // If this Worker throws an uncaught exception, Cloudflare would normally
    // return a 1101 error page. passThroughOnException() prevents that by
    // falling back to the origin response instead.
    ctx.passThroughOnException();

    try {
      const response = await fetch(request);

      // Only transform HTML responses
      const ct = response.headers.get('content-type') || '';
      if (!ct.includes('text/html')) {
        return response;
      }

      // Determine region from Cloudflare's country code
      const country = request.cf?.country || '';
      let region;
      if (EU_EEA_UK.has(country)) {
        region = 'eu';
      } else if (country === '') {
        region = 'unknown';
      } else {
        region = 'other';
      }

      // Inject <meta name="psp-geo" content="..."> as the first child of <head>
      return new HTMLRewriter()
        .on('head', {
          element(el) {
            el.prepend(
              `<meta name="psp-geo" content="${region}">`,
              { html: true }
            );
          },
        })
        .transform(response);

    } catch (e) {
      // fetch() error or HTMLRewriter error — return unmodified origin response.
      // analytics.js treats absent psp-geo tag as opt-in (privacy-protective).
      return fetch(request);
    }
  },
};
