# Issue #9: NFR verification and operations

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

The v1.2 document set in [PR #29](https://github.com/Raksha269/Event-Management-System/pull/29) labels the revised acceptance as a reproducible report with no unreported errors; p95 <= 2 seconds is an optimization goal, not a pass condition. It still calls the representative PostgreSQL staging series pending. This local SQLite series is reproducible evidence, but it does not replace that staging run. PR #29 is a candidate pending team/faculty approval, so do not treat its revised criteria as formally adopted until approved.

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

## Backup and restore

### PostgreSQL

The PostgreSQL CI workflow rehearses a custom-format `pg_dump` and restores it into a separate disposable database. The latest successful main-branch PostgreSQL run [#43626022835](https://github.com/Raksha269/Event-Management-System/actions/runs/43626022835) completed that rehearsal and the application suite. This verifies the CI backup/restore procedure, not that the Render database is backed up or meets recovery objectives.

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

PR #26 reports muted text contrast improved from 4.39:1 to 6.99:1. The previous local responsive spot checks and filter-label tests are useful supporting evidence, but the v1.2 candidate's documented full breakpoint/keyboard checklist remains incomplete.

## Current verification boundary

Current local verification: 90 Django tests and 24 RBAC tests passed on 2026-11-15. PostgreSQL CI also passed with the capacity/idempotency concurrency assertions and the disposable backup/restore rehearsal. Local SQLite restore validation passed on 1,500 events. Remaining v1.2 candidate evidence: representative PostgreSQL staging performance run; review of monitoring cadence and a suitable observation window; deployed database recovery/retention policy review; full responsive/keyboard/accessibility checklist; and team/faculty approval of PR #29's revised baseline. Record results in Issue #9; do not close it until the accepted criteria and evidence are reviewed.

## Rahul's isolated PostgreSQL implementation (#32 / #33)

The owner reports that there is currently no deployed application/database to administer. Existing Render references above are historical evidence, not verification of a current deployed PostgreSQL database or its policy. See [the isolated staging runbook](staging/README.md), [implementation plan](staging/implementation-plan.md) and [local evidence summary](staging/results.md) for the reproducible PostgreSQL environment, synthetic dataset, search measurements and separate-database restore checks. These are local PostgreSQL results and do not establish production comparability, provider-managed backups, deployed audit archival/deletion, or overall Issue #9 completion. Keep those external criteria pending.
