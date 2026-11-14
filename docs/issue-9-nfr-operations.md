# Issue #9: NFR verification and operations

This runbook separates repeatable local/CI checks from evidence that requires the deployed service or its database owner. Do not use the live Render database for load tests, restore rehearsals, or synthetic data.

## Event-search load test

Use an isolated staging deployment with representative **published** events, the same database engine and comparable resource limits as production. Confirm the test window and request rate with the deployment owner. The script performs one read-only request per client; it does not create registrations or events.

```powershell
$env:NFR_BENCHMARK_URL = 'https://<staging-host>/api/v1/events/?q=Benchmark&limit=50&offset=0'
$env:NFR_BENCHMARK_CLIENTS = '100'
python scripts/nfr_search_benchmark.py
$env:NFR_BENCHMARK_CLIENTS = '500'
python scripts/nfr_search_benchmark.py
```

Save the full JSON output with the date, deployment revision, dataset size, database engine, and machine/service size. It reports request totals, HTTP status counts, transport failures and connection refusals, average, p50/p95/p99/max latency, wall time, throughput, and whether all requests passed with p95 below 2 seconds. A run with any failed requests is not a pass. Repeat runs and report each result; do not discard a failed run. The included script is a synchronized burst probe, not a sustained-load or registration test.

Local SQLite figures do not establish production/PostgreSQL performance. Do not call a benchmark representative if the search query returns no matching published records.

### Local baseline captured 2026-11-14

Using the local SQLite database (1,500 events total, 1,233 published), the current `main` search code (PR #24 is still separate/open), Waitress (64 threads), and the query `q=Sample&limit=50&offset=0`:

| Concurrent clients | Requests | HTTP 200 | Failed | Average | p50 | p95 | p99 | Throughput | 2 s p95 target |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 100 | 100 | 100 | 0 | 2.219 s | 2.168 s | 3.070 s | 3.100 s | 32.14 req/s | Miss |
| 500 | 500 | 500 | 0 | 7.529 s | 7.490 s | 12.323 s | 12.671 s | 39.21 req/s | Miss |

These synchronized local bursts completed without connection failures, but both miss the latency target and are not a staging acceptance run. The 100-client measurement is consistent with earlier runs being over 2 seconds. Run on the target PostgreSQL staging deployment before drawing a production conclusion.

## Availability monitoring

The GitHub Actions workflow `.github/workflows/uptime-monitoring.yml` checks `/health/ready/` every 15 minutes and on manual dispatch. The endpoint tests the Django process and database connectivity. Each run writes HTTP status and response time to the Actions summary and uploads a one-row CSV artifact for 35 days; failed checks also fail the workflow. Review scheduled run history and outages before calculating monthly availability. A green manual run or a workflow configuration alone is not monthly uptime evidence. This monitor does not page an on-call person; configure an external alert destination with the deployment owner if alerting is required.

The workflow is configured for the repository's Render URL. If the deployment URL changes, update the workflow and check the readiness route before relying on it. A successful HTTP response is one sample, not proof of a 99.5% monthly SLO.

## Backup and restore

### PostgreSQL

The PostgreSQL CI workflow rehearses a custom-format `pg_dump` and restores it into a separate disposable database. This validates the basic tool chain only; it does not prove that the Render database is backed up or meets recovery objectives.

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

## Accessibility and usability review

Automated template tests verify that the discovery search, category, location, and date controls have associated labels. These tests do not constitute a WCAG conformance audit. Before marking the review complete, test all public and authenticated workflows with keyboard-only navigation and a screen reader; check visible focus, heading order, link/button names, image alternatives, form errors, zoom/reflow at 200%, and text/UI contrast against WCAG 2.1 AA. Record browser, assistive technology, pages, findings, and screenshots. Fix issues and rerun the checks.

## Current verification boundary

Repository tests, local SQLite results, and disposable PostgreSQL CI are implementation evidence only. Staging load results, 30 days of availability samples, deployed backup/restore evidence, and the complete manual accessibility review require the deployment/database owner and must be attached to GitHub Issue #9 before it is closed.
