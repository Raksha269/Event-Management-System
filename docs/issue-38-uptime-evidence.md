# Issue #38: uptime cadence and evidence status

Owner: Raksha269. **Status: INCOMPLETE.** Issue #38 and parent #9 remain open.

Evidence inventory cutoff: **2026-11-15 16:32:55 UTC (22:02:55 IST)**. PR #43 merged into `main` at **15:55:43 UTC**. The latest available Actions inventory at the cutoff still contains seven runs, all created before PR #43 merged.

## Acceptance criteria

| Criterion | Status | Current evidence / remaining work |
| --- | --- | --- |
| Inspect scheduled Actions history, investigate multi-hour gaps, document findings/corrections | **INCOMPLETE** | Seven-run history and three historical scheduled gaps are documented; PR #40 staggered the cron. The repository Actions policy API returned 403, and no root cause is established. The 16:07 and 16:22 UTC nominal slots after PR #43 have no run record at this cutoff; delay/drop remains possible. |
| Get team agreement on observation period, cadence, availability calculation, missing samples, and maintenance | **WAITING FOR TEAM APPROVAL** | Issue #38 contains a request for these decisions; no team response or approval was present in the inspected comments. |
| Collect and preserve timestamped status/latency for the observation period, including failures and missed checks | **INCOMPLETE** | Six timestamped CSV rows are preserved across seven runs. Three runs were manual; two have CSV rows and one lacks an archived CSV. Four runs were scheduled, all before PR #40. No scheduled run or collector artifact after PR #43 is available yet. Nominal slots without a run record remain UNKNOWN. |
| Summarize coverage, downtime, gaps, limitations; calculate availability only when supported | **INCOMPLETE** | The summary validates the six archived CSV rows and reports gaps. It cannot establish downtime duration or availability from these sparse samples. No percentage is claimed. |
| Submit evidence/configuration changes for review and update NFR status accurately | **INCOMPLETE** | PRs #40–#43 are merged. The newly found output-directory defect and this refreshed report are submitted separately for review; they are not yet merged. No issue has been closed. |

## Current workflow configuration

- The default branch is `main`. GitHub reports `Render Uptime Monitoring` as active. The complete workflow at `.github/workflows/uptime-monitoring.yml` has `schedule` and `workflow_dispatch`, cron `7,22,37,52 * * * *` UTC, and `permissions: contents: read`.
- PR #43 added `actions/checkout@v7` before repository scripts, and the collector exists on `main` at `scripts/collect_uptime_check.py`.
- **A remaining workflow defect was found:** `python ... > uptime-results/collector.log` attempts to open the log before a directory exists. The repository does not contain `uptime-results/`, and Bash opens redirection targets before launching Python. Therefore, as currently merged, this command fails before the collector starts. The corrective change is to run `mkdir -p uptime-results` first. This report and regression check accompany that fix in the current review PR.
- The artifact step uses `if: always()` and archives `uptime-results/`; after the directory-order correction, the collector log and CSV can be archived on success or failure. `if-no-files-found: ignore` can otherwise hide the absence of files, so successful upload still needs verification in a real post-fix scheduled run.

## Actions history and execution evidence

The read-only GitHub API inventory at the cutoff returned **7 runs: 4 `schedule`, 3 `workflow_dispatch`**. All seven Actions conclusions are success. The last recorded run is manual #7 (`43711931757`), created at 12:03:50 UTC; its archived check row is timestamped 12:03:55 UTC. The latest scheduled run is #5 (`43667292046`), created at 02:20:09 UTC with a check at 02:20:13 UTC. Both predate PR #42 and PR #43. **No scheduled run occurred after PR #43 in the inspected history; the 16:07 and 16:22 UTC nominal slots have no run record as of the cutoff. There are no post-PR #43 logs or artifacts to validate.**

Four actual scheduled checks and two manual checks have archived CSV rows. All six report HTTP 200 / UP. The other manual run (#1, `43566650792`) has no CSV in the artifact archive; its successful Actions conclusion is not used as a replacement health result. Existing CSV hashes and GitHub artifact digests validate against the committed manifest/metadata. Run #5 logs show the old collector printing HTTP 200 and 32.817167 seconds and the artifact being successfully uploaded. These records predate the new collector and do not verify it.

Historical scheduled run-creation/sample gaps were **310.52, 235.50, and 209.08 minutes**. Recorded job start delays were 2–3 seconds after run creation; that does not explain why the run-creation events were hours apart. After PR #43 merged at 15:55:43 UTC, the 16:07 and 16:22 UTC nominal cron slots had no run record by the 16:32:55 UTC cutoff. Treat both slots as **UNKNOWN**; a trigger delay or omission cannot be distinguished yet.

The repository confirms `main` as its default branch and the workflow as active. The repository Actions policy endpoint returned **403** with “You must have repository read permissions or have the repository Actions policies fine-grained permission.” Consequently, repository/organization policy restrictions could not be inspected. The logs show runner token permissions `contents: read` on a historical run. No root cause for schedule gaps is asserted.

## Preserved sample table

| Check timestamp UTC | Trigger | HTTP | Response seconds | Run |
| --- | --- | ---: | ---: | --- |
| 2026-11-14 13:45:07 | Scheduled | 200 | 32.700909 | [43601319394](https://github.com/Raksha269/Event-Management-System/actions/runs/43601319394) |
| 2026-11-14 18:55:38 | Scheduled | 200 | 41.639877 | [43629277239](https://github.com/Raksha269/Event-Management-System/actions/runs/43629277239) |
| 2026-11-14 22:51:08 | Scheduled | 200 | 31.755677 | [43650227798](https://github.com/Raksha269/Event-Management-System/actions/runs/43650227798) |
| 2026-11-15 02:20:13 | Scheduled | 200 | 32.817167 | [43667292046](https://github.com/Raksha269/Event-Management-System/actions/runs/43667292046) |
| 2026-11-15 08:16:58 | Manual | 200 | 0.184001 | [43693758441](https://github.com/Raksha269/Event-Management-System/actions/runs/43693758441) |
| 2026-11-15 12:03:55 | Manual | 200 | 31.834339 | [43711931757](https://github.com/Raksha269/Event-Management-System/actions/runs/43711931757) |

Earlier snapshots remain preserved as separate files in `docs/uptime-evidence/`; this refresh does not overwrite the PR #41 snapshot. The archived run/job JSON, CSVs, manifest, artifact metadata/digests, hashes, and generated summary remain available. GitHub's ZIP digest is preserved from its API metadata; the original artifact ZIP bytes are not stored in this repository for independent rehashing.

## Limits and next actions

- Missing observations remain **UNKNOWN**, not UP or DOWN. No downtime duration, continuous uptime, or availability rate is supported. The monthly 99.5% objective is not demonstrated by this short, sparse sample.
- No manual monitoring run was triggered for this review. No production data, deployment settings, cron frequency, or issues were changed.
- Merge the output-directory correction only after review. Then wait for a natural scheduled execution and inspect its collector logs and artifact. Do not count any manual run as scheduled evidence.
- Continue collecting actual runs and failures, refresh the inventory cutoff and evidence summary without deleting older snapshots, and ask the team to approve the observation period and interpretation rules. A policy admin may need to inspect Actions settings that the API permission could not expose.
- Keep #38 and parent #9 open until all agreed acceptance criteria and evidence are reviewed.

## Reproduce the archived evidence summary

```bash
python scripts/summarize_uptime_evidence.py
python manage.py test events.test_uptime_evidence
```

The summarizer is offline; it does not contact the live endpoint. Local tests do not establish deployed monitoring behavior.
