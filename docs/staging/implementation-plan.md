# Issues #32 and #33 implementation plan

Owner: Rahul. Execution and evidence review: Rahul, with Rajath/team review requested through the PR.

1. Use `.venv` for all Python dependencies, Django, Gunicorn and orchestration. PostgreSQL runs as an isolated native service; a Python virtual environment does not isolate a database server.
2. Provision an unprivileged, loopback-only PostgreSQL cluster under ignored `.staging/`, with separate source and restore databases. Use the installed PostgreSQL version and capture it. Never use existing deployment credentials or databases.
3. Add a guarded repeatable seed command for a known synthetic dataset: 1,500 events, 1,233 published, 233 published matches for `Sample`, category/status/date/venue variation, organizer and ticket tiers. Reject unexpected databases and pre-existing unrelated events.
4. Run migrations and Django checks on PostgreSQL, seed, analyze, start Gunicorn, verify readiness and nonempty search results. Capture revision, hardware, application configuration and dataset counts.
5. Run synchronized search probes with 10, 50 and 100 clients; retain full JSON including failures. Correct the probe's HTTP-error handling and test it.
6. Dump the populated source, restore into a distinct empty database, compare public-table row counts and database integrity indicators, check migration state and restored application readiness. Record backup identity, timestamps, duration and operator. Keep private dump/data outside Git.
7. Run meaningful PostgreSQL tests and seed-safety tests. Save sanitized evidence and document reproduction, access, resource assumptions and backup/audit policy gaps.
8. Package a reviewable PR addressing both issues. Do not claim deployed backups, production-comparable staging, monthly availability, full accessibility, high-volume registration testing or overall Issue #9 acceptance. No deployed database or approved production baseline is currently available according to the owner. Leave unsupported criteria pending.

## Documentation and PR scope

- This plan, `docs/staging/README.md`, sanitized execution evidence and a current status matrix.
- Repeatable local orchestration, synthetic-data command and regression tests.
- Update the Issue #9 runbook with an explicit link to new evidence and its limits.
- One PR referencing #32 and #33 (without auto-close keywords while deployment-specific criteria remain pending). No automatic messages, issue comments or reviewer notifications. Remote PR publication is the final review step; local preparation and validation come first.

## Acceptance boundary

Local PostgreSQL setup, benchmark execution and isolated recovery verification can be completed here. Team agreement on a production baseline/test window, provider backup settings, deployed audit scheduling/archival, production recovery objectives and independent evidence review require external decisions. Document these as pending, never substitute proposed settings for verified policy.

## Execution status — 2026-11-15

Steps 1–7 are implemented and locally verified: 95 PostgreSQL Django tests, two benchmark regression tests, all 160 search requests successful, and separate-database restore checks passed. See `results.md` and the authoritative run's source manifest. Step 8 has a prepared PR description in `pr-description.md`; publishing status is reported in the task handoff. External acceptance items in the boundary above remain pending.
