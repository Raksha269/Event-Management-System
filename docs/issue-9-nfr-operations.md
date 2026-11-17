# Issue #9: NFR verification and operations

## Final academic-scope acceptance

The repository owner recorded team acceptance in [Issue #9](https://github.com/Raksha269/Event-Management-System/issues/9#issuecomment-6932891735) and [Issue #38](https://github.com/Raksha269/Event-Management-System/issues/38#issuecomment-6932881938). Both issues are closed against the limited academic-project scope. This records the owner's stated team decision; no separate faculty approval is inferred.

[Issue #37](https://github.com/Raksha269/Event-Management-System/issues/37#issuecomment-6922868953) records the owner's completed responsive/keyboard checks for User Administration and Security Alerts at 320, 360, 768 and 1440 px, NVDA form-error/navigation checks, and confirmation that Manage Tickets responsive and remaining contrast checks were checked. These are user-performed results. Additional numerical contrast measurements or independent retests are not invented here. This acceptance is not a full WCAG certification.

Scheduled evidence is accepted with its gaps retained as UNKNOWN. Consistent 15-minute execution, monthly availability, availability percentages and downtime durations remain unverified. Maintenance exclusions require documented approval. Historical test results and limitations below remain unchanged.

## Scope and status (revised v1.2)

This review follows the team's academic mini-project scope: the verification baseline is the local application and isolated local PostgreSQL. Hosted-service uptime, production load, and provider operations are outside this Issue #9 work. Local readiness checks and isolated PostgreSQL backup/restore remain in scope. Scheduled uptime history is handled separately by [Issue #38](https://github.com/Raksha269/Event-Management-System/issues/38); its workflow and evidence files were not changed in this review.

The revised requirements and verification approach are in the merged SRS, Software Test Plan and SAD. This report distinguishes locally verified criteria from open usability evidence and operational limitations. No production availability, hosted backup policy or WCAG conformance is claimed.

| Requirement | Implementation | Verification and evidence | Status and limits |
| --- | --- | --- | --- |
| **EMS-NF-001 Performance** | Indexed event status/date and PostgreSQL trigram search; bounded opt-in API pagination and compact list serializer; repeatable synchronized search probe. | Owner-approved isolated PostgreSQL 16 run with 1,500 synthetic events, 233 matching published events; 10/50/100 clients all succeeded (160/160), p95 0.171/0.359/0.795 s. See [staging report](staging/report.md), [runbook](staging/README.md), `scripts/nfr_search_benchmark.py`. | **COMPLETE for revised local search benchmark scope.** p95 ≤2 s is documented as an optimization goal, not an acceptance gate. This short read-only search burst is not sustained load or a hosted-service result. |
| **EMS-NF-002 Availability** | `/health/ready/` validates local app/database readiness and returns a request ID; isolated source and restored PostgreSQL applications passed readiness. | `events/health.py`, `events/test_nonfunctional.py::NonFunctionalFoundationTests.test_readiness_checks_database_and_returns_request_id`, PostgreSQL restore evidence in [staging report](staging/report.md), and scheduled evidence in [Issue #38](issue-38-uptime-evidence.md). | **LOCAL READINESS VERIFIED; LIMITED SCHEDULED EVIDENCE ACCEPTED.** The owner recorded team acceptance of sparse samples and scheduling limitations; no continuous or monthly availability claim is made. |
| **EMS-NF-003 Scalability and integrity** | PostgreSQL transactions and row locks protect event/ticket capacity; a unique per-user idempotency constraint prevents duplicate retries. | `events/services.py`, migration `0007`, `events/test_event_management.py::ConcurrentCapacityTests`; PostgreSQL CI and the local staging report record two-worker capacity and idempotency assertions. | **COMPLETE for revised deterministic integrity scope.** The tests demonstrate no oversell/duplicate row in the tested case; no 500/10,000-registration stress run is claimed. SQLite skips the two concurrency tests because it lacks the required row-lock semantics. |
| **EMS-NF-004 Usability and accessibility** | Responsive layouts, named controls, labels, visible focus styling, form error descriptions and focusable error summaries; browser regression coverage. | `events/test_nonfunctional.py`, `events/test_accessibility_errors.py`, and [accessibility verification records](verification/README.md), including local browser/axe findings and user-supplied NVDA reports. | **ACCEPTED FOR SCOPED USER VERIFICATION.** The owner’s #37 closure comment confirms the remaining checks. Preserve the sampled evidence and user-reported provenance; no independent full WCAG audit is claimed. |
| **EMS-NF-005 Audit and recovery** | Append-only `AuditEvent` records, administrator-only read access, a 1,095-day retention setting and purge command; local PostgreSQL dump restored into a separate isolated database. | `events/audit.py`, `events/models.py`, `events/test_nonfunctional.py`; [PostgreSQL backup/restore report](staging/report.md) and backup/restore CI rehearsal. | **COMPLETE for the revised local prototype scope.** Three-year elapsed retention is simulated at the boundary, not observed over three years. The local tool has no automatic archive/purge schedule, encrypted dump or production recovery guarantee; these are explicitly documented as absent. |

### Cross-cutting security and reliability review

Authentication and role checks use Django/DRF authentication and explicit role/owner permissions; forms and serializers validate user-supplied values before writes. The security suite covers lockout, password hashing, payment tokenization, authorization, security alerts, and transport/security settings. Audit and readiness behavior are summarized in EMS-NF-002/005 above. No additional security defect requiring code changes was found in this scoped review. These automated checks are not a penetration test or certification.

### Verification performed in this review

On the Issue #9 branch, the declared project requirements were installed into an ignored `.venv`. `python manage.py check` reported no issues. `python manage.py test` ran **112 tests: 110 passed, 2 skipped** (SQLite concurrency limitations). The separate RBAC suite ran **24/24 passed**. The container resource-limit regression tests passed **3/3**. The benchmark-probe regression suite ran **2 tests: 1 passed and 1 skipped** because this Windows host timed out on a local socket instead of returning a connection-refused result; it still reported the failures as transport errors. The same refusal assertion remains active on environments that return an actual refusal. This local run did not execute PostgreSQL tests; PostgreSQL CI and owner-run isolated-container evidence are linked above.

## Remaining verification handoff (#36–#38)

See the [scoped accessibility and uptime report](verification/README.md) for the browser findings, screen-reader handoff and monitoring history. The report documents limitations and does not certify WCAG conformance or a completed availability window. The local accessibility test evidence does not substitute for the remaining manual checks.

This runbook keeps repeatable local/CI checks separate from items requiring explicit owner approval. Do not use the live Render database for load tests, restore rehearsals, or synthetic data.

## Local PostgreSQL event-search benchmark

The owner-approved local baseline in [the staging runbook](staging/README.md) uses an isolated PostgreSQL 16 container, a synthetic published-event dataset and a resource-limited local application container. Reproduce it only with the guarded local runner:

```bash
python scripts/run_container_staging.py --runtime podman
```

The runner records source/runtime information, dataset counts, response statuses, failures, p50/p95/p99 latency, throughput, backup/restore validation and cleanup. It performs read-only event-search bursts; it does not run registration load or contact a hosted production service. The included generic probe can also be used against a locally authorized endpoint:

```powershell
$env:NFR_BENCHMARK_URL = 'http://127.0.0.1:8000/api/v1/events/?q=Sample&limit=50&offset=0'
$env:NFR_BENCHMARK_CLIENTS = '10'
python scripts/nfr_search_benchmark.py
```

Use a locally isolated database with representative published synthetic events. Preserve all failed responses; do not call an empty-catalogue result representative. The p95 ≤2 seconds figure is an optimization goal under the revised v1.2 acceptance, not a pass/fail threshold. This is a short synchronized burst, not sustained load.

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

## Local readiness and scheduled availability handoff

The included readiness endpoint checks whether the Django application can reach its configured database; the local test asserts HTTP 200, a JSON `{"status":"ok"}` response, and a generated request ID. The owner-run isolated PostgreSQL report records successful readiness both before testing and after restoring into a separate database. These checks verify local readiness behavior, not continuous availability.

As of the **2026-11-16 19:17 UTC** Actions inventory check, four scheduled runs after PR #47 returned HTTP 200 in 31.715020, 32.684809, 31.760717 and 31.598001 seconds. The latest observed run-creation gap was 629.90 minutes (#11→#12); no later scheduled run appeared after 2026-11-16 18:41:19 UTC. These observations show that some checks completed, not that 15-minute cadence or availability was achieved. The later owner acceptance above supersedes the earlier pending decision; the measurements do not establish continuous availability.

Scheduled uptime runs, their raw status/latency samples, cadence gaps and observation-window acceptance belong to [Issue #38](issue-38-uptime-evidence.md). No scheduled uptime percentage, production availability or hosting operations are asserted as Issue #9 local-prototype results. The owner accepted the limited evidence with UNKNOWN gaps and closed #38/#9; scheduled availability remains unverified.

## Isolated backup and restore

The approved local PostgreSQL runner performs a custom-format `pg_dump` and restores it into a separate disposable PostgreSQL container/database. It validates data counts/content hashes, constraints/indexes, migrations, integrity checks and application readiness. See [`docs/staging/report.md`](staging/report.md) for the actual run and [`docs/staging/README.md`](staging/README.md) for reproduction. The PostgreSQL CI workflow also rehearses a dump/restore into a disposable database.

These are local prototype checks. They do not assert hosted-service backup frequency, provider retention, production recovery objectives, encryption guarantees or a recurring backup scheduler. The owner-run report documents the local tool's actual backup and retention arrangements, including controls that are absent. No backup/restore test should point at a shared or hosted database.

A local SQLite development copy can be made without replacing the active file:

```sh
sqlite3 db.sqlite3 ".backup 'db-backup.sqlite3'"
sqlite3 db-backup.sqlite3 "PRAGMA integrity_check;"
```

The historical local SQLite rehearsal returned `ok` and matched the source event count. PostgreSQL 16 is the accepted isolated recovery evidence; the SQLite copy is supplementary.

## Registration integrity and database consistency

`events.test_event_management.ConcurrentCapacityTests` runs two concurrent registration attempts against an event with one remaining ticket and asserts exactly one success, one `Sold Out` rejection, zero remaining capacity, and one active registration. Its idempotency test submits two concurrent retries with the same key and asserts that both resolve to one registration row. The tests passed in the PostgreSQL NFR workflow above and in the local Django suite. This is a small deterministic integrity test, not a high-volume registration stress run.

## Accessibility and usability review

Local browser verification and fixes are recorded in [the verification handoff](verification/README.md). Automated checks cover sampled public/authenticated pages, responsive widths, accessible labels, error-description targets and focus on sampled invalid submissions. User-supplied NVDA reports add observations for selected registration, login, attendee, organizer, discovery and ticket states; they are reported as user-performed evidence, not independently reproduced tests.

**Historical verification boundary before the owner’s final #37 confirmation:** The evidence does not establish full WCAG 2.1 AA conformance. Remaining items include a complete manual color/focus contrast review, repeated authenticated workflows, and independently reproducible assistive-technology checks across the agreed set of flows. Check the handoff's pending list before reporting any additional item as complete.

## Current verification boundary

The full local events suite passed **110 tests with 2 SQLite concurrency skips** (112 discovered), and the separate RBAC suite passed **24 tests** in this review. A missing local dependency initially caused test errors; after installing the already-declared `requirements.txt` into `.venv`, the full suite passed. PostgreSQL concurrency, backup/restore, and local performance evidence is available in the owner-run PostgreSQL 16 staging report and CI; this Windows run did not rerun those PostgreSQL tests because no local container runtime was available.

Issue #9 is **closed under the owner-recorded academic-scope acceptance** linked above. The local prototype work does not require hosted uptime, production load, or provider-managed backup evidence under the revised scope. The owner recorded team acceptance; faculty acceptance is not independently established here.

## Rahul's isolated PostgreSQL implementation (#32 / #33)

On 2026-11-15 the owner approved local PostgreSQL as the revised acceptance scope and authorized Rahul to execute the benchmarks directly. A rootless Podman baseline now enforces 1 CPU/512 MiB for Gunicorn and 1 CPU/1 GiB for PostgreSQL 16, with swap disabled and effective cgroup limits verified. All 160 search requests succeeded; p95 was 0.171s, 0.359s and 0.795s at 10/50/100 clients. A populated backup restored into a separate PostgreSQL container; all content/count/integrity/migration/readiness checks passed. All 95 Django tests and five script regression tests passed.

See the [formal report](staging/report.md) and [operating runbook](staging/README.md) for full evidence and revised acceptance traceability. PR #35 has merged and Issues #32 and #33 are closed under that local scope. The report documents actual local backup frequency/retention and audit arrangements, including absent scheduling/encryption/archive guarantees. It does not assert a hosted deployment, provider policy, cloud equivalence, monthly uptime, accessibility conformance or registration stress-test completion. Parent #9 was subsequently closed under the acceptance linked above.
