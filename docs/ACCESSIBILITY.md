# Accessibility Compliance & Findings (WCAG 2.1 AA) — FDR Portal

Review and verification of accessibility standards for the AICTE Security Deposit / FDR Portal prototype.

## Principles & Design Hardening
1. **Never Colour Alone:**
   - Every badge and status indicator pairs color with text labels and semantic icons (e.g., `claimed`, `confirmed`, `stale`, `changed`).
   - Discrepancy codes (`D1` through `D6`) explicitly state severity and message, not just red badge tinting.
2. **Keyboard Navigation:**
   - All interactive controls (buttons, modals, forms, tables) have visible focus indicators (`ring-2 ring-primary`).
   - Modal dialogs maintain focus traps and support `Escape` key dismissal.
   - Form inputs have associated `<label>` elements with matching `htmlFor` / `id`.
3. **Screen Reader Compatibility:**
   - `aria-labels` and `aria-describedby` provided for table actions, icon buttons, and file upload dropzones.
   - Dynamic counter updates use `aria-live="polite"` regions so assistive technology users receive real-time updates.
   - Status banners include `role="alert"` or `role="status"`.
4. **Plain Language & Transparency:**
   - Clear status messages: *"Waiting for bank confirmation"*, *"Bank-confirmed on 2026-04-01"*, *"Matures in 45 days"*, *"Overdue by 12 days"*.
   - Clear simulated environment notice: Persistent `SIMULATED ENVIRONMENT — SYNTHETIC DATA ONLY` banner displayed at all times.

---

## Accessibility Audit Findings & Resolutions

| Item ID | Component | WCAG Criterion | Issue Observed | Resolution Implemented | Status |
|---|---|---|---|---|---|
| **A11Y-01** | Action Table | 1.4.1 Use of Color | Status dots relied only on green/yellow/red styling | Added explicit textual badge tags (`Confirmed`, `Pending`, `Discrepancy`) alongside icons | **FIXED** |
| **A11Y-02** | File Upload Modal | 2.1.1 Keyboard | Drag-and-drop zone lacked explicit keyboard Enter/Space trigger | Added hidden native file input with keyboard focusable trigger button | **FIXED** |
| **A11Y-03** | Needs Action Queue | 1.3.1 Info & Relationships | Action buttons in table lacked accessible name for screen readers | Added `aria-label="Process action for {reference_number}"` | **FIXED** |
| **A11Y-04** | Discrepancy Alerts | 4.1.3 Status Messages | Discrepancy banners did not announce on dynamic render | Added `role="alert"` and `aria-live="assertive"` to alert container | **FIXED** |
| **A11Y-05** | Form Validation | 3.3.1 Error Identification | Input error states only showed red border | Added descriptive error text below input with `aria-errormessage` binding | **FIXED** |

**Conclusion:** All blocking accessibility items have been verified and remediated to meet WCAG 2.1 Level AA conformance.
