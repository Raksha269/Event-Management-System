# Issue #37 follow-up — attendee registration errors and evidence status

## Final academic-scope acceptance

The repository owner recorded team acceptance in [Issue #9](https://github.com/Raksha269/Event-Management-System/issues/9#issuecomment-6932891735) and [Issue #38](https://github.com/Raksha269/Event-Management-System/issues/38#issuecomment-6932881938). Both issues are closed against the limited academic-project scope. This records the owner's stated team decision; no separate faculty approval is inferred.

[Issue #37](https://github.com/Raksha269/Event-Management-System/issues/37#issuecomment-6922868953) records the owner's completed responsive/keyboard checks for User Administration and Security Alerts at 320, 360, 768 and 1440 px, NVDA form-error/navigation checks, and confirmation that Manage Tickets responsive and remaining contrast checks were checked. These are user-performed results. Additional numerical contrast measurements or independent retests are not invented here. This acceptance is not a full WCAG certification.

Scheduled evidence is accepted with its gaps retained as UNKNOWN. Consistent 15-minute execution, monthly availability, availability percentages and downtime durations remain unverified. Maintenance exclusions require documented approval. Historical test results and limitations below remain unchanged.

Historical findings below describe the earlier follow-up, before the later owner verification and closure. Their pending statements are retained as historical context.

Date: 2026-11-16 (Asia/Kolkata). Code and Django tests were run in the isolated `feature/issue-37-accessibility-completion` worktree using an isolated SQLite test database. All test accounts and event records are synthetic. No production or shared database, hosted site, or live registration flow was used.

## Defect fixed

An invalid attendee event-registration POST previously fell through to a redirect to the event detail page. That discarded the bound form errors, so the attendee did not receive field-specific validation feedback. The view now renders the event detail page with the bound form on validation failure. Invalid controls expose `aria-invalid` and resolvable `aria-describedby` targets; a focusable `role="alert"` error summary links to invalid fields and receives focus. Field-level messages remain visible beside their controls.

Selected empty-state and event-detail headings were also adjusted to avoid skipped heading levels, and global error messages now use an alert role. These changes are implementation fixes; they do not establish how a screen reader announces them.

## Verification performed

| Check | Environment/method | Actual result | Evidence |
| --- | --- | --- | --- |
| Attendee invalid registration response | Django test client; synthetic attendee/event; isolated SQLite | Passed: response re-renders the event page; error summary exists, is an alert and focusable, script focuses it; every `aria-describedby` ID resolves; no registration row is created | `events/test_accessibility_errors.py::test_event_registration_errors_are_announced_and_linked_to_fields` |
| Registration service failure feedback | Django test client; synthetic full event | Passed: failure feedback is rendered as an alert and sold-out status is present | `events/test_accessibility_errors.py::test_registration_service_failure_uses_an_alert_role` |
| Heading hierarchy on sampled empty states | Django test client; discovery, attendee dashboard, organizer dashboard | Passed: first heading is level 1; no subsequent sampled heading skips a level | `events/test_accessibility_errors.py::test_selected_empty_states_have_no_skipped_heading_levels` |
| Targeted accessibility regressions | `python manage.py test events.test_accessibility_errors` | **9 tests passed** | Command output from 2026-11-16 |
| Full Django suite | `python manage.py test` | **119 tests passed; 2 SQLite concurrency tests skipped** | Command output from 2026-11-16; skips are expected because SQLite cannot verify the PostgreSQL concurrency guarantees |
| Django configuration | `python manage.py check` | **Passed; no issues identified** | Command output from 2026-11-16 |
| Whitespace validation | `git diff --check` | **Passed** | Command output from 2026-11-16 |

The existing browser artifacts at [`browser-results.json`](browser-results.json) and [`contrast-browser-results.json`](contrast-browser-results.json) remain historical evidence from headless Chromium 156.0.8078.79 with axe-core 4.14.0 on the documented sample pages and 360/768/1440 CSS-pixel widths. They were not regenerated for this patch and do not verify the new registration-error rendering, current authenticated workflows, actual 200% zoom, or manual contrast. Existing user-reported NVDA and zoom reports remain attributed to their reporters and were not independently repeated in this follow-up.

## Issue #37 acceptance status

| Acceptance criterion | Status | Evidence / remaining work |
| --- | --- | --- |
| Record agreed page/workflow checklist, browser/version, environment, date and evidence for each check | **PARTIAL** | Existing manual matrix and historic browser evidence are linked from [`issue-36-37-followup-2026-11-15.md`](issue-36-37-followup-2026-11-15.md); this supplement records test environment/date/results. Team agreement on the complete checklist and fresh browser captures is not recorded. |
| Test authenticated attendee/organizer workflows for keyboard order, visible focus and keyboard traps | **INCOMPLETE** | Existing user reports cover selected attendee and organizer states. Full forward/reverse traversal and no-trap checks across the agreed workflows have not been independently performed in this follow-up. |
| Verify form-error identification, association and focus in isolated staging, coordinating screen-reader announcements with #36 | **PARTIAL** | New synthetic-local Django regression confirms attendee invalid-form response, error IDs, summary focus markup, and no registration side effect. Existing organizer creation/ticket-tier tests cover their markup. A real isolated staging/browser retest and coordinated NVDA announcement evidence remain pending under #36. |
| Verify 200% zoom/reflow and populated event cards at 360/768/1440 CSS px using representative staging data | **PARTIAL** | Historic headless browser runs cover selected pages and populated discovery data at those CSS widths; user reports cover selected 200% zoom states. Fresh independent retests of updated pages, authenticated dashboards/forms and representative populated cards, including 200% reflow, remain pending. |
| Record text/UI contrast measurements against agreed WCAG 2.1 AA criteria, plus headings, control names and image alternatives | **PARTIAL** | Historic axe and selected palette measurements are preserved; selected empty-state heading order now has a regression test. A complete manual measurement of text, UI boundaries, focus, hover/disabled and status/error colors plus image alternatives on the full checklist remains pending. |
| Link defects, record fixes/retests and submit scoped evidence in a PR; leave untested items pending | **IN PROGRESS** | The invalid-registration defect and regression test are in this change; remaining checks are explicitly marked pending. PR review and acceptance are required. |

Issue #37 is **not ready to close**. Parent #9 remains open. This report makes no claim of complete WCAG conformance or production/staging verification.

## Exact remaining manual work

Using the team-approved isolated staging fixture and recording browser/version, environment, date/time and evidence:

1. Run complete forward and reverse keyboard traversal through the agreed attendee and organizer workflows, confirm visible focus at each step, and verify no keyboard trap.
2. At 360, 768 and 1440 CSS px, inspect populated event cards, ticket creation/forms, attendee dashboard and organizer dashboard for clipping and horizontal overflow; repeat at 200% browser zoom and record the actual viewport/reflow result.
3. Measure representative text, control boundary, focus, disabled/hover, error and status colors against WCAG 2.1 AA thresholds; document each sampled foreground/background pair and ratio.
4. Verify headings, control names and image alternatives on the agreed pages.
5. Coordinate the invalid registration and organizer validation flows with the screen-reader check in Issue #36; record only actual NVDA/browser speech and findings.
6. Attach fresh captures or reproducible logs, retest any defects, and obtain reviewer/team acceptance before closing #37.
