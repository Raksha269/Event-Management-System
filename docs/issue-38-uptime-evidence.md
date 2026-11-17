# Issue #38: uptime cadence and evidence status

**Status: CLOSED UNDER ACCEPTED LIMITED ACADEMIC SCOPE.** See the owner-recorded acceptance below. Scheduled availability itself remains unverified. The historical snapshot below records the Actions API inventory at **2026-11-15 18:55:08 UTC**. This report was refreshed from the schedule-filtered Actions API at **2026-11-16 19:17:32 UTC**, after PR #50 merged. No workflow was manually dispatched for this review.

## Final academic-scope acceptance

The repository owner recorded team acceptance in [Issue #9](https://github.com/Raksha269/Event-Management-System/issues/9#issuecomment-6932891735) and [Issue #38](https://github.com/Raksha269/Event-Management-System/issues/38#issuecomment-6932881938). Both issues are closed against the limited academic-project scope. This records the owner's stated team decision; no separate faculty approval is inferred.

[Issue #37](https://github.com/Raksha269/Event-Management-System/issues/37#issuecomment-6922868953) records the owner's completed responsive/keyboard checks for User Administration and Security Alerts at 320, 360, 768 and 1440 px, NVDA form-error/navigation checks, and confirmation that Manage Tickets responsive and remaining contrast checks were checked. These are user-performed results. Additional numerical contrast measurements or independent retests are not invented here. This acceptance is not a full WCAG certification.

Scheduled evidence is accepted with its gaps retained as UNKNOWN. Consistent 15-minute execution, monthly availability, availability percentages and downtime durations remain unverified. Maintenance exclusions require documented approval. Historical test results and limitations below remain unchanged.

## Historical acceptance assessment before final owner approval

The table below preserves the assessment at the evidence cutoff. Pending/open statements in this historical assessment are superseded by the final acceptance above; measurements and unresolved scheduling causes are unchanged.

## Acceptance criteria

| Criterion | Status | Evidence / remaining work |
| --- | --- | --- |
| Inspect scheduled Actions history, investigate multi-hour gaps, document findings and corrections | **INCOMPLETE** | The workflow is active on default branch `main`; cron is `7,22,37,52 * * * *` UTC. Post-mitigation scheduled runs remain hours apart. Job starts were 2–3 seconds after creation, so runner queue delay does not explain the gaps. Actions policy settings could not be read (API 403); the scheduling root cause is unknown. |
| Agree observation period, cadence, availability calculation, missing-sample and maintenance rules with the team | **WAITING FOR TEAM APPROVAL** | The existing Issue #38 comment requests these decisions, but no approval is recorded. A scope clarification is also required; see below. |
| Preserve timestamped status/latency evidence throughout the agreed period, including failures and missed checks | **INCOMPLETE** | Ten raw CSV samples and collector logs are archived: eight scheduled and two manual. All ten have HTTP 200 / UP results. Scheduled observations remain sparse; missing slots remain UNKNOWN. Run #8 failed before an HTTP probe and has no CSV. This does not yet cover a team-approved observation period. |
| Summarize coverage, downtime, gaps and limitations; calculate availability only with an agreed method and sufficient data | **INCOMPLETE** | Run-creation gaps include 310.52, 235.50, 209.08, 858.98, 283.57, 238.95, 409.77 and 629.90 minutes. They are workflow-run gaps, not downtime. No availability percentage or downtime duration is supported. |
| Submit changes for review and update consolidated NFR status | **IN PROGRESS** | PR #50 merged the prior evidence refresh and consolidated NFR update. This follow-up adds Run #12 and updates the inventory; team observation/acceptance criteria remain incomplete. |

## Latest inventory refresh (2026-11-16)

The schedule-filtered Actions API returned eight scheduled runs at the refresh cutoff: Runs #2–#5 and #9–#12. Archived failed Run #8 is not returned by the live list. The latest run, #12, was created **2026-11-16 18:41:19 UTC** and its probe finished at **18:41:25 UTC**. No later scheduled run was visible at the **19:17:32 UTC** inventory cutoff, 36.22 minutes later. This run-history gap is not evidence of application downtime or of why scheduled triggers were absent.

Runs #9–#12 have archived CSV samples and collector logs. Run #12 returned HTTP 200 / UP in 31.598001 s. These response times are readiness-check durations, not latency estimates from continuous service observation. Job creation/start/completion timestamps are preserved in each `jobs.json`. See the run table and files under `docs/uptime-evidence/<run-id>/`; artifact and canonical CSV SHA-256 values are in `artifact-metadata.json` and `sample-manifest.json`.

| Run | ID | Created (UTC) | Sample time (UTC) | Status | Response |
| --- | ---: | --- | --- | --- | ---: |
| #9 | 43763351798 | 2026-11-15 21:22:42 | 2026-11-15 21:22:47.186604 | 200 / UP | 31.715020 s |
| #10 | 43785811701 | 2026-11-16 01:21:39 | 2026-11-16 01:21:45.356731 | 200 / UP | 32.684809 s |
| #11 | 43829255391 | 2026-11-16 08:11:25 | 2026-11-16 08:11:31.575947 | 200 / UP | 31.760717 s |
| #12 | 43931446204 | 2026-11-16 18:41:19 | 2026-11-16 18:41:25.822196 | 200 / UP | 31.598001 s |

These are eight scheduled CSV samples over a timestamp span of about **52 hours 56 minutes** across the full archive, not continuous coverage or the team-approved monthly observation period.

The configured 15-minute schedule is best effort. The current evidence shows that successful post-fix runs exist, but substantial gaps remain. No Actions policy root cause was identified, no change to the schedule was made here, and nominal slots without a corresponding health sample remain UNKNOWN.

## Live Actions inventory refresh

The [Render Uptime Monitoring Actions page](https://github.com/Raksha269/Event-Management-System/actions/workflows/uptime-monitoring.yml) and schedule-filtered API were checked at **2026-11-16 19:17:32 UTC**. The API returned eight scheduled runs, latest Run #12 (ID `43931446204`), created **2026-11-16 18:41:19 UTC**. Archived Run #8 (ID `43736667439`, created **2026-11-15 16:39:08 UTC**) remains a failed pre-fix run without an HTTP sample.

The offline summary lists nominal post-PR #40 schedule timestamps through the inventory cutoff as UNKNOWN. It does not map late workflow starts to individual cron slots because the team has not approved a grace or matching rule; the count is not a count of proven dropped triggers. The timestamped API inventories are preserved in `docs/uptime-evidence/inventory-2026-11-16T161208Z.json` and `docs/uptime-evidence/inventory-2026-11-16T191732Z.json`.

In the **2026-11-15 18:55:08 UTC historical inventory**, Run #8 predated the output-directory correction merged in PR #44 at **2026-11-15 16:55:27 UTC**. At that historical cutoff, no scheduled run after PR #44 or PR #47 was visible. The current refresh above records later post-fix checks. The Actions API does not explain missing triggers. Absent runs and nominal schedule slots are not UP or DOWN observations; they remain **UNKNOWN** and do not establish continuous coverage or availability.

## Workflow and code inspection

- `.github/workflows/uptime-monitoring.yml` exists on `main`; the workflow is active and includes `schedule` plus `workflow_dispatch`.
- The schedule remains `7,22,37,52 * * * *` UTC. Permissions remain read-only (`contents: read`).
- `actions/checkout@v7` runs before repository scripts. `mkdir -p uptime-results` runs before shell redirection to `collector.log`. Artifact upload uses `if: always()` and archives `uptime-results/` when files exist.
- The collector records a UTC timestamp, HTTP status, elapsed response time, run identity and transport errors. A real HTTP response outside 2xx is **DOWN**; no complete HTTP response / curl transport failure is **UNKNOWN**. Failed checks retain measured timing or a labeled monotonic fallback, not a fabricated zero.
- Before this change, transport failures were incorrectly labelled DOWN. The collector and offline summarizer now classify these as UNKNOWN; regression tests cover connection/timeout failures and ensure UNKNOWN is not counted as verified HTTP downtime.

## Historical run inventory (cutoff 2026-11-15 18:55:08 UTC)

The detailed API inventory captured at **2026-11-15 18:55:08 UTC** returned seven completed successful workflow records, all on `main`:

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

At the **2026-11-16 16:12 UTC** historical cutoff, the archive contained **8 scheduled / 3 manual runs**, with **7 scheduled / 2 manual CSV samples**. Runs #9–#11 were the first three successful scheduled observations after the transport-classification fix in PR #47; PR #44 had already corrected the missing-directory error. Run #8 failed before a health request and manual Run #1 has no CSV. Manual samples are not used as scheduled coverage. No returned run was pending or cancelled. The Actions API list is not sufficient to prove whether GitHub skipped trigger delivery for every absent nominal slot.

## Scheduling gaps and limits

Observed scheduled run-creation gaps in the preserved history: #2→#3 **310.52 minutes**, #3→#4 **235.50 minutes**, #4→#5 **209.08 minutes**, #5→#8 **858.98 minutes**, #8→#9 **283.57 minutes**, #9→#10 **238.95 minutes**, #10→#11 **409.77 minutes**, and #11→#12 **629.90 minutes**. Available job metadata shows starts 2–3 seconds after run creation, so runner queue delay does not explain these observed gaps. No later run was visible 36.22 minutes after #12 at the inventory cutoff. These gaps do not establish why scheduled runs were absent.

The repository Actions permissions/policies endpoint returned HTTP 403 with: “You must have repository read permissions or have the repository Actions policies fine-grained permission.” Therefore repository/organization scheduling policy, restrictions or pause settings could not be verified. The workflow is shown as active and the default branch as `main`; no evidence identifies a root cause. Sparse health probes do not establish the service state between probes.

The offline evidence summary reports **12 archived runs**, **9 scheduled**, **3 manual**, **10 valid CSV samples** (8 scheduled, 2 manual), **1 unsuccessful workflow run (#8)**, and missing CSV evidence for #1 and #8. It does not calculate availability. Raw CSVs, collector logs, manifests, artifact/CSV hashes and snapshots are preserved; the checks are those naturally scheduled by Actions, with no production mutation or manual dispatch in this review.

## Historical scope question (superseded by final owner acceptance)

The revised README/NFR summary says this academic prototype is evaluated locally and hosted-service availability/production operations are outside scope, while the Issue #9 report says local readiness is verified and tracks scheduled monitoring separately under #38. The revised verification notes also refer to scheduled readiness monitoring and retained external checks over the available project observation window. These statements leave the intended acceptance boundary for #38 unclear. No team approval resolving this conflict was found.

**Question for the issue owner:** “For the revised academic-prototype baseline, is Issue #38 satisfied by local readiness evidence, or is scheduled external Render readiness monitoring still required for the available project observation window? Please confirm the controlling SRS/Test Plan/SAD acceptance criteria, observation period, cadence, availability calculation, treatment of missing samples and maintenance, and who owns the monitoring configuration.”

The question is prepared here; it has not been posted and no approval is implied.

## Historical proposed next steps (before final owner acceptance)

1. Obtain the issue owner's/team's written decision on the scope conflict and the observation/acceptance rules above.
2. If hosted monitoring remains in scope, ask a repository administrator to inspect Actions scheduling policies and continue collecting genuine scheduled observations over the approved period. Keep missing slots UNKNOWN; do not count manual runs as scheduled.
3. Continue observing natural scheduled executions and preserve their CSV/log artifacts, including failed results. Do not manually dispatch checks to fill gaps.
4. Reconcile the evidence against the confirmed acceptance method. Do not report availability or downtime without a supported calculation and sufficient observations.
5. Review this PR through the team's normal process. Keep Issue #38 and parent #9 open until accepted evidence is complete.

## Reproduce offline evidence checks

```bash
python scripts/summarize_uptime_evidence.py
python manage.py check
python manage.py test events.test_uptime_evidence
```

Offline tests validate the collector and archived evidence logic; they do not verify deployed uptime or GitHub's future scheduled-trigger delivery.
