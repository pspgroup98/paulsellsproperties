# Privacy Incident Response

Procedures for responding to a privacy or security incident affecting paulsellsproperties.com.

**Last updated:** August 2026

---

## What Constitutes an Incident

| Incident type | Examples |
|--------------|---------|
| Unauthorized access | Someone gains access to the email account receiving Formspree submissions |
| Data exposure | Form submissions visible to unintended parties |
| Third-party breach | Formspree, Calendly, or another vendor announces a security breach |
| Site compromise | Malicious code injected into the site's HTML or JavaScript files |
| Repository exposure | Private content accidentally committed to a public repository |

---

## Immediate Response (First Hour)

1. **Contain.** If the site is compromised, disable or revert the affected code. Revert commits if malicious changes are detected:
   ```bash
   git revert <commit>
   git push origin main --force-with-lease
   ```

2. **Assess.** What data may have been exposed? Who may have been affected?

3. **Preserve.** Do not delete evidence before documenting it. Screenshot or log what was found.

4. **Notify yourself.** Create a brief incident note with: date discovered, what was found, initial assessment of scope.

---

## Vendor-Specific Response

### Formspree breach or unauthorized access
- Review Formspree status page: [formspree.io/status](https://status.formspree.io)
- Change Formspree account password immediately
- Review email account for unauthorized access (check login history in email provider)
- If email account was compromised, change password and enable 2FA

### GitHub repository compromise
- Review commit history: `git log --oneline -20`
- If malicious commit found: `git revert`, push, verify GitHub Pages re-deploys
- Review GitHub access log in account security settings

### Analytics data exposure
- GA4 and Clarity do not store PII by design — scope of exposure is limited
- If GA4 property was accessed by unauthorized parties: remove unauthorized access in GA4 Admin

---

## Notification Decisions

**Internal notification:** Document every incident regardless of scope.

**Affected individual notification:** Notify individuals whose personal information (name, email, message content) may have been exposed. Email them directly explaining what happened, what data was involved, and what was done to address it.

**California law notification:** California Civil Code 1798.29 and 1798.82 require notification if a breach involves unencrypted personal information of California residents. Consult an attorney for breach notification obligations — do not make notification decisions without legal guidance.

---

## Post-Incident Review

After containment, document:
- What happened (timeline)
- What data was involved
- Who was notified
- What was changed to prevent recurrence

---

## Preventive Checklist

- [ ] 2FA enabled on: email account, Formspree account, Calendly account, GitHub account, GA4, Clarity
- [ ] Site password: GitHub account uses a strong, unique password
- [ ] Formspree form IDs: these are semi-public (in page source) but not credentials — keep account credentials private
- [ ] Repository: confirm `.gitignore` excludes any files with secrets (currently: `editorial-context.json`, `approved-batches/*.json`)
- [ ] Analytics.js: confirm only public IDs are in code (GA4 Measurement ID and Clarity Project ID are designed to be public)
- [ ] No secrets committed: run `git log --all --full-history -- "**/*secret*" "**/*credential*" "**/*.env"` periodically
