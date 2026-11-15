# Issue #9: remaining verification evidence

This evidence supports #36, #37 and #38. It does not close them or certify WCAG conformance. The local browser checks use a synthetic SQLite database, local-only sessions and in-memory email; no production records or live submissions were used.

## Accessibility (#37)

See [browser-results.json](accessibility/browser-results.json) for the timestamp, base revision, exact paths, roles, accessibility trees, focus sequence, measured widths, axe version/results (including incomplete checks), and invalid-submit results. [template-manifest.json](accessibility/template-manifest.json) identifies the tested template contents on top of that base revision. The fixture contains three published events and synthetic attendee/organizer/admin users. The admin user was not used for the sampled routes.

Browser: headless Chromium 156.0.8078.79 on Linux, automated using Playwright. Default page scans used axe-core WCAG 2 A/AA and WCAG 2.1 A/AA tags at 1440 CSS px. Width sweeps used 360/768/1440 CSS px. These are local implementation results, not deployed-site verification.

| Sampled page/state | Result after fixes |
| --- | --- |
| Populated discovery, login, registration, event detail | HTTP 200; no horizontal overflow at sampled widths; no axe violations in sampled default state |
| Attendee dashboard (empty registrations), attendee profile | Same; authenticated routes tested via synthetic local sessions |
| Organizer dashboard (three events), event creation | Same; 360 px event form overflow fixed |
| Empty registration submission | Invalid fields point to existing help/error elements; error summary receives focus |
| Invalid event creation submission | Invalid fields point to existing error elements; error summary receives focus |

Before fixes, axe measured the guest navigation Create account text as #172554 on #2563eb (2.84:1, below 4.5:1). The navigation override now keeps its primary button text white (#ffffff on #2563eb, approximately 5.17:1). The login registration link now has an underline. Invalid-field description IDs previously did not resolve; registration help/error elements and event-form errors now supply those IDs. Both forms focus a linked error summary. The event form now stacks its grid below 600 px. The initial raw browser findings are retained in [before-results.json](accessibility/before-results.json); its single combined-ID lookup cannot validate multi-token descriptions, so that measurement was corrected to resolve each ID separately in the after run. The missing individual help/error elements were also confirmed in the templates.

Screenshots: [discovery at 360 px](accessibility/discovery-360.png), [registration at 360 px](accessibility/registration-360.png), [event form at 360 px](accessibility/event-create-360.png). These show selected default states, not all tested widths or error states. The event-form screenshot was visually inspected for stacking/clipping; keyboard focus styles were recorded by script, not independently reviewed visually for every control.

Validation: existing Django events suite discovered 95 tests, passed with two concurrency tests skipped on SQLite; two added error-description tests passed separately. Logs are in this directory. No claim is made that SQLite verifies PostgreSQL concurrency.

Still pending: real screen-reader announcements; real browser 200% zoom/reflow; manual text/UI/focus contrast review (axe incomplete checks are not passes); complete keyboard interaction and reverse traversal/no-trap checks; other authenticated workflows (registration/payment/tickets/reporting/admin), error states beyond the two sampled forms, and post-deployment retests. The attendee sample had no registrations. A recorded Tab sequence is not proof of full keyboard operability.

## Screen-reader handoff (#36)

Use the [Windows/NVDA worksheet](nvda-worksheet.md) for the remaining manual checks. A [new user-performed registration report](registration-nvda-user-report.md) records actual Speech Viewer text with NVDA, Windows and Edge versions. It has not been independently reproduced. The worksheet's unexecuted items remain pending; the older registration report is not retroactively verified by this separate check. Accessibility-tree names and HTML password types do not prove spoken announcements.

The user also [reported successful NVDA and forward/reverse keyboard checks on discovery and login](discovery-login-nvda-user-report.md). Exact per-control speech and page-specific execution metadata were not supplied, so this confirmation is kept separate from the registration transcript and does not establish full accessibility completion.

## Uptime (#38)

The user-supplied revised SRS PDF page 15 and Test Plan PDF page 25 state: scheduled readiness monitoring, with schedule, endpoint, timestamped results and failures documented over the available project observation window. They explicitly call 99.5% monthly uptime a longer-term objective rather than academic prototype acceptance. Revised SAD PDF page 18 describes retained timestamped external readiness checks. These documents retain candidate/approval caveats: record which baseline and observation window the team accepts; this report supplies no faculty approval.

The current workflow is active, checks `/health/ready/`, is configured for `*/15 * * * *`, uploads CSV results for 35 days and accepts manual dispatch. [run-history.json](uptime/run-history.json) is the API history captured during this review, not a stream of health measurements. It contains four successful scheduled runs plus two successful manual runs. Scheduled creation gaps were 310.52, 235.50 and 209.08 minutes, exceeding the configured 15 minutes. A scheduled job examined through the API started three seconds after run creation and completed within 38 seconds; that run does not show a multi-hour runner queue. It does not establish why other scheduled invocations are absent.

Historical issue reports give scheduled HTTP 200 samples with response times 32.701/41.640/31.756/32.817 seconds and a later manual sample of 0.184 seconds. Those numbers were not independently revalidated from the CSV artifacts in this review: artifact download returned Forbidden. Workflow success is not substituted for a raw status/latency CSV. No new health checks or load were triggered.

Remaining action: preserve raw CSV artifacts before their 35-day expiry, confirm the accepted observation period and missing-sample treatment, investigate scheduled-trigger gaps with the repository/deployment owner, and extend observation if the accepted criteria require it. Missing observations are unknown, not assumed UP or DOWN. No availability percentage or monthly SLO compliance is claimed. If strict 15-minute sampling is required, evaluate an external scheduled monitor with the owner rather than claiming GitHub cron guarantees that cadence. No monitoring configuration was changed without an evidenced cause.
