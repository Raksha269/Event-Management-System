# Local PostgreSQL staging operations

The owner approved **local PostgreSQL as the revised acceptance scope for #32 and #33** on 2026-11-15. The [formal report](report.md) records the acceptance baseline, measurements, backup/audit inventory and traceability. No hosted deployment or provider backup policy is claimed.

## Resource-controlled baseline

| Service | CPU quota | RAM ceiling | Configuration |
| --- | --- | --- | --- |
| Django/Gunicorn | 1 CPU | 512 MiB | DEBUG=false; 2 workers, 4 threads/worker; non-root app user |
| PostgreSQL source | 1 CPU | 1 GiB | PostgreSQL 16; 64 connections; 128 MiB shared buffers |
| PostgreSQL restore | 1 CPU | 1 GiB | Separate container/server with its own data volume |
| Restored application | 1 CPU | 512 MiB | Same application image and Gunicorn configuration |

Swap is disabled in each container. The runner reads `cpu.max`, `memory.max` and `memory.swap.max` inside each service and fails if limits are missing or differ from the baseline. CPU quota is scheduler time equivalent to one core, not a dedicated physical core. The load generator runs in the host `.venv` outside service quotas; all containers still share the physical workstation, kernel and storage.

This is the project's selected local production-comparable baseline, not measured equivalence to a future cloud service. Source and restore database containers share no database volume. Only randomly allocated loopback ports are published; application containers share their respective database container's network namespace, preserving the guarded `127.0.0.1` database configuration. There is no public URL or TLS proxy.

## Reproduce

Prerequisites: rootless Podman with delegated cgroup-v2 CPU/memory controllers, or Docker on Linux with equivalent controls. Runtime access and image downloads may require permission. No system Python packages are installed.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
podman pull docker.io/library/postgres:16-bookworm
.venv/bin/python scripts/run_container_staging.py --runtime podman
```

For Docker, replace the pull command with `docker pull ...` and select `--runtime docker`. Podman was actually tested; Docker compatibility is provided by the common CLI flags but was not independently executed here. Run one staging job at a time because the local app image tag is shared.

The app image recipe is `infra/staging/Containerfile`. It creates `/opt/venv`, installs the project requirements there, copies only application source and runs as user `ems` (UID 10001). `.containerignore` and `.dockerignore` exclude credentials, databases, host virtual environments, Git metadata and evidence from build context. The host orchestrator, seeder, migrations, probes and tests all use `.venv`; the served application uses the container `/opt/venv`.

The workflow builds the app image, records image IDs/digests and source hashes, starts isolated PostgreSQL, migrates/seeds/analyzes it, starts Gunicorn, verifies quotas/readiness/search, runs 10/50/100-client bursts, captures service stats, stops source traffic, takes a custom-format backup, restores to the second server, compares public-table counts/content hashes, checks constraints/indexes/heap integrity, starts the restored app, checks migrations/readiness and runs the Django and script regression suites. Normal completion/failure cleanup removes only uniquely named containers and anonymous volumes created by that run. Check the evidence's `containers_removed` field. Abrupt termination such as host power loss may require manual removal of the uniquely named `ems-*` containers identified in that run's private logs; never remove unrelated containers.

## Data, access and evidence

The seed command requires `EMS_ISOLATED_STAGING=synthetic-only`, loopback PostgreSQL, exact database name `ems_staging`, and an empty user/event dataset. It refuses a repeat invocation. The fixed fixture contains 1,500 events, 1,233 published, 233 published matches for `Sample`, six categories, three venues, varied capacities/prices, mixed statuses, one organizer with an unusable password and 3,000 ticket tiers. It has no registrations/payments and uses a fixed 2030 date anchor. This dataset represents public event search, not all production workloads.

Access is through the local command above. Rahul owns and executes this environment and its read-only probe within the test window recorded in the environment JSON. The owner authorized self-execution in place of Rajath's original handoff. Results can be reviewed through the report/PR without sharing secrets. No persistent shared staging endpoint is required under the revised scope.

Sanitized evidence lives in `docs/staging/evidence/<UTC-run-id>-container/`. Private environment files, random credentials, dumps and service logs live in ignored `.staging/<run-id>/`, with owner-only permissions. Container images remain cached locally for reproduction; database volumes are removed after validation. A retained dump can be restored by a new verification session; re-creating that session starts with fresh credentials and data. Do not commit private artifacts. Review all raw logs before publishing evidence.

Host and app Python dependency inventories are recorded separately; tags/requirements are not immutable over time, so retain the recorded image digests and package inventories for historical comparisons. Search results are synchronized bursts, not sustained-load or registration throughput measurements. Preserve all failed responses and latencies. A p95 below two seconds applies to the recorded local bursts only.

## Actual local backup and audit arrangements

- Backup frequency: one on-demand `pg_dump` per verification session, after the source app stops; no recurring scheduler.
- Retention: private dump retained until the owner manually removes it; no automatic expiry or guaranteed retention duration.
- Access/encryption: random SCRAM password, loopback-only connections, protected local files. No harness-managed TLS, encrypted dump or verified disk encryption. The disposable database administrator can create test databases/extensions; it is not a production least-privilege role design.
- RPO: recover to the recorded dump snapshot; no guaranteed time-based RPO or point-in-time recovery.
- RTO: measured restore-command duration in the report; no full incident-recovery guarantee.
- Audit: explicit 1,095-day application setting, with existing access/immutability/retention-boundary regression tests. No archive or purge scheduler is installed; `purge_audit_events` is manual. Do not imply that the application setting creates a scheduler or archive.

These are documented observations, including absent controls, and satisfy the revised task to document the local setup. A hosted production launch would require a separately approved recurring backup/retention, encryption/access, archival/deletion and recovery-objective policy.

## Historical native setup

`scripts/run_postgres_staging.py` remains a reusable non-container fallback. It requires matching installed PostgreSQL server/client/contrib utilities and does not impose service CPU/RAM quotas. It is not the acceptance baseline. The workstation's native PostgreSQL 18.6 required a matching Fedora contrib RPM extracted under `.staging/pg-extra`, without system installation. Its private extension search uses PostgreSQL 18's [extension-control path](https://www.postgresql.org/docs/18/runtime-config-client.html#GUC-EXTENSION-CONTROL-PATH). Do not use that extraction with PostgreSQL 16. The container run avoids this workstation-specific setup entirely.

The original report and unchanged raw evidence remain as historical records. Issue #9's other NFRs, including monthly availability, accessibility and any required registration stress tests, are outside these two revised sub-issues.
