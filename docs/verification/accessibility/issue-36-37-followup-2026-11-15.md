# Accessibility follow-up for Issues #36 and #37

Date: 2026-11-15. Environment: repository templates and Django test client with isolated SQLite test databases. No production site, production account, or live data was used in this follow-up.

## Existing evidence retained

The earlier reports in [`../README.md`](../README.md), [`browser-results.json`](browser-results.json), [`contrast-browser-results.json`](contrast-browser-results.json), and the linked NVDA user reports remain intact. The browser JSON records headless Chromium 156.0.8078.79, axe-core 4.14.0, three viewport widths (360/768/1440 CSS px), and the sampled paths/states. The NVDA reports are user-performed reports and have not been independently reproduced by this follow-up. None of those artifacts is represented as a full manual audit.

## Defects fixed in this follow-up

| Finding | Change | Verification |
| --- | --- | --- |
| Invalid organizer ticket-tier submissions showed field errors without resolvable descriptions or a focused summary. | Add `aria-invalid`, `aria-describedby`, linked error-summary entries, and focus the summary after invalid submission, including capacity/name errors added after normal form validation. | New Django tests submit invalid ticket-tier data and verify the summary, focus script, and every described-by ID; a separate test covers capacity-overflow error association. |
| Admin user search/filter and security-alert filters had no accessible names; repeated per-user action controls had generic names. | Add specific `aria-label`s to search/filter controls and per-user role/action controls. Add captions to user-facing data tables. | New Django response test asserts the rendered accessible names for admin list and alert filters. |
| Ticket tier price/quantity inputs were forced into two columns at narrow widths. | Use a min-width-safe grid that stacks below 600 CSS px. | Code and Django rendering checks confirm the responsive rule is present. A fresh browser viewport measurement was not run in this environment. |

The visible text of repeated controls is preserved; accessible names identify the target user. Hidden table captions use the shared visually-hidden utility.

## Verification performed

- `python manage.py test events.test_accessibility_errors`: **6 tests passed** after the new regressions were added.
- Full Django suite: **115 tests ran; all passed, with 2 concurrency tests skipped on SQLite**. The skips are expected because SQLite does not provide the PostgreSQL concurrency semantics those tests exercise.
- `python manage.py check`: **passed; no issues identified**.
- `git diff --check`: **passed**.
- Existing stored browser/axe results are prior evidence and were not regenerated for this follow-up. Automated axe results do not establish screen-reader speech, complete keyboard operability, manual contrast, or real browser zoom behavior.

## Manual test matrix still required

Use the same Windows machine and record the exact Windows build, screen reader/version, browser/version, date/time/timezone, URL (local or staging), zoom, and whether test data is synthetic. Use synthetic accounts and events only. Copy actual speech from Speech Viewer; do not write expected speech as an observed result. Keep current user reports linked from [`../README.md`](../README.md) and add a separate retest record for the new changes.

| Page/workflow | Controls and states to test | Expected check (not a claimed result) | Actual result |
| --- | --- | --- | --- |
| Registration `/accounts/register/` | Navigation links; username, email, password, confirmation; submit; empty/invalid error summary and each error link | Correct name, role and required state; protected password fields; error summary and linked invalid field feedback | Use existing user transcript as history; independently retest after changes if the team requires it. |
| Login `/accounts/login/` | Username/password, submit, invalid credentials | Names/roles/states; generic login error announced and its focus/reading order understood | Existing user report is not independently reproduced; retest. |
| Discovery `/events/discover/` | Search, category, location, date, Search/Clear, result link and pagination | Each control has an understandable name; result navigation works with keyboard; filters/results context remains understandable | Existing user reports and browser tree retained; manual retest pending. |
| Event detail and registration `/events/<id>/` | Ticket type, quantity, Register; invalid quantity or stale/unavailable tier; confirmation feedback | Labels and errors announced; no focus loss/trap; result feedback is discoverable | Pending direct manual SR retest for error/state transitions. |
| Attendee registrations/profile/ticket/payment | Event card, Pay Now, View Ticket, payment result, QR alternative, profile navigation | Repeated actions distinguish event/ticket; status and outcome are available as text; QR has a useful alternative | Prior local user report covers selected synthetic states only; remaining workflows pending. |
| Organizer dashboard/event create/edit | Event links, view/edit/tickets/report/publish/unpublish; invalid event form | Repeated action context, visible focus and logical sequence; invalid fields linked to focused error summary | Prior user reports cover selected dashboard/event form states only; remaining actions pending. |
| Organizer ticket tiers `/events/<id>/tickets/` | Tier name, price, quantity, Add; empty/invalid/duplicate/capacity-overflow errors | Control name/role/state; error summary receives focus; each error link targets and describes the affected control | New code-level tests passed; actual NVDA retest pending. |
| Organizer report `/events/<id>/report/` | Revenue figures, ticket tier/attendee tables, CSV download | Table captions/headers provide context; download link has a meaningful name; keyboard access works | Caption added where needed; manual SR review pending. |
| Admin user list and alerts `/admin-portal/users/`, `/admin-portal/alerts/` | Search/filter, per-user role/action, resolve | New names identify purpose and target; tables expose captions and headers; state changes have discoverable feedback | New Django markup tests passed; actual NVDA retest pending. |

For all applicable pages, perform forward and reverse keyboard traversal, activate controls without a mouse in a safe local fixture, confirm no trap, inspect visible focus, and test browser zoom at 200% plus reflow at 320 CSS px. Record manual contrast samples for text, control boundaries, focus, disabled/hover states, and error/status badges. Do not treat existing 360/768/1440 width sweeps as proof of 200% zoom or the 320 px reflow check.

## Status

| Requirement area | Status | Basis / remaining work |
| --- | --- | --- |
| Existing public/auth page label, accessible-tree and responsive evidence | PARTIAL | Preserved browser results cover eight states at 360/768/1440 CSS px. They do not cover every user-facing page or current ticket-tier changes. |
| Ticket-tier form field errors and summary focus | COMPLETE FOR THE PATCHED LOCAL STATE | New local Django tests cover field errors and capacity errors; real-browser/SR retest remains outstanding. |
| Admin search/filter and repeated per-user control names | COMPLETE FOR RENDERED MARKUP | New Django tests assert accessible names; no SR announcement has been claimed. |
| 360/768/1440 responsive checks for all applicable pages | INCOMPLETE | Existing sampled pages are documented; ticket-tier grid now has a narrow breakpoint but was not measured in a browser during this follow-up. |
| Full keyboard traversal and visible focus across public/authenticated workflows | INCOMPLETE | Existing scripted/user reports cover selected flows. Complete manual traversal and no-trap checks remain. |
| 200% zoom and reflow | INCOMPLETE | Prior user reports cover selected states; independent complete retesting, including narrow reflow, remains. |
| Full text, UI, status, and focus contrast review | INCOMPLETE | Existing palette samples and axe data are scoped evidence; manual remaining-state contrast audit is pending. |
| Real screen-reader verification (#36) | INCOMPLETE / REVIEW REQUIRED | Linked user-performed NVDA reports exist but were not independently reproduced here; new ticket/admin changes need actual Speech Viewer retests and environment details. |

The follow-up code defects are implemented and locally regression-tested. Issues #36 and #37, and parent #9, remain open. No production verification, screen-reader pass, full manual accessibility audit, or issue closure is claimed.
