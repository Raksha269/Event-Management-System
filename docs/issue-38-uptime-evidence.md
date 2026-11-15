# Issue #38: uptime cadence and evidence status

Owner: Raksha269. **Status: INCOMPLETE.** Issue #38 and parent #9 remain open.

Evidence inventory cutoff: **2026-11-15 16:47:59 UTC (22:17:59 IST)**. PR #43 merged to `main` at **15:55:43 UTC**. The inventory now includes scheduled Run #8, created after PR #43.

## Acceptance criteria

| Criterion | Status | Evidence / remaining work |
| --- | --- | --- |
| Inspect scheduled Actions history, investigate multi-hour gaps, document findings/corrections | **INCOMPLETE** | Eight-run history is archived. PR #40 staggered the cron; Run #8 proves a workflow execution occurred after PR #43, but the repository Actions policy API returned 403 and no cause for historical gaps is established. |
| Get team agreement on observation period, cadence, availability calculation, missing samples, and maintenance | **WAITING FOR TEAM APPROVAL** | The observation plan is still pending team confirmation. |
| Collect and preserve timestamped status/latency for the observation period, including failures and missed checks | **INCOMPLETE** | Six CSV health samples remain archived (four scheduled, two manual; all HTTP 200 / UP). Run #8 was scheduled but failed before making an HTTP request; it has no CSV or artifact. Its health observation is UNKNOWN. |
| Summarize coverage, downtime, gaps, limitations; calculate availability only when supported | **INCOMPLETE** | Evidence summary records run #8 as an unsuccessful workflow and without CSV. No downtime duration or availability rate can be calculated from these sparse observations. |
| Submit evidence/configuration changes for review and update NFR status accurately | **INCOMPLETE** | PR #44 contains the directory fix, regression test, and updated evidence. It is under review and is not merged. No issue has been closed. |

## Run #8: verified failure

- Run: [43736667439](https://github.com/Raksha269/Event-Management-System/actions/runs/43736667439), event `schedule`, run #8, branch `main`, commit `f862d75a2b62a5c3719c860d47cab62ec469dfc8`.
- Created/started: **2026-11-15 16:39:08 UTC**; runner job started at **16:39:10 UTC**. The 16:37 cron slot therefore produced a run about 2 minutes 8 seconds later.
- Checkout succeeded. The availability step failed immediately because Bash could not open the redirection target: `uptime-results/collector.log: No such file or directory`. The follow-up `cat` failed for the same reason.
- The Python collector never ran. No HTTP status, latency, or UP/DOWN result was measured. The artifact step reported no files at `uptime-results/`, and no artifact was uploaded.
- This is a **workflow/configuration failure**, not evidence that the Render service was down. Preserve this run as UNKNOWN for application health.

Raw run metadata and job/step results are archived under `docs/uptime-evidence/43736667439/`. No CSV is included because none was produced. The prior evidence snapshot remains preserved separately.

## Corrective change in PR #44

The workflow now runs `mkdir -p uptime-results` before the shell redirects collector output to `uptime-results/collector.log`. This ensures the collector can start when the directory is absent. Existing collector error handling, real elapsed timing, scheduled/manual distinction, `schedule` and `workflow_dispatch` triggers, cron, read-only permissions, and artifact upload configuration are preserved. A regression test verifies repository checkout and directory creation precede collector redirection. A natural post-fix scheduled run is still needed to verify the log and CSV artifact in Actions.

## Inventory and evidence limits

The Actions inventory contains **8 runs: 5 scheduled and 3 manual**. The six archived CSV rows are four scheduled and two manual, all reporting HTTP 200 / UP. Manual observations are not counted as scheduled. Two runs have no archived CSV: the earlier manual run #1 and scheduled run #8. Their successful/failed workflow conclusions do not substitute for application health results.

Scheduled run creation gaps in the available history were 310.52, 235.50, and 209.08 minutes before Run #8. The gap from the previous scheduled run (#5) to #8 was 858.98 minutes; this is a run-creation gap, and #8 itself contains no health sample. Run #8's creation-to-job-start delay was approximately 2 seconds. The other nominal cron slots after PR #43 remain without verified health evidence; missing observations are UNKNOWN. The workflow run alone does not establish continuous service availability.

The repository Actions policy endpoint returned **403**: “You must have repository read permissions or have the repository Actions policies fine-grained permission.” Repository/organization policy settings could not be inspected, so no scheduling root cause is claimed. Older samples and their CSV/hash/artifact metadata remain unchanged. No original artifact ZIP is stored locally for independent rehashing.

No manual workflow dispatch or production change was made. No uptime percentage, downtime duration, or continuous-availability claim is supported. Team agreement on the observation period and calculation rules remains outstanding.

## Next actions

1. Review and merge PR #44 only through the normal team review process.
2. Wait for a natural scheduled run after the fix; verify it invokes the collector and uploads its CSV/log artifact. Do not dispatch manually for this evidence.
3. Continue collecting observations for the team-approved window and record missing slots as UNKNOWN.
4. Obtain team confirmation of the observation period, availability method, maintenance handling, and gap interpretation. A repository admin may need to inspect Actions policy settings.
5. Keep #38 and parent #9 open until their agreed acceptance criteria are genuinely met.

## Reproduce the archived evidence summary

```bash
python scripts/summarize_uptime_evidence.py
python manage.py test events.test_uptime_evidence
```

The summarizer is offline. Local tests do not establish deployed monitoring behavior.\n