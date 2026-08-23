# Tracking Technologies Inventory

Cookies, local storage, and tracking technologies used on paulsellsproperties.com.

**Last updated:** August 2026

---

## Cookies Set by This Site

This site's own code sets **no cookies directly**. All cookies on the site are set by third-party
services described below.

---

## Third-Party Cookies

### Google Analytics 4

| Cookie | Purpose | Expiry |
|--------|---------|--------|
| `_ga` | Distinguishes visitors (random ID) | 2 years |
| `_ga_XXXXXXXXXX` | Stores session state | 2 years |

These are analytics cookies, not advertising cookies. GA4 is configured with:
- `allow_google_signals: false` (Google Signals disabled)
- `allow_ad_personalization_signals: false`
- `ad_storage: "denied"` via Consent Mode

### Microsoft Clarity

| Cookie | Purpose | Expiry |
|--------|---------|--------|
| `_clck` | Stores visitor ID | 1 year |
| `_clsk` | Links page views to a session | 1 day |
| `_cltk` | Session token | Session |
| `MUID` | Microsoft user ID (cross-Microsoft analytics) | 1 year |

Clarity input masking is enabled — form fields and text inputs are not recorded.

### Calendly

Calendly sets cookies when the scheduling popup is opened (not on page load — Calendly
assets are loaded lazily, only on user interaction). Calendly's cookies are governed by
[Calendly's cookie policy](https://calendly.com/privacy).

---

## Browser Local Storage

| Key | Purpose | Value format | Shared? |
|-----|---------|-------------|---------|
| `psp_analytics` | Analytics consent preference | `"granted"` or `"denied"` | Per-browser only; not transmitted |

---

## Tracking Pixel / Beacon Technologies

**None.** This site does not use:

- Meta Pixel (Facebook/Instagram advertising pixel)
- TikTok Pixel
- Google Ads conversion tracking
- Google Ads remarketing
- LinkedIn Insight Tag
- Any other advertising or retargeting pixel
- Email open tracking pixels
- Server-side event matching / CAPI

---

## Session Recording

Microsoft Clarity records mouse movements, clicks, and scroll behavior to help
improve site usability. Input fields (forms, text areas, password fields) are
**masked by default** — keystrokes are not captured. Recordings do not include
personally identifiable information by design.

---

## How to Opt Out

**Option A — Site-level opt-out:**
Click "Privacy Policy" in the footer → "Manage Analytics Preferences" → "Turn off analytics".
GA4 and Clarity will not load on subsequent page visits from this browser.

**Option B — Browser-level opt-out:**
- GA4: [Google Analytics opt-out add-on](https://tools.google.com/dlpage/gaoptout)
- Clarity: Respects Global Privacy Control (GPC) browser signal
- Calendly: Do not open the scheduling popup

**Option C — Browser settings:**
Delete cookies for `paulsellsproperties.com`, `google-analytics.com`, `clarity.ms`,
and `bing.com` using your browser's developer tools or settings.

---

## Audit Log

| Date | Change |
|------|--------|
| August 2026 | Initial inventory created |
| August 2026 | GA4 and Clarity added (replacing zero analytics state) |
| August 2026 | Calendly changed from eager-load to on-demand load |
