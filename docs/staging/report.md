# Issue #9 — Local PostgreSQL Staging and Recovery Report

**Date:** 2026-11-15

**Owner/operator:** Rahul Biju (`rahulb`)

**Scope:** revised local acceptance for [#32](https://github.com/Raksha269/Event-Management-System/issues/32) and [#33](https://github.com/Raksha269/Event-Management-System/issues/33)

**Delivery:** [PR #34](https://github.com/Raksha269/Event-Management-System/pull/34)

**Disposition:** both sub-issues' implementation and verification are complete under the owner-approved local scope; PR review/merge is the next handoff. Parent #9 remains open for its other NFR work.

## 1. Scope decision and executive assessment

On 2026-11-15 the owner explicitly approved: “Use local PostgreSQL as the revised acceptance scope” and requested a containerized production-comparable environment, performance execution and documentation. This supersedes the earlier requirement to obtain hosted-provider evidence for these two tasks. Rahul executes the tests directly in place of a staging handoff to Rajath. The chosen baseline is a small resource-constrained application/database deployment; no existing production deployment is asserted.

Rootless Podman enforced independent CPU/RAM ceilings for PostgreSQL 16 and Gunicorn. The public-search dataset had matching published events. All 160 requests succeeded and p95 stayed below two seconds at 10/50/100 concurrent clients. A populated backup was restored into a separate PostgreSQL server/container; data and integrity checks and restored application readiness passed. All 95 Django tests and five script regressions passed. All four run-owned containers and their anonymous volumes were removed after validation; private backup/evidence files remain protected locally.

This is a reproducible local acceptance baseline. Shared physical host/kernel/storage, synthetic data and short search bursts limit extrapolation to a future hosted deployment, sustained load or registration stress. Backup/audit controls that are absent are recorded as absent, not presented as configured.

## 2. Baseline and provenance

| Component | Selected baseline | Verified evidence |
| --- | --- | --- |
| Application | Python 3.12 container; DEBUG=false; non-root user; Gunicorn 2 workers × 4 threads | App image recipe, dependency inventory, readiness |
| Application resources | 1 CPU quota; 512 MiB RAM; no swap | `cpu.max=100000 100000`, `memory.max=536870912`, `memory.swap.max=0` |
| Source database | PostgreSQL 16.16 (Debian 16.16-1.pgdg12+1); 64 max connections; 128 MiB shared buffers | Official image, explicit startup configuration and SQL version query |
| Database resources | 1 CPU quota; 1 GiB RAM; no swap | `cpu.max=100000 100000`, `memory.max=1073741824`, `memory.swap.max=0` |
| Recovery target | Separate PostgreSQL container/server/data volume, same resource limits | Matching quota checks and cross-container restore |
| Restored app | Same app image and limits | Readiness and quota checks |
| Load generator | Host `.venv`, outside service quotas | Host package inventory and probe JSON |

CPU quotas bound scheduler time rather than reserve physical cores. [Podman resource controls](https://docs.podman.io/en/stable/markdown/podman-run.1.html) and [Docker's resource documentation](https://docs.docker.com/engine/containers/resource_constraints/) describe these limits. The runner independently verifies effective cgroup values and refuses silently ignored limits. The measured runtime is Podman; Docker is an unexecuted CLI-compatible option.

Authoritative run: [`20261115T071135Z-container`](evidence/20261115T071135Z-container/environment.json). Local execution window: `2026-11-15T07:11:35.801509+00:00` through `2026-11-15T07:13:01.930646+00:00`. Only locally provisioned services received test traffic. The owner's instruction to execute locally supplies authorization for this window; no external deployment operator/test window is required under the revised scope.

Base revision: `2b15e952326437df2be6cd89821a183a780891c2` plus the container implementation present at execution. [Source manifest](evidence/20261115T071135Z-container/source-manifest.json) captures the exact Python/requirements/Containerfile hashes, so these results are not attributed to the unchanged base revision. App image ID: `42be559748a163e3d77b8048f048fc4269fe71d339950ada2e9eb9fb052f6f3e`. Database image ID and registry digests are in environment JSON. [Host packages](evidence/20261115T071135Z-container/host-python-packages.txt) and [app packages](evidence/20261115T071135Z-container/app-python-packages.txt) are separate inventories. All Python dependencies ran in host `.venv` or image `/opt/venv`; no global Python installation was modified.

## 3. Method and dataset

The runner builds the image, provisions a unique source database container, applies migrations, seeds/analyzes data, starts the limited app, verifies cgroup limits/readiness/nonempty search, executes synchronized read-only search bursts, captures stats, stops source traffic, dumps the populated database, provisions a second database server, restores and validates it, starts the restored app, checks migrations/readiness, runs automated tests and removes its own containers/volumes. The [runbook](README.md) contains exact reproduction and credential-free access instructions.

[Dataset evidence](evidence/20261115T071135Z-container/dataset.json): 1,500 synthetic events, 1,233 published, 233 published `Sample` matches, six categories, three venues, varied capacities/prices/statuses, one organizer with an unusable password and 3,000 ticket tiers. No production data, registrations or payments are copied. Fixed future dates use a 2030 anchor. The guard rejects unexpected engines/names/hosts, absent explicit opt-in, existing users/events and repeat seeding.

## 4. Performance findings

Request: `/api/v1/events/?q=Sample&limit=50&offset=0`. Readiness and a nonempty matching response were verified first. Each measurement is one synchronized burst, not a sustained-load run. No failed requests were omitted.

| Concurrent clients | HTTP 200 | Failed | p50 | p95 | Requests/sec |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 10/10 | 0 | 0.158 s | 0.185 s | 54.0 |
| 50 | 50/50 | 0 | 0.172 s | 0.375 s | 114.0 |
| 100 | 100/100 | 0 | 0.430 s | 0.833 s | 115.0 |

All 160 requests returned HTTP 200; transport failures and connection refusals were zero. The two-second optimization target was met in these bursts. Full reports: [10 clients](evidence/20261115T071135Z-container/search-10.json), [50 clients](evidence/20261115T071135Z-container/search-50.json), [100 clients](evidence/20261115T071135Z-container/search-100.json). This does not prove 500-user registration, 10,000 attempts, monthly uptime or accessibility acceptance.

## 5. Backup and recovery findings

| Record | Result |
| --- | --- |
| Source/target | `ems_staging` → `ems_restore_test`, in separate PostgreSQL containers and volumes |
| Operator | `rahulb` |
| Backup identifier | `20261115T071135Z-container/staging.dump` |
| Backup timestamp | `2026-11-15T07:12:08.856113+00:00` to `2026-11-15T07:12:09.015275+00:00` |
| Backup size/SHA-256 | 122,169 bytes; `3077f88d8b45ffc4f1b34c846aea3886fee9cd30ee700f3dc1fb68a065fa5483` |
| Restore timestamp | `2026-11-15T07:12:11.988131+00:00` to `2026-11-15T07:12:12.425356+00:00` |
| Restore-command duration | 0.437 seconds; not an end-to-end incident RTO |
| Data validation | All public-table counts and ordered row-content SHA-256 hashes exactly matched |
| Schema integrity | Zero invalid indexes, zero unvalidated constraints; `pg_amcheck` passed |
| App validation | Restored migrations current, Django checks passed, restored app readiness HTTP 200 |

[Data comparison](evidence/20261115T071135Z-container/restore-validation.json), [heap/B-tree checks](evidence/20261115T071135Z-container/restore-integrity.log), [Django checks](evidence/20261115T071135Z-container/restored-check.log), [migration check](evidence/20261115T071135Z-container/restored-migrations.log) and environment JSON retain the detailed record. `pg_amcheck` covers supported heap/B-tree structures, not every index access method. The backup is custom-format and restored with `--exit-on-error --no-owner --no-acl`. It is never restored over the source.

## 6. Actual backup, retention and audit arrangements (#33)

| Control | Actual local configuration |
| --- | --- |
| Provider/operator | Local rootless Podman; official PostgreSQL 16 image; Rahul operates the session |
| Backup frequency | One on-demand logical dump per verification session after source traffic stops; no recurring scheduler |
| Retention | Manual owner-managed retention under ignored `.staging/`; no automatic expiry or guaranteed duration |
| Access | Random SCRAM password, loopback published ports, owner-only private files; disposable database administrator |
| Encryption | No harness-managed TLS, dump encryption or verified disk encryption; loopback-only use |
| RPO | Recovery to the recorded dump snapshot; no guaranteed time-based RPO or continuous recovery |
| RTO | Restore-command duration measured above; full incident recovery objective is not configured |
| Audit retention | Explicit 1,095-day application setting; audit access/immutability/retention tests passed |
| Archival/deletion | No archive or scheduled purge; application `purge_audit_events` is a manual command |

The task is to document the actual arrangements, including missing controls. No daily backup, encrypted storage, automatic expiry, audit scheduler or approved numerical recovery guarantee is invented. These controls would need separate approval/configuration before a hosted production launch and are outside the owner's revised local acceptance scope.

## 7. Validation and cleanup

- [95 Django tests passed against containerized PostgreSQL 16](evidence/20261115T071135Z-container/postgres-tests.log), including seed-safety, audit, capacity-lock and idempotency tests.
- [Five script regressions passed](evidence/20261115T071135Z-container/script-tests.log): HTTP/transport error reporting plus acceptance/rejection of actual CPU/memory limits.
- Source hashes, local documentation links and whitespace checks were verified before commit. No application behavior changed after this measured run.
- Evidence confirms all four run-owned containers and volumes were removed. Private dumps/env/logs remain outside Git; cached images are intentionally retained for reproduction. No unrelated containers were changed.
- Project bytecode caches were removed. Retained Python files implement repeatable setup/probing or regression checks; no one-off scratch Python files are included.

## 8. Revised acceptance traceability

| Revised criterion | Evidence | Disposition |
| --- | --- | --- |
| #32: isolated PostgreSQL and production-comparable local resource baseline, source/environment recorded | Independent enforced quotas, image IDs/digests, source manifest, environment JSON | Complete |
| #32: representative synthetic published events and matching query | Dataset and nonempty search smoke test | Complete for public event search |
| #32: authorized local test window/rate; Rahul executes tests | Owner-approved local scope and self-execution; timestamped 10/50/100-client reports | Complete |
| #32: access process and setup/evidence PR | Runbook, one-command local access, PR #34 | Complete; PR review/merge next |
| #33: identify local database/provider/operator | Podman/image/version/operator evidence | Complete |
| #33: document actual backup frequency, retention, encryption/access and recovery objectives | Inventory above and environment JSON; absent controls explicitly disclosed | Complete |
| #33: document actual audit retention/archive/deletion | Explicit application setting distinguished from absent archive/scheduler | Complete |
| #33: authorized restore into a separate isolated database with required record | Separate server/container restore, backup metadata, timing, data/integrity/migration/readiness evidence | Complete |
| #33: documentation/evidence PR, unavailable hosted evidence clearly excluded | This report, runbook, raw evidence and PR #34 | Complete; PR review/merge next |

Both assigned sub-issues are ready for completion under the explicitly revised local scope. Their GitHub criteria should record this amendment, and closure should follow PR merge. Parent #9 remains open for its other NFR verification. Original unrestricted native results remain in the [historical report](history/native-verification-report.md) with unchanged raw evidence; they are superseded as acceptance evidence by this quota-controlled run.
