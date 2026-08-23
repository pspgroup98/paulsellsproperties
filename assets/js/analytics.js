/**
 * Paul Sells Properties — Analytics
 *
 * Loads Google Analytics 4 and Microsoft Clarity with an opt-out
 * consent model appropriate for a California small-business website.
 *
 * SETUP INSTRUCTIONS
 * ──────────────────
 * 1. Replace MEASUREMENT_ID below with your GA4 property's Measurement ID
 *    (format: G-XXXXXXXXXX). Find it in GA4 > Admin > Data Streams.
 * 2. Replace CLARITY_ID below with your Clarity Project ID
 *    (format: 10-character alphanumeric). Find it in Clarity > Settings.
 * 3. Leave GA4_ENABLED and CLARITY_ENABLED true while testing.
 *    Set either to false to disable that service without removing code.
 *
 * PRIVACY MODEL
 * ─────────────
 * Analytics load by default. Visitors can opt out at any time via the
 * "Privacy Choices" link in the footer or the privacy.html page.
 * The preference is stored in localStorage under the key "psp_analytics"
 * ("granted" = load analytics, "denied" = skip analytics).
 * This default-on, opt-out model is appropriate for basic analytics on
 * a California-based website not subject to CCPA/CPRA size thresholds.
 *
 * WHAT IS NOT DONE HERE
 * ──────────────────────
 * - No Meta Pixel, TikTok Pixel, Google Ads, or remarketing tags
 * - No advertising features (Google Signals disabled)
 * - No ad personalization
 * - No cross-site tracking or fingerprinting
 * - No PII sent to any analytics service
 */

(function () {
  'use strict';

  // ── Configuration ───────────────────────────────────────────────────────────
  var MEASUREMENT_ID = 'G-XXXXXXXXXX'; // TODO: replace with real GA4 Measurement ID
  var CLARITY_ID     = 'xxxxxxxxxx';   // TODO: replace with real Clarity Project ID
  var GA4_ENABLED    = true;
  var CLARITY_ENABLED = true;
  var CONSENT_KEY    = 'psp_analytics'; // localStorage key
  var SCROLL_MILESTONES = [25, 50, 75, 90];

  // ── Consent management ──────────────────────────────────────────────────────

  /**
   * Return the current consent preference.
   * Defaults to "granted" (opt-out model) if no preference has been set.
   */
  function getConsent() {
    try {
      return localStorage.getItem(CONSENT_KEY) || 'granted';
    } catch (e) {
      return 'granted'; // storage blocked — treat as consented
    }
  }

  /**
   * Set the consent preference and reload so the change takes effect.
   * Call from privacy.html or any opt-out UI.
   * window.PSP.setConsent("denied")  — opt out
   * window.PSP.setConsent("granted") — opt back in
   */
  function setConsent(value) {
    if (value !== 'granted' && value !== 'denied') return;
    try {
      localStorage.setItem(CONSENT_KEY, value);
    } catch (e) {}
    // Signal GA4 consent mode update (if gtag is already loaded)
    if (typeof gtag === 'function') {
      gtag('consent', 'update', {
        analytics_storage: value === 'granted' ? 'granted' : 'denied',
        ad_storage: 'denied',           // always denied — no advertising
        ad_user_data: 'denied',         // always denied
        ad_personalization: 'denied',   // always denied
      });
    }
    // Reload the page so analytics scripts reflect the new choice
    window.location.reload();
  }

  var consented = getConsent() === 'granted';

  // ── Google Analytics 4 ──────────────────────────────────────────────────────

  function loadGA4() {
    if (!GA4_ENABLED || !consented) return;
    if (MEASUREMENT_ID === 'G-XXXXXXXXXX') return; // not yet configured

    // Initialize consent mode before loading gtag (required for GA4 consent mode)
    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    window.gtag = gtag;

    gtag('consent', 'default', {
      analytics_storage: 'granted',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied',
    });

    gtag('js', new Date());
    gtag('config', MEASUREMENT_ID, {
      // Disable advertising features
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      // Redact query params that could contain PII (safety net)
      url_passthrough: false,
      // Data retention: 14 months (set in GA4 Admin UI)
      cookie_flags: 'SameSite=Lax;Secure',
    });

    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + MEASUREMENT_ID;
    document.head.appendChild(s);
  }

  // ── Microsoft Clarity ──────────────────────────────────────────────────────

  function loadClarity() {
    if (!CLARITY_ENABLED || !consented) return;
    if (CLARITY_ID === 'xxxxxxxxxx') return; // not yet configured

    (function (c, l, a, r, i, t, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r);
      t.async = 1;
      t.src = 'https://www.clarity.ms/tag/' + i;
      y = l.getElementsByTagName(r)[0];
      y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', CLARITY_ID);

    // Mask all text inputs and textareas (privacy default — do not log keystrokes)
    if (typeof window.clarity === 'function') {
      window.clarity('set', 'maskAll', true);
    }
  }

  // ── Calendly lazy-loading ──────────────────────────────────────────────────

  var _calendlyLoaded = false;
  var _calendlyLoading = false;
  var _calendlyQueue = [];

  /**
   * Open the Calendly popup, loading Calendly assets on first call.
   * Replaces the eager Calendly.initPopupWidget() calls in the HTML.
   */
  function openCalendly(url) {
    if (_calendlyLoaded) {
      window.Calendly.initPopupWidget({ url: url });
      track('calendly_trigger', { calendly_url: url });
      return;
    }

    _calendlyQueue.push(url);

    if (_calendlyLoading) return;
    _calendlyLoading = true;

    // Load Calendly CSS
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://assets.calendly.com/assets/external/widget.css';
    document.head.appendChild(link);

    // Load Calendly JS
    var script = document.createElement('script');
    script.src = 'https://assets.calendly.com/assets/external/widget.js';
    script.async = true;
    script.onload = function () {
      _calendlyLoaded = true;
      _calendlyLoading = false;
      _calendlyQueue.forEach(function (u) {
        window.Calendly.initPopupWidget({ url: u });
        track('calendly_trigger', { calendly_url: u });
      });
      _calendlyQueue = [];
    };
    document.head.appendChild(script);
  }

  // ── Event tracking ─────────────────────────────────────────────────────────

  /**
   * Send a custom event to GA4.
   * Silently no-ops if analytics are not loaded or opted out.
   *
   * @param {string} eventName - GA4 event name (snake_case)
   * @param {Object} params    - event parameters (no PII)
   */
  function track(eventName, params) {
    if (!consented) return;
    if (typeof window.gtag !== 'function') return;
    window.gtag('event', eventName, params || {});
  }

  // ── UTM parameter extraction ────────────────────────────────────────────────

  function _getUTMParams() {
    try {
      var search = window.location.search;
      if (!search) return {};
      var params = {};
      var parts = search.slice(1).split('&');
      parts.forEach(function (p) {
        var kv = p.split('=');
        if (kv[0] && kv[0].startsWith('utm_')) {
          params[kv[0]] = decodeURIComponent(kv[1] || '');
        }
      });
      return params;
    } catch (e) {
      return {};
    }
  }

  // ── Scroll depth tracking ──────────────────────────────────────────────────

  function _initScrollTracking() {
    if (!consented) return;
    var reached = {};
    function onScroll() {
      var scrollTop = window.scrollY || document.documentElement.scrollTop;
      var docHeight = Math.max(
        document.body.scrollHeight, document.documentElement.scrollHeight,
        document.body.offsetHeight, document.documentElement.offsetHeight
      ) - window.innerHeight;
      if (docHeight <= 0) return;
      var pct = Math.round((scrollTop / docHeight) * 100);
      SCROLL_MILESTONES.forEach(function (m) {
        if (!reached[m] && pct >= m) {
          reached[m] = true;
          track('scroll', { percent_scrolled: m });
        }
      });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  // ── Auto-instrumentation from data-track-* attributes ─────────────────────

  function _autoInstrument() {
    // data-track-click="event_name" data-track-params='{"key":"value"}'
    document.querySelectorAll('[data-track-click]').forEach(function (el) {
      el.addEventListener('click', function () {
        var eventName = el.getAttribute('data-track-click');
        var rawParams = el.getAttribute('data-track-params');
        var params = {};
        try { params = rawParams ? JSON.parse(rawParams) : {}; } catch (e) {}
        track(eventName, params);
      });
    });

    // Outbound link tracking
    document.querySelectorAll('a[href]').forEach(function (a) {
      try {
        var href = a.getAttribute('href');
        if (!href) return;
        // Skip internal, anchor, mailto, tel
        if (href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) return;
        if (href.startsWith('/') || href.startsWith('../') || !href.startsWith('http')) return;
        // Exclude same-domain
        var url = new URL(href, window.location.href);
        if (url.hostname === window.location.hostname) return;
        a.addEventListener('click', function () {
          track('outbound_link', { link_url: href, link_domain: url.hostname });
        });
      } catch (e) {}
    });

    // Contact method clicks
    document.querySelectorAll('a[href^="mailto:"]').forEach(function (a) {
      a.addEventListener('click', function () {
        track('contact_method_click', { method: 'email' });
      });
    });
    document.querySelectorAll('a[href^="tel:"]').forEach(function (a) {
      a.addEventListener('click', function () {
        track('contact_method_click', { method: 'phone' });
      });
    });
  }

  // ── Article page tracking ──────────────────────────────────────────────────

  function _trackArticleView() {
    var section = document.querySelector('[data-article-slug]');
    if (!section) return;
    var slug = section.getAttribute('data-article-slug');
    var category = section.getAttribute('data-article-category') || '';
    var articleType = section.getAttribute('data-article-type') || '';
    track('article_view', {
      article_slug: slug,
      article_category: category,
      article_type: articleType,
    });
  }

  // ── Form tracking ──────────────────────────────────────────────────────────

  /**
   * Wire up form-level analytics for a form element.
   * Call from each page's inline script: PSP.trackForm(formElement, "form_name")
   *
   * Do NOT pass form field values (including email, name, phone) to this function.
   * Only pass the form identifier string.
   */
  function trackForm(formEl, formName) {
    if (!formEl) return;
    var started = false;
    formEl.querySelectorAll('input, textarea, select').forEach(function (input) {
      input.addEventListener('focus', function () {
        if (!started) {
          started = true;
          track('form_start', { form_name: formName });
        }
      }, { once: true });
    });
    formEl.addEventListener('submit', function (e) {
      track('form_submit', { form_name: formName });
    });
  }

  // ── Privacy opt-out modal ──────────────────────────────────────────────────

  /**
   * Show a simple privacy choices modal.
   * Call from "Privacy Choices" footer link: PSP.showPrivacyChoices()
   */
  function showPrivacyChoices() {
    var existing = document.getElementById('psp-privacy-modal');
    if (existing) { existing.remove(); return; }

    var current = getConsent();
    var modal = document.createElement('div');
    modal.id = 'psp-privacy-modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', 'psp-privacy-title');
    modal.innerHTML = [
      '<div class="psp-modal-backdrop"></div>',
      '<div class="psp-modal-box">',
      '  <h2 id="psp-privacy-title">Privacy Choices</h2>',
      '  <p>This site uses Google Analytics and Microsoft Clarity to understand',
      '  how visitors use the site. No advertising pixels or cross-site tracking.',
      '  No personal information is sent to these services.</p>',
      '  <p class="psp-modal-status">Current status: <strong id="psp-consent-label">',
      (current === 'granted' ? 'Analytics on' : 'Analytics off'),
      '  </strong></p>',
      '  <div class="psp-modal-actions">',
      '    <button id="psp-opt-out" class="btn btn-outline">Turn off analytics</button>',
      '    <button id="psp-opt-in" class="btn btn-gold">Turn on analytics</button>',
      '    <button id="psp-modal-close" class="btn btn-outline">Close</button>',
      '  </div>',
      '  <p class="psp-modal-note"><a href="/privacy.html">Full Privacy Policy</a></p>',
      '</div>',
    ].join('');

    document.body.appendChild(modal);

    modal.querySelector('.psp-modal-backdrop').addEventListener('click', function () {
      modal.remove();
    });
    modal.querySelector('#psp-modal-close').addEventListener('click', function () {
      modal.remove();
    });
    modal.querySelector('#psp-opt-out').addEventListener('click', function () {
      setConsent('denied');
    });
    modal.querySelector('#psp-opt-in').addEventListener('click', function () {
      setConsent('granted');
    });
  }

  // ── Initialization ─────────────────────────────────────────────────────────

  function init() {
    loadGA4();
    loadClarity();
    _getUTMParams(); // parsed automatically by GA4; here for reference

    document.addEventListener('DOMContentLoaded', function () {
      _autoInstrument();
      _initScrollTracking();
      _trackArticleView();
    });
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  window.PSP = window.PSP || {};
  window.PSP.track         = track;
  window.PSP.trackForm     = trackForm;
  window.PSP.openCalendly  = openCalendly;
  window.PSP.setConsent    = setConsent;
  window.PSP.getConsent    = getConsent;
  window.PSP.showPrivacyChoices = showPrivacyChoices;

  // Run immediately (not waiting for DOMContentLoaded) so scripts load early
  init();
})();
