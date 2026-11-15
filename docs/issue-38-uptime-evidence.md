# Issue #38: uptime cadence and evidence status

**Status: INCOMPLETE.** Issue #38 and parent Issue #9 remain open. This report reflects repository main at `1b1420c9` and the Actions run inventory available at **2026-11-15 18:55:08 UTC**. The latest available Actions API inventory returned seven runs; the repository's preserved archive also contains Run #8, which is no longer returned by the live run-list API. No workflow was manually dispatched for this review.

## Acceptance criteria

| Criterion | Status | Evidence / remaining work |
| --- | --- | --- |
| Inspect scheduled Actions history, investigate multi-hour gaps, document findings and corrections | **INCOMPLETE** | Runs and archived Run #8 were reviewed. The workflow is active on default branch `main`; cron is `7,22,37,52 * * * *` UTC. The available history has large run-creation gaps. Actions policy settings could not be read (API 403), so the scheduling root cause is unknown. |
| Agree observation period, cadence, availability calculation, missing-sample and maintenance rules with the team | **WAITING FOR TEAM APPROVAL** | The existing Issue #38 comment requests these decisions, but no approval is recorded. A scope clarification is also required; see below. |
| Preserve timestamped status/latency evidence throughout the agreed period, including failures and missed checks | **INCOMPLETE** | Six archived CSV samples are retained: four scheduled and two manual. All six show HTTP 200 / UP. Scheduled observations are sparse; missed nominal slots remain UNKNOWN. Run #8 failed before an HTTP probe and has no CSV. |
| Summarize coverage, downtime, gaps and limitations; calculate availability only with an agreed method and sufficient data | **INCOMPLETE** | Creation gaps among scheduled runs with probes were 310.52, 235.50 and 209.08 minutes. Gap from scheduled Run #5 to failed Run #8 was 858.98 minutes. These are gaps between workflow run creation times, not downtime durations. No availability percentage or downtime duration is supported. |
| Submit changes for review and update consolidated NFR status | **INCOMPLETE** | PRs #40–#44 are merged. This report and the DOWN/UNKNOWN classification correction are being submitted in a new PR for review; they are not yet merged. |

## Workflow and code inspection

- `.github/workflows/uptime-monitoring.yml` exists on `main`; the workflow is active and includes `schedule` plus `workflow_dispatch`.
- The schedule remains `7,22,37,52 * * * *` UTC. Permissions remain read-only (`contents: read`).
- `actions/checkout@v7` runs before repository scripts. `mkdir -p uptime-results` runs before shell redirection to `collector.log`. Artifact upload uses `if: always()` and archives `uptime-results/` when files exist.
- The collector records a UTC timestamp, HTTP status, elapsed response time, run identity and transport errors. A real HTTP response outside 2xx is **DOWN**; no complete HTTP response / curl transport failure is **UNKNOWN**. Failed checks retain measured timing or a labeled monotonic fallback, not a fabricated zero.
- Before this change, transport failures were incorrectly labelled DOWN. The collector and offline summarizer now classify these as UNKNOWN; regression tests cover connection/timeout failures and ensure UNKNOWN is not counted as verified HTTP downtime.

## Available run inventory

Live `gh run list --workflow 418077012 --limit 100` returned seven completed successful workflow records, all on `main`:

| Run | ID | Trigger | Created (UTC) | Health evidence |
| --- | ---: | --- | --- | --- |
| #1 | 43566650792 | `workflow_dispatch` | 2026-11-14 06:30:15 | No archived CSV; health UNKNOWN |
| #2 | 43601319394 | `schedule` | 2026-11-14 13:45:03 | 200, 32.700909 s, UP |
| #3 | 43629277239 | `schedule` | 2026-11-14 18:55:34 | 200, 41.639877 s, UP |
| #4 | 43650227798 | `schedule` | 2026-11-14 22:51:04 | 200, 31.755677 s, UP |
| #5 | 43667292046 | `schedule` | 2026-11-15 02:20:09 | 200, 32.817167 s, UP |
| #6 | 43693758441 | `workflow_dispatch` | 2026-11-15 08:16:54 | 200, 0.184001 s, UP |
| #7 | 43711931757 | `workflow_dispatch` | 2026-11-15 12:03:50 | 200, 31.834339 s, UP |

The repository archive preserves scheduled Run #8, ID `43736667439`, created 2026-11-15 16:39:08 UTC on `main`, trigger `schedule`, commit `f862d75a2b62a5c3719c860d47cab62ec469dfc8`. Its checkout succeeded, but the workflow shell failed before invoking the collector because `uptime-results/collector.log` did not exist. No request was made, no HTTP status or latency was measured, and no artifact was uploaded. This is a workflow failure and UNKNOWN application health, not evidence that Render was down. The current live run-list API no longer returns #8; its archived `run.json`, `jobs.json`, `logs.txt` and empty `artifacts.json` remain in `docs/uptime-evidence/43736667439/`.

PR #44 corrected the missing-directory error. It merged after Run #8 on 2026-11-15 16:55:27 UTC (merge commit `37d7c37c...`). At the 18:55:08 UTC inventory cutoff, there was no scheduled run after PR #44; the latest run returned by the live API was manual Run #7. Nominal slots after PR #44 at 17:07, 17:22, 17:37, 17:52, 18:07, 18:22, 18:37 and 18:52 UTC have no visible run or health sample in the available inventory and remain UNKNOWN. A missing run-list entry does not establish why GitHub did not create a run. The archived evidence contains **5 scheduled / 3 manual runs**, with **4 scheduled / 2 manual CSV samples**. Manual samples are not used as scheduled coverage. No currently available run record is pending or cancelled; the API inventory is not sufficient to prove whether GitHub skipped trigger delivery for every absent cron slot.

## Scheduling gaps and limits

Observed scheduled run-creation gaps in the preserved eight-run history: #2→#3 **310.52 minutes**, #3→#4 **235.50 minutes**, #4→#5 **209.08 minutes**, and #5→#8 **858.98 minutes**. Available job metadata shows starts 2–3 seconds after run creation, so runner queue delay does not explain these observed gaps. This does not establish why scheduled runs were absent.

The repository Actions permissions/policies endpoint returned HTTP 403 with: “You must have repository read permissions or have the repository Actions policies fine-grained permission.” Therefore repository/organization scheduling policy, restrictions or pause settings could not be verified. The workflow is shown as active and the default branch as `main`; no evidence identifies a root cause. Sparse health probes do not establish the service state between probes.

The offline evidence summary currently reports **8 archived runs**, **5 scheduled**, **3 manual**, **6 valid CSV samples**, **1 unsuccessful workflow run (#8)**, and missing CSV evidence for #1 and #8. It does not calculate availability. Historical raw files, CSVs, manifests, hashes and snapshots were preserved; no production request was made as part of this review.

## Scope conflict requiring issue-owner decision

The revised README/NFR summary says this academic prototype is evaluated locally and hosted-service availability/production operations are outside scope, while the Issue #9 report says local readiness is verified and tracks scheduled monitoring separately under #38. The revised verification notes also refer to scheduled readiness monitoring and retained external checks over the available project observation window. These statements leave the intended acceptance boundary for #38 unclear. No team approval resolving this conflict was found.

**Question for the issue owner:** “For the revised academic-prototype baseline, is Issue #38 satisfied by local readiness evidence, or is scheduled external Render readiness monitoring still required for the available project observation window? Please confirm the controlling SRS/Test Plan/SAD acceptance criteria, observation period, cadence, availability calculation, treatment of missing samples and maintenance, and who owns the monitoring configuration.”

The question is prepared here; it has not been posted and no approval is implied.

## Remaining work

1. Obtain the issue owner's/team's written decision on the scope conflict and the observation/acceptance rules above.
2. If hosted monitoring remains in scope, ask a repository administrator to inspect Actions scheduling policies and continue collecting genuine scheduled observations over the approved period. Keep missing slots UNKNOWN; do not count manual runs as scheduled.
3. Observe a natural scheduled execution after PR #44 and verify its CSV/log artifact. This review did not manually dispatch a run.
4. Reconcile the evidence against the confirmed acceptance method. Do not report availability or downtime without a supported calculation and sufficient observations.
5. Review this PR through the team's normal process. Keep Issue #38 and parent #9 open until accepted evidence is complete.

## Reproduce offline evidence checks

```bash
python scripts/summarize_uptime_evidence.py
python manage.py check
python manage.py test events.test_uptime_evidence
```

Offline tests validate the collector and archived evidence logic; they do not verify deployed uptime or GitHub's future scheduled-trigger delivery.
