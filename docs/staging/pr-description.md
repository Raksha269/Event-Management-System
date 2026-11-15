## Summary

Issues #32 and #33 require environment-backed NFR evidence, but no current deployed database or production resource baseline has been supplied. Add a repeatable local PostgreSQL staging harness that seeds a guarded synthetic dataset, runs search probes and restores a populated backup into a separate database.

- Run all Python tooling in `.venv`; isolate PostgreSQL data, credentials and dumps under ignored `.staging/` with loopback-only services and automatic shutdown.
- Seed 1,500 synthetic events (1,233 published, 233 published `Sample` matches) plus 3,000 ticket tiers. Reject unexpected databases and existing datasets.
- Capture environment/source hashes, complete benchmark reports, backup identity/timing, table counts/content hashes, physical heap/B-tree integrity checks, migration state and restored application readiness.
- Fix benchmark HTTP-error handling so HTTP failures are reported instead of crashing; add regression and seed-safety tests.
- Document reproduction, local backup/audit configuration, evidence and deployment-dependent gaps.

## Validation

- Full local PostgreSQL 18.6 run: 95 Django tests and two benchmark regression tests passed.
- Search bursts: all 160 requests HTTP 200; p95 0.112s / 0.178s / 0.347s at 10 / 50 / 100 clients.
- Populated backup restored into `ems_restore_test`; all public table counts and content hashes matched, `pg_amcheck` passed, restored migrations/checks/readiness passed.
- `pip check`, migration drift and `git diff --check` passed.

Evidence and exact limitations: `docs/staging/results.md`. Implementation plan and policy inventory: `docs/staging/implementation-plan.md` and `docs/staging/README.md`.

## Remaining acceptance

Refs #9, #32, #33. No auto-close: this is local PostgreSQL verification, not a hosted or production-comparable deployment. Team agreement on the baseline/test scope, current deployed provider/operator, actual scheduled backup/retention/encryption/access, approved RPO/RTO and deployed audit archival/deletion remain pending. Rajath/team review of the evidence is still required. Overall Issue #9 also retains its other verification requirements.
