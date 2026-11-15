# Issues #32 and #33 — implementation and completion plan

Owner/operator: Rahul. Delivery: [PR #34](https://github.com/Raksha269/Event-Management-System/pull/34). Formal findings: [report](report.md); reproduction: [runbook](README.md).

## Approved scope amendment

On 2026-11-15 the owner instructed: “Use local PostgreSQL as the revised acceptance scope” and requested a production-comparable container environment with performance execution/documentation. Rahul executes the work directly. Hosted deployment/provider verification is superseded for these two sub-issues; no real production equivalence or hosted backup guarantee is asserted.

## Completed implementation

- [x] Run host Python in `.venv` and served app Python in container `/opt/venv`.
- [x] Create an isolated PostgreSQL 16 source container and Gunicorn app image, with loopback-only published access and random protected credentials.
- [x] Establish the local baseline: app 1 CPU/512 MiB; database 1 CPU/1 GiB; no swap; verify actual cgroup limits rather than relying on requested CLI settings.
- [x] Seed 1,500 synthetic events (1,233 published, 233 published `Sample` matches) and 3,000 ticket tiers, with explicit database/opt-in/empty-dataset guards.
- [x] Apply migrations, analyze, check readiness/nonempty search and execute timestamped 10/50/100-client bursts outside service quotas; retain all errors and full reports.
- [x] Dump source and restore into a second isolated PostgreSQL server/container/volume; compare row counts/content hashes, verify constraints/indexes, run heap/B-tree checks, and verify restored migrations/readiness.
- [x] Document actual local backup frequency, retention, encryption/access, RPO/RTO and audit retention/archive/deletion, including absent controls.
- [x] Pass 95 Django tests on PostgreSQL 16 and five script regressions, including resource-limit validation.
- [x] Retain source/image/package evidence; remove run-owned containers/volumes and project bytecode caches; keep private dumps/credentials out of Git.
- [x] Deliver the formal report, organized operating instructions, implementation and raw evidence on the issue branch.

## PR and issue handoff

Update PR #34 and both issue bodies to record the scope amendment and completed local acceptance. PR #34 should close #32 and #33 on merge, leaving review/merge to the owner. Parent #9 stays open for its other requirements. Do not label absent scheduled backups, encryption, archives, recovery objectives or future hosted controls as implemented.

The initial native PostgreSQL run is retained as historical evidence. The authoritative resource-limited run is `20261115T071135Z-container`; see the report for exact metrics and validation.
