# Isolated PostgreSQL staging and recovery

This implements the local environment and evidence portion of issues #32 and #33. The owner reports there is no deployed application/database. Historical Render references in the main runbook and monitoring workflow are not confirmation of current ownership, configuration or database availability. Do not infer a production backup policy from them.

## Reproduce

Python must run in the repository virtual environment. Native PostgreSQL is a separate isolated database service, not a Python package. Required native utilities: `initdb`, `pg_ctl`, `pg_dump`, `pg_restore` and `pg_amcheck`, plus matching `pg_trgm` and `amcheck` extensions. PostgreSQL 16 with contrib matches CI; this workstation has PostgreSQL 18.6.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/run_postgres_staging.py
```

For exact Python versions used in the recorded run, use its `python-packages.txt` in a fresh virtual environment. Existing `requirements.txt` remains the application's supported dependency range.

The command provisions a fresh cluster for every run. It binds only `127.0.0.1`, chooses free TCP ports, disables Unix sockets, uses a random SCRAM password, and creates `ems_staging` and `ems_restore_test`. No existing database or cloud credentials are used. It runs migrations, seeds, collects static assets, checks readiness/search, executes 10/50/100-client probes, dumps/restores, verifies row counts/content hashes/indexes/constraints, runs `pg_amcheck`, checks restored migrations/readiness, then runs the full Django suite on PostgreSQL and script regression tests. It stops Gunicorn and PostgreSQL on completion or failure. Check `environment.json` for the result and cleanup status.

There is no long-lived shared URL: this is a self-contained local test session. Rahul executes it and Rajath/team review the evidence. Sharing a hosted environment later requires a separate deployment and access arrangement. Agree on an idle local test window; no external service is targeted by this runner. `--clients 10` can shorten an investigative run; `--skip-tests` explicitly records skipped tests and must not be represented as full verification.

Private cluster data, generated credentials, application logs, media and dumps remain under ignored `.staging/`, with owner-only permissions. Evidence is written to `docs/staging/evidence/<UTC-run-id>/`. Review evidence before committing; do not commit dumps, private logs or real data. The staging settings bypass HTTPS only for this loopback harness; do not use them for an internet-facing deployment. The cluster user is its disposable administrator so it can create databases/extensions/test databases; a deployed application needs a separate restricted role.

### This Fedora workstation's isolated contrib package

The installed server lacked contrib. A matching `postgresql-contrib-18.6-1.fc44.x86_64.rpm` was downloaded without system installation and extracted under `.staging/pg-extra`. To reproduce on the same Fedora version, download the matching package with `dnf download` into `.staging/packages`, with DNF cache/log/persistent directories also redirected under `.staging`, then:

```bash
mkdir -p .staging/pg-extra
rpm2cpio .staging/packages/postgresql-contrib-18.6-1.fc44.x86_64.rpm | cpio -id --quiet -D .staging/pg-extra
```

The runner detects that layout, rewrites only the private `pg_trgm`/`amcheck` control files to their extracted libraries, and sets PostgreSQL 18's private extension search path. The configured search entries contain an `extension` subdirectory, as required by [PostgreSQL's documentation](https://www.postgresql.org/docs/18/runtime-config-client.html#GUC-EXTENSION-CONTROL-PATH). This fallback is Fedora/PostgreSQL-18-specific. On PostgreSQL 16, use matching installed contrib utilities and omit the private extraction directory. Never mix server/library major versions.

## Dataset and benchmark interpretation

The guarded `seed_postgres_staging` command requires explicit `EMS_ISOLATED_STAGING=synthetic-only`, loopback PostgreSQL, the exact database name `ems_staging`, and no existing users/events. A second invocation refuses to change data. To regenerate, run the harness again, creating a fresh cluster; do not clear an existing database.

The fixture has 1,500 events, 1,233 published, 233 published matches for `Sample`, six categories, three venues, varied capacities/prices, mixed statuses, one organizer with an unusable password and 3,000 ticket tiers. Dates use a fixed 2030 anchor for reproducibility. It contains no registrations/payments and does not model heavy attendee histories or all production distributions. Revisit the fixture before claiming broader representativeness.

Gunicorn uses two workers with four threads each. Database connection limit: 120; Django connection reuse: 60 seconds. No harness-imposed CPU/RAM quotas exist. Database, application and load generator share the workstation and OS scheduling. This is a synchronized burst search probe, not sustained load, 500 concurrent registrations or 10,000 attempts. Preserve failed-request counts and full latency reports. The recorded local p95 values do not establish hosted or production performance or overall Issue #9 acceptance.

## Backup, recovery and audit policy inventory (#33)

| Item | Verified local setup | Deployed configuration |
| --- | --- | --- |
| Database/operator | Disposable native PostgreSQL; local OS user recorded per run | No deployed database/provider/operator confirmed; pending |
| Backup frequency | One on-demand `pg_dump` per successful harness run; no scheduler | Pending |
| Backup retention | Private dump retained until manually removed; no automatic expiry | Pending approved retention policy |
| Encryption | SCRAM authentication; loopback transport and dump are not encrypted by this harness; host disk encryption unverified | Pending encryption-at-rest/in-transit evidence |
| Access | Loopback listener, random password, owner-only staging directory; disposable DB administrator | Pending deployed role/access review |
| Recovery point objective | No approved target; dump snapshot is the local recovery point | Pending approved RPO and measured backup age |
| Recovery time objective | Restore duration measured; excludes infrastructure provisioning, incident detection and traffic cutover | Pending approved RTO and full recovery timing |
| Audit retention | Explicit 1,095-day application setting in harness; audit boundary tests in main suite | Pending deployed environment inspection |
| Audit deletion | `purge_audit_events` exists; not scheduled by harness | Pending scheduler/operator evidence |
| Audit archive | No archive configured by harness | Pending archival/deletion policy |

The runner restores a custom-format backup into `ems_restore_test` with `--exit-on-error --no-owner --no-acl`. It compares every public table's row count and ordered row-content SHA-256 against the source, checks validated constraints/indexes, runs `pg_amcheck`, checks pending migrations, and starts the restored app to verify `/health/ready/`. Backup ID/SHA-256, source revision, operator, timestamps, duration and validation are recorded. Backup files contain synthetic data only. This verifies logical recovery within the same local PostgreSQL cluster, not provider failover or disaster recovery on another host.

No production purge, live restore, external messages or monitoring configuration changes are performed. Do not configure an archival/deletion schedule until the team approves the policy. Manual dump retention is an observed local fact, not a proposed production policy.

## Completion and PR review

| Acceptance item | Status |
| --- | --- |
| Isolated PostgreSQL, repeatable synthetic seed, matching search, benchmark execution | Implemented and locally verified; see evidence summary |
| Recorded revision/environment and credential-free access process | Implemented; source starts/stops locally, no shared credentials |
| Production-comparable resource baseline | Pending team agreement; no production environment exists |
| Test scope/window agreement and independent evidence review | Pending Rajath/team review; only local resources were exercised |
| Isolated backup/restore evidence | Locally verified, with synthetic data |
| Actual deployed backups, retention, encryption/access, RPO/RTO | Pending deployment and operator evidence |
| Deployed audit retention/archive/deletion | Pending deployment and policy approval |

Use one PR referencing #32 and #33, with no auto-close keywords while the external criteria remain pending. Include the plan, harness, seed command/tests, benchmark error fix/regressions, runbook and sanitized evidence. Rajath/team should review dataset suitability, baseline, accepted NFR document version and whether local evidence satisfies any criteria. Issue #9 remains open for other verification, including accessibility/availability and any required registration load tests.
