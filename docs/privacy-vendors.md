# Privacy Vendor Audit

Third-party services used by paulsellsproperties.com and their privacy implications.

**Last updated:** August 2026

---

## Service Inventory

### Google Analytics 4 (GA4)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Usage analytics — page views, sessions, events |
| **Data sent** | Page URL, session data, browser info, general location, custom events |
| **PII sent?** | No (configured to exclude PII; advertising features disabled) |
| **Advertising use?** | No (Google Signals off, ad_storage denied) |
| **Data residency** | Google's servers (US and global) |
| **Privacy policy** | [policies.google.com/privacy](https://policies.google.com/privacy) |
| **DPA available?** | Yes (Google's data processing addendum included in ToS) |
| **Opt-out mechanism** | Site opt-out via `PSP.setConsent("denied")`; browser add-on at tools.google.com/dlpage/gaoptout |
| **Necessity justification** | Understand content performance to improve editorial quality |
| **Alternative considered** | Cloudflare Web Analytics (privacy-friendly, no cookies) — consider as upgrade |

**Configuration hardening applied:**
- `allow_google_signals: false`
- `allow_ad_personalization_signals: false`
- GA4 Consent Mode: `ad_storage: denied`, `ad_user_data: denied`, `ad_personalization: denied`

---

### Microsoft Clarity

| Attribute | Value |
|-----------|-------|
| **Purpose** | Session recording and heatmaps for UX improvement |
| **Data sent** | Mouse movements, clicks, scroll, page URL |
| **PII sent?** | No (input masking enabled — form fields not recorded) |
| **Advertising use?** | No |
| **Data residency** | Microsoft Azure (US) |
| **Privacy policy** | [privacy.microsoft.com](https://privacy.microsoft.com/privacystatement) |
| **DPA available?** | Yes (Microsoft Online Services DPA) |
| **Opt-out mechanism** | Site opt-out via `PSP.setConsent("denied")`; GPC browser signal respected |
| **Necessity justification** | Identify UX issues without user interviews |
| **Alternative considered** | Hotjar (similar, paid at scale) — Clarity is free and sufficient |

**Configuration hardening applied:**
- `maskAll: true` (masks all input fields and form content)

---

### Formspree

| Attribute | Value |
|-----------|-------|
| **Purpose** | Form submission processing and forwarding |
| **Data sent** | Form field contents (name, email, phone, message, property address) |
| **PII sent?** | Yes — contact form submissions contain PII |
| **Advertising use?** | No |
| **Data residency** | Formspree's servers (US) |
| **Privacy policy** | [formspree.io/legal/privacy-policy](https://formspree.io/legal/privacy-policy/) |
| **Status** | Integration pending — `YOUR_FORM_ID` placeholder not yet replaced |
| **Action required** | Sign up at formspree.io, replace placeholder IDs in contact.html, home-valuation.html, and index.html |
| **Necessity justification** | Receive and respond to contact inquiries without a server |

**Open items:**
- [ ] Create Formspree account and replace placeholder form IDs
- [ ] Configure Formspree spam filtering
- [ ] Review Formspree data retention settings

---

### Calendly

| Attribute | Value |
|-----------|-------|
| **Purpose** | Appointment scheduling |
| **Data sent** | Name, email, phone (optional), selected time — collected by Calendly at scheduling |
| **PII sent?** | Yes — Calendly collects scheduling details directly from the user |
| **Advertising use?** | No |
| **Data residency** | Calendly's servers (US) |
| **Privacy policy** | [calendly.com/privacy](https://calendly.com/privacy) |
| **DPA available?** | Yes |
| **Load behavior** | Lazy — Calendly CSS and JS load only when user clicks a scheduling button |
| **Necessity justification** | Essential for lead capture and appointment booking (core business function) |

---

### Google Fonts

| Attribute | Value |
|-----------|-------|
| **Purpose** | Typography (Cormorant Garamond + Inter) |
| **Data sent** | Browser request to fonts.googleapis.com includes IP address |
| **PII sent?** | IP address (Google processes; does not store per their policy) |
| **Advertising use?** | No |
| **Privacy policy** | [developers.google.com/fonts/faq/privacy](https://developers.google.com/fonts/faq/privacy) |
| **Alternative** | Self-host fonts (eliminates Google request; increases bundle size by ~50KB) |

---

### GitHub Pages

| Attribute | Value |
|-----------|-------|
| **Purpose** | Static site hosting |
| **Data sent** | Visitor IP (server log), user-agent, request path |
| **PII sent?** | Yes (IP address, standard HTTP request data) |
| **Advertising use?** | No |
| **Privacy policy** | [github.com/site-policy](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement) |
| **DPA available?** | Yes (GitHub DPA via Microsoft) |
| **Necessity justification** | Required for hosting (core infrastructure) |

---

## Services NOT Used

The following services were considered and rejected or are not used:

| Service | Reason not used |
|---------|----------------|
| Meta Pixel | Advertising pixel — explicitly prohibited per site policy |
| TikTok Pixel | Advertising pixel — explicitly prohibited |
| Google Ads remarketing | Advertising — explicitly prohibited |
| LinkedIn Insight Tag | Advertising pixel — not needed |
| Hotjar | Paid alternative to Clarity — Clarity sufficient for current scale |
| HubSpot CRM | Overkill for current scale; Formspree + email sufficient |
| CAPTCHA (reCAPTCHA, hCaptcha) | Not installed — Formspree provides spam filtering |

---

## Review Schedule

This inventory should be reviewed:
- When adding any new third-party script or service
- When renewing annual vendor agreements
- Annually at minimum

| Review date | Reviewer | Notes |
|-------------|----------|-------|
| August 2026 | Paul Adams II | Initial audit |
