# Local PostgreSQL verification results — 2026-11-15

Authoritative run: [20261115T065402Z](evidence/20261115T065402Z/environment.json), executed by `rahulb`. All Python commands used `.venv`; no system Python packages or system database packages were installed. Matching contrib libraries were downloaded/extracted privately. The database and application are stopped after verification (`postgres_stopped: true`).

## Environment and source

- PostgreSQL 18.6; Python 3.14.10; [exact dependencies](evidence/20261115T065402Z/python-packages.txt).
- Linux workstation: 16 logical CPUs, 15.03 GiB reported host RAM. No imposed per-service limits; processes share the host. Cgroup limits are recorded in the environment JSON.
- Gunicorn: two workers, four threads each. PostgreSQL max connections: 120; Django connection reuse: 60 seconds.
- Base revision `321c7924e372b56c0e4098df5623ff2241feaec5` plus this implementation's uncommitted changes at execution. [Source manifest](evidence/20261115T065402Z/source-manifest.json) identifies the exact Python/requirements contents tested; this is not a measurement of the unchanged base commit.
- [Dataset](evidence/20261115T065402Z/dataset.json): 1,500 synthetic events, 1,233 published, 233 published matches for `Sample`, 3,000 ticket tiers, no registrations/payments.

## Search results

Request: `/api/v1/events/?q=Sample&limit=50&offset=0`. Readiness and nonempty search smoke tests passed first. Each series is one synchronized burst, with no failed requests discarded.

| Concurrent clients | HTTP 200 | Failed | p95 | Requests/sec |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 10/10 | 0 | 0.112 s | 88.6 |
| 50 | 50/50 | 0 | 0.178 s | 267.9 |
| 100 | 100/100 | 0 | 0.347 s | 267.3 |

All 160 requests returned HTTP 200. The local series is below the 2-second optimization target. Full JSON reports: [10](evidence/20261115T065402Z/search-10.json), [50](evidence/20261115T065402Z/search-50.json), [100](evidence/20261115T065402Z/search-100.json). Results are local PostgreSQL evidence; they do not establish production-comparable resources, sustained-load behavior, 500-user registration or 10,000-attempt acceptance.

## Isolated restore results

- Backup identifier: `20261115T065402Z/staging.dump`. Private dump size: 122,873 bytes. SHA-256 and timestamps are in the environment JSON.
- Source: `ems_staging`; target: separately created `ems_restore_test` in the same disposable cluster.
- `pg_restore --exit-on-error`: passed in 0.303 seconds. This is restore-command duration, not an approved end-to-end RTO.
- Every public table's row count and content SHA-256 matched; zero invalid indexes and zero unvalidated constraints. See [comparison](evidence/20261115T065402Z/restore-validation.json).
- `pg_amcheck --heapallindexed --parent-check`: passed; [verbose log](evidence/20261115T065402Z/restore-integrity.log). This checks supported heap/B-tree structures, not every PostgreSQL index access method.
- Restored migrations current, Django checks passed, restored application readiness HTTP 200.

## Automated validation

- [95 Django tests passed on PostgreSQL](evidence/20261115T065402Z/postgres-tests.log), including seed guard/refusal/exact-count tests and existing audit, row-lock capacity and idempotency tests.
- [Two benchmark regression tests passed](evidence/20261115T065402Z/script-tests.log): HTTP 503 responses produce a complete error report, and connection refusals are counted.
- Migration drift check and dependency consistency check passed. The separate RBAC project was not changed or rerun.

## Outstanding evidence

No current deployed database/provider or approved production baseline has been supplied. Production-comparable staging, coordinated test-window/baseline approval, provider backup frequency/retention/encryption/access, approved RPO/RTO, deployed audit archive/deletion scheduling and team evidence review remain pending. See the [policy inventory and acceptance matrix](README.md). This work supplies a repeatable local environment, measured search results and isolated logical restore evidence. Do not close Issue #9 or represent #32/#33's external criteria as complete.
