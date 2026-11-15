# Historical native PostgreSQL verification report

Superseded by the owner-approved resource-controlled local scope; see the [current report](../report.md). Status statements below describe the scope before that revision.

**Report date:** 2026-11-15

**Owner/operator:** Rahul Biju (`rahulb`)

**Assigned sub-issues:** [#32](https://github.com/Raksha269/Event-Management-System/issues/32) and [#33](https://github.com/Raksha269/Event-Management-System/issues/33)

**Implementation:** commit `56d2bae`; [draft PR #34](https://github.com/Raksha269/Event-Management-System/pull/34)

**Disposition:** local implementation and verification complete; original deployment-dependent acceptance remains incomplete.

## 1. Executive assessment

The isolated local PostgreSQL environment, synthetic dataset, performance measurements and separate-database restore verification have been implemented and tested. All 160 search requests succeeded, 95 Django tests and two probe regression tests passed, and restored data matched the source. Both PR CI workflows passed.

The owner reports that no deployed application/database exists. Accordingly, this report documents the local backup and audit configuration as observed, and records deployment-specific requirements as pending. Neither sub-issue can be certified complete under its currently published acceptance criteria. No issue closure, merge or deployment is performed by this report.

## 2. Objective and method

The objective of #32 is isolated PostgreSQL staging with representative published events for performance verification. The objective of #33 is evidence of the deployed database backup/recovery and audit-retention arrangements, including a restore into a separate isolated database.

The method was to provision an unprivileged disposable cluster, migrate Django, generate synthetic records, analyze tables, start Gunicorn, verify readiness and nonempty search, execute synchronized search bursts, stop the source app, dump the populated database, restore into a separately created database, compare table content/counts, run integrity checks, and verify restored migrations/readiness. Automated tests ran against PostgreSQL. Services were stopped after verification. Python dependencies and commands ran in `.venv`; native database utilities used an isolated data directory. See the [operating runbook](../README.md) for reproduction and access.

Authoritative run: [20261115T065402Z](../evidence/20261115T065402Z/environment.json), executed by `rahulb`. All Python commands used `.venv`; no system Python packages or system database packages were installed. Matching contrib libraries were downloaded/extracted privately. The database and application are stopped after verification (`postgres_stopped: true`).

## 3. Environment and source

- PostgreSQL 18.6; Python 3.14.10; [exact dependencies](../evidence/20261115T065402Z/python-packages.txt).
- Linux workstation: 16 logical CPUs, 15.03 GiB reported host RAM. No imposed per-service limits; processes share the host. The runner records cgroup limits when exposed at `/sys/fs/cgroup`; no cgroup limit fields were present in this run, so inherited container quotas were not verified.
- Gunicorn: two workers, four threads each. PostgreSQL max connections: 120; Django connection reuse: 60 seconds.
- Base revision `321c7924e372b56c0e4098df5623ff2241feaec5` plus this implementation's uncommitted changes at execution. [Source manifest](../evidence/20261115T065402Z/source-manifest.json) identifies the exact Python/requirements contents tested; this is not a measurement of the unchanged base commit.
- [Dataset](../evidence/20261115T065402Z/dataset.json): 1,500 synthetic events, 1,233 published, 233 published matches for `Sample`, 3,000 ticket tiers, no registrations/payments.

## 4. Performance findings

Request: `/api/v1/events/?q=Sample&limit=50&offset=0`. Readiness and nonempty search smoke tests passed first. Each series is one synchronized burst, with no failed requests discarded.

| Concurrent clients | HTTP 200 | Failed | p95 | Requests/sec |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 10/10 | 0 | 0.112 s | 88.6 |
| 50 | 50/50 | 0 | 0.178 s | 267.9 |
| 100 | 100/100 | 0 | 0.347 s | 267.3 |

All 160 requests returned HTTP 200. The local series is below the 2-second optimization target. Full JSON reports: [10](../evidence/20261115T065402Z/search-10.json), [50](../evidence/20261115T065402Z/search-50.json), [100](../evidence/20261115T065402Z/search-100.json). Results are local PostgreSQL evidence; they do not establish production-comparable resources, sustained-load behavior, 500-user registration or 10,000-attempt acceptance.

## 5. Recovery findings

- Backup identifier: `20261115T065402Z/staging.dump`. Private dump size: 122,873 bytes. SHA-256 and timestamps are in the environment JSON.
- Source: `ems_staging`; target: separately created `ems_restore_test` in the same disposable cluster.
- `pg_restore --exit-on-error`: passed in 0.303 seconds. This is restore-command duration, not an approved end-to-end RTO.
- Every public table's row count and content SHA-256 matched; zero invalid indexes and zero unvalidated constraints. See [comparison](../evidence/20261115T065402Z/restore-validation.json).
- `pg_amcheck --heapallindexed --parent-check`: passed; [verbose log](../evidence/20261115T065402Z/restore-integrity.log). This checks supported heap/B-tree structures, not every PostgreSQL index access method.
- Restored migrations current, Django checks passed, restored application readiness HTTP 200.

## 6. Automated validation

- [95 Django tests passed on PostgreSQL](../evidence/20261115T065402Z/postgres-tests.log), including seed guard/refusal/exact-count tests and existing audit, row-lock capacity and idempotency tests.
- [Two benchmark regression tests passed](../evidence/20261115T065402Z/script-tests.log): HTTP 503 responses produce a complete error report, and connection refusals are counted.
- Migration drift check and dependency consistency check passed. The separate RBAC project was not changed or rerun.

## 7. Backup and audit operations inventory

These are observed local settings, not approved production policy.

| Control | Observed setup | Evidence / limitation |
| --- | --- | --- |
| Provider/operator | Native PostgreSQL 18.6, local operator `rahulb` | Environment JSON; no deployed provider confirmed |
| Backup frequency | One on-demand dump per successful harness session | Backup log and timestamps; no recurring scheduler |
| Backup retention | Manual retention in ignored `.staging/`; no configured expiry | Local file lifecycle; no approved retention duration |
| Backup integrity | SHA-256, successful separate-database restore, table hashes/counts and `pg_amcheck` | Raw evidence linked above |
| Encryption | SCRAM authentication; no harness-managed TLS or encrypted dump | Loopback-only service; disk encryption unverified |
| Access | Random password, owner-only run directories, disposable administrator | Harness source; deployed least-privilege role unverified |
| RPO | No approved objective | Local recovery point is the dump snapshot; scheduled recovery-point coverage unverified |
| RTO | No approved objective | Restore command took 0.303 seconds; full incident recovery unmeasured |
| Audit retention | Explicit 1,095-day setting | Harness and existing audit-boundary tests |
| Audit archival/deletion | No archive or purge scheduler configured | Application purge command exists; deployed configuration unavailable |

## 8. Acceptance traceability and delivery

Criteria were read from GitHub on 2026-11-15. A passed local test does not override a requirement for a deployed system or an agreement with other operators.

| Issue / criterion | Assessment | Evidence or remaining action |
| --- | --- | --- |
| #32: isolated PostgreSQL, production-comparable limits, revision/environment | Partial | Isolation and source/environment evidence supplied; comparable production baseline absent |
| #32: synthetic published events and matching benchmark query | Verified locally | Dataset JSON and search smoke test; broader distribution suitability requires review |
| #32: agreed test window/request rate with Rajath and deployment owner | Pending external agreement | Rahul executed local bursts as requested; no deployment owner or recorded team agreement supplied |
| #32: documented access and setup/evidence PR | Delivered for review | Runbook and draft PR #34; loopback access through local reproduction, no persistent shared endpoint |
| #33: deployed database/provider and operator | Pending | No deployment supplied; local engine/operator identified |
| #33: actual deployed backup configuration and recovery objectives | Pending | Local inventory recorded above; deployed controls and approved RPO/RTO absent |
| #33: deployed audit retention and archival/deletion | Pending | Application retention distinguished from missing operational scheduler/archive |
| #33: authorized isolated restore and complete verification record | Verified locally; deployed-backup evidence pending | Source/target names, operator, timestamp, revision, backup identifier, duration, checks and readiness captured |
| #33: documentation/evidence PR, unavailable evidence pending | Delivered for review | Draft PR #34 and this report |

Both GitHub issues remain open. PR #34's Django CI and PostgreSQL NFR checks passed for implementation commit `56d2bae`: [Django CI](https://github.com/Raksha269/Event-Management-System/actions/runs/43688089590) and [PostgreSQL CI](https://github.com/Raksha269/Event-Management-System/actions/runs/43688089642). The PostgreSQL CI uses version 16, complementing the local version-18 run; CI does not execute the full local staging harness.

### Repository organization and cleanup

- `config/staging_settings.py`: guarded loopback staging configuration.
- `events/management/commands/seed_postgres_staging.py`: repeatable guarded fixture generator.
- `events/test_staging.py`: database guard and dataset regression checks.
- `scripts/run_postgres_staging.py`: reusable staging/benchmark/restore orchestration.
- `scripts/nfr_search_benchmark.py` and `scripts/test_nfr_search_benchmark.py`: reusable probe and failure-reporting checks.
- `docs/staging/README.md`: operating instructions; this report: findings and acceptance traceability; `implementation-plan.md`: execution plan; `evidence/<run-id>/`: raw records.
- Python bytecode caches outside `.venv` were removed. No temporary one-off Python source files were found; the retained Python files are required implementation or tests. The superseded PR-description scratch document was removed after PR publication.
- `.venv` and ignored `.staging/` are intentionally retained: they contain dependencies and isolated database/backup artifacts needed for reproduction and evidence retention. None are committed. Historical evidence is preserved unchanged.

## 9. Conclusion and remaining decisions

No current deployed database/provider or approved production baseline has been supplied. Production-comparable staging, coordinated test-window/baseline approval, provider backup frequency/retention/encryption/access, approved RPO/RTO, deployed audit archive/deletion scheduling and team evidence review remain pending. See the [policy inventory and acceptance matrix](../README.md). This work supplies a repeatable local environment, measured search results and isolated logical restore evidence. Do not close Issue #9 or represent #32/#33's external criteria as complete.
