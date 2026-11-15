# Issue #9: NFR verification and operations

## Remaining verification handoff (#36–#38)

See [the scoped accessibility and uptime report](verification/README.md) for local browser findings/fixes, a Windows/NVDA worksheet, and a snapshot of scheduled monitoring history. This evidence leaves real screen-reader announcements, manual zoom/contrast and full-workflow verification, and accepted uptime observation coverage pending. It does not close Issue #9 or supersede an approved acceptance baseline.

This runbook separates repeatable local/CI checks from evidence that requires the deployed service or its database owner. Do not use the live Render database for load tests, restore rehearsals, or synthetic data.

## Event-search load test

Use an isolated staging deployment with representative **published** events, the same database engine and comparable resource limits as production. Confirm the test window and request rate with the deployment owner. The script performs one read-only request per client; it does not create registrations or events.

```powershell
$env:NFR_BENCHMARK_URL = 'https://<staging-host>/api/v1/events/?q=Sample&limit=50&offset=0'
$env:NFR_BENCHMARK_CLIENTS = '10'
python scripts/nfr_search_benchmark.py
$env:NFR_BENCHMARK_CLIENTS = '50'
python scripts/nfr_search_benchmark.py
$env:NFR_BENCHMARK_CLIENTS = '100'
python scripts/nfr_search_benchmark.py
```

Save the full JSON output with the date, deployment revision, dataset size, database engine, and machine/service size. It reports request totals, HTTP status counts, transport failures and connection refusals, average, p50/p95/p99/max latency, wall time, throughput, and whether the p95 optimization goal was met. Report failed requests; do not discard them. The included script is a synchronized burst probe, not a sustained-load or registration test.

Local SQLite figures do not establish production/PostgreSQL performance. Do not call a benchmark representative if the search query returns no matching published records.

### Historical baseline captured before PR #24 merged (2026-11-14)

This earlier local SQLite run used the same 1,500-event dataset (1,233 published), Waitress (64 threads), and query `q=Sample&limit=50&offset=0`. PR #24 was still open at the time, so this is not a measurement of the current `main` code.

| Concurrent clients | Requests | HTTP 200 | Failed | p95 | Context |
| ---: | ---: | ---: | ---: | ---: | :--- |
| 100 | 100 | 100 | 0 | 3.070 s | pre-PR #24 local baseline |
| 500 | 500 | 500 | 0 | 12.323 s | pre-PR #24 local baseline |

### Revised-scope local benchmark series (2026-11-15)

After PR #24 was merged, the same SQLite dataset, Waitress configuration, and query were measured using 10, 50, and 100 synchronized read-only clients. There were 233 published events matching `Sample`; all requests returned HTTP 200 and there were no transport errors.

| Concurrent clients | Requests | HTTP 200 | Failed | Average | p50 | p95 | p99 | Throughput |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 10 | 10 | 0 | 2.509 s | 2.509 s | 2.517 s | 2.517 s | 3.97 req/s |
| 50 | 50 | 50 | 0 | 1.585 s | 1.591 s | 1.810 s | 1.826 s | 27.31 req/s |
| 100 | 100 | 100 | 0 | 2.900 s | 3.020 s | 3.603 s | 3.614 s | 27.51 req/s |

The v1.2 document set in [PR #29](https://github.com/Raksha269/Event-Management-System/pull/29) is merged. It labels the revised acceptance as a reproducible report with no unreported errors; p95 <= 2 seconds is an optimization goal, not a pass condition. The representative local PostgreSQL container benchmark is now documented in [PR #35](https://github.com/Raksha269/Event-Management-System/pull/35) and `docs/staging/report.md`. This earlier SQLite series remains separate supporting evidence and does not establish performance on a hosted deployment. Confirm with the team/faculty whether any separate approval of the revised baseline is required.

## Availability monitoring

The GitHub Actions workflow `.github/workflows/uptime-monitoring.yml` is configured to check `/health/ready/` every 15 minutes and on manual dispatch. The endpoint tests the Django process and database connectivity. Each run writes HTTP status and response time to the Actions summary and uploads a one-row CSV artifact for 35 days; failed checks also fail the workflow. The monitor does not page an on-call person; configure an external alert destination with the deployment owner if alerting is required.

Observed post-merge scheduled samples (UTC):

| Check time | HTTP status | Response time | Result |
| --- | ---: | ---: | :---: |
| 2026-11-14 13:45 | 200 | 32.701 s | UP |
| 2026-11-14 18:55 | 200 | 41.640 s | UP |
| 2026-11-14 22:51 | 200 | 31.756 s | UP |
| 2026-11-15 02:20 | 200 | 32.817 s | UP |

These four samples verify that scheduled checks and artifact uploads are working. In the observed history, they were spaced several hours apart rather than every 15 minutes, so inspect Actions history for missed or delayed schedules. They do not establish a monthly availability rate; collect a representative observation window before reporting one.

The workflow is configured for the repository's Render URL. If the deployment URL changes, update the workflow and check the readiness route before relying on it. A successful HTTP response is one sample, not proof of a 99.5% monthly SLO.

The GitHub Actions history inspected on 2026-11-15 contained four successful scheduled runs and two manual runs. The scheduled runs were 310.52, 235.50, and 209.08 minutes apart, despite the 15-minute cron. GitHub documents that scheduled events can be delayed or dropped during high workflow load, especially at the start of an hour. The schedule is therefore staggered to minutes 7, 22, 37, and 52 as a mitigation. This does not establish why the earlier runs were absent and does not guarantee cadence; missing run records are unknown monitoring samples, not proof that the service was up or down. Continue collecting the agreed observation period and retain the CSV artifacts before their 35-day expiry. Do not calculate an availability percentage from the incomplete history.

## Backup and restore

### PostgreSQL

The PostgreSQL CI workflow rehearses a custom-format `pg_dump` and restores it into a separate disposable database. The local PostgreSQL container backup/restore rehearsal in [PR #35](https://github.com/Raksha269/Event-Management-System/pull/35) also restored a populated dataset into a separate server/container and verified data, integrity, migrations, and readiness. These checks document the local procedure and actual local retention/access arrangements; they do not verify provider-managed backups for a hosted database.

The database owner should configure and document provider-managed backups, frequency, retention, encryption, access control, and recovery point/recovery time objectives. For an authorized staging rehearsal:

1. Take a backup using the provider's supported process or `pg_dump --format=custom --no-owner --no-acl` with credentials supplied through a protected environment, never a checked-in file or chat.
2. Restore into a newly created, isolated staging database with a distinct name. Never point a rehearsal at the production database.
3. Run `pg_restore --exit-on-error`, apply/check migrations, and verify expected table and representative row counts plus application readiness.
4. Record timestamp, source revision, backup identifier, restore duration, validation results, and operator. Remove the isolated restore only under the team's data-retention process.

### SQLite local development

Use SQLite's online backup facility to make a consistent copy while the application may be open:

```sh
sqlite3 db.sqlite3 ".backup 'db-backup.sqlite3'"
sqlite3 db-backup.sqlite3 "PRAGMA integrity_check;"
```

The integrity check must return `ok`. To rehearse recovery, copy the backup to a separate file such as `db-restore-test.sqlite3`, check it with `PRAGMA integrity_check`, and inspect expected records there. Do not replace `db.sqlite3` for the rehearsal. Protect and expire backup files according to the project's data policy; backups contain personal data and should not be committed.

Local rehearsal completed 2026-11-14 using SQLite's online backup API into a temporary directory: the restored copy returned `integrity_check = ok` and matched the source count of 1,500 event rows. Temporary copies were automatically removed. This verifies a local SQLite copy only, not Render/PostgreSQL backup retention or recovery.

## Registration integrity and database consistency

`events.test_event_management.ConcurrentCapacityTests` runs two concurrent registration attempts against an event with one remaining ticket and asserts exactly one success, one `Sold Out` rejection, zero remaining capacity, and one active registration. Its idempotency test submits two concurrent retries with the same key and asserts that both resolve to one registration row. The tests passed in the PostgreSQL NFR workflow above and in the local Django suite. This is a small deterministic integrity test, not a 500/10,000-client load run.

## Accessibility and usability review

Automated template tests verify that the discovery search, category, location, and date controls have associated labels. These tests do not constitute a WCAG conformance audit. Before marking the review complete, test all public and authenticated workflows with keyboard-only navigation and a screen reader; check visible focus, heading order, link/button names, image alternatives, form errors, zoom/reflow at 200%, and text/UI contrast against WCAG 2.1 AA. Record browser, assistive technology, pages, findings, and screenshots. Fix issues and rerun the checks.

PR #26 reports muted text contrast improved from 4.39:1 to 6.99:1. The previous local responsive spot checks and filter-label tests are useful supporting evidence, but the documented full breakpoint/keyboard checklist remains incomplete.

### Live public-page spot check (2026-11-15)

The deployed Render site was manually checked at viewport widths 360 px, 768 px, and 1440 px for the event discovery, login, and registration pages. All three pages loaded, had a document title, `lang="en"`, and a primary heading; none showed horizontal overflow. The live DOM inspection found no interactive controls without accessible names and no images missing `alt` text on those pages. Keyboard traversal was checked on registration: navigation links, all four form fields, submit, and sign-in link were reachable, and each focused element showed a visible focus indicator. The login page exposed associated Username and Password fields and a Log in button in the accessibility tree.

This is a limited manual spot check of public pages. It did not cover authenticated attendee/organizer flows, screen-reader operation, 200% zoom/reflow, or a complete color-contrast audit, so EMS-NF-004 remains partial until the full checklist above is completed.

## Current verification boundary

Current local verification: 90 Django tests and 24 RBAC tests passed on 2026-11-15. PostgreSQL CI passed with the capacity/idempotency concurrency assertions and disposable backup/restore rehearsal. PR #35 records the revised local PostgreSQL 16 performance and isolated restore evidence under the owner-approved local scope; it does not claim hosted-provider equivalence. The earlier local SQLite restore also passed on 1,500 events. Remaining Issue #9 evidence: review monitoring cadence and collect the agreed availability observation window; complete the full responsive/keyboard/screen-reader/accessibility checklist; and confirm whether separate team/faculty approval of the revised baseline is required. Hosted provider backup guarantees are not claimed because no hosted database owner/policy has been established. Keep Issue #9 open until the accepted criteria and evidence are reviewed.

## Rahul's isolated PostgreSQL implementation (#32 / #33)

On 2026-11-15 the owner approved local PostgreSQL as the revised acceptance scope and authorized Rahul to execute the benchmarks directly. A rootless Podman baseline now enforces 1 CPU/512 MiB for Gunicorn and 1 CPU/1 GiB for PostgreSQL 16, with swap disabled and effective cgroup limits verified. All 160 search requests succeeded; p95 was 0.171s, 0.359s and 0.795s at 10/50/100 clients. A populated backup restored into a separate PostgreSQL container; all content/count/integrity/migration/readiness checks passed. All 95 Django tests and five script regression tests passed.

See the [formal report](staging/report.md) and [operating runbook](staging/README.md) for full evidence and revised acceptance traceability. Both sub-issues' implementation is complete under that local scope, with the implementation PR ready for review and closure on merge. The report documents actual local backup frequency/retention and audit arrangements, including absent scheduling/encryption/archive guarantees. It does not assert a hosted deployment, provider policy, cloud equivalence, monthly uptime, accessibility conformance or registration stress-test completion. Parent #9 remains open for its other verification.
