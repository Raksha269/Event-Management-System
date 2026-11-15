# Issue #38: uptime evidence review

Owner: Raksha269. Status: PARTIAL / FOR REVIEW. #38 and parent #9 remain open.

Snapshot cutoff: **15 November 2026, 12:05:38 UTC (17:35:38 IST)**. Submission deadline supplied by the user: **16 November 2026, 09:00 IST (03:30 UTC)**. This is not the final submission snapshot.

## Criteria and observation plan

The revised SRS PDF page 15 and Test Plan PDF page 25 specify documented scheduled readiness monitoring over the available project observation window; monthly 99.5% uptime is a longer-term objective, not academic prototype acceptance. Revised SAD PDF page 18 describes readiness monitoring and retained timestamped evidence. Amendment pages retain team/faculty approval caveats. This report supplies evidence, not faculty approval or a new acceptance baseline.

The [concrete observation proposal](issue-38-observation-plan.md) keeps all available history, separates post-change observations, and proposes final review before the confirmed submission deadline. Team acceptance of duration, cadence and missing-sample treatment is still needed. No 24-hour completed period is claimed: merge-to-deadline is only 17h 51m 53s.

## Configuration and schedule investigation

- Default-branch workflow `.github/workflows/uptime-monitoring.yml` is active and checks the public Render `/health/ready/` endpoint.
- PR #40 merged at 2026-11-15 09:38:07 UTC (15:08:07 IST), changing cron from `*/15` to `7,22,37,52 * * * *` UTC. It is a mitigation, not a guarantee or proof of why earlier triggers are absent.
- Original scheduled run-creation gaps: **310.52, 235.50 and 209.08 minutes**, exceeding nominal 15-minute spacing. All recorded jobs started within 2–3 seconds of run creation; observed runner-queue delays do not explain those multi-hour gaps. Missing triggers before run creation cannot be diagnosed from these job records.
- The workflow is active on main, but no scheduled run after PR #40 appears in this snapshot. Nine nominal cron instants occurred between merge and cutoff (:52 on 09 UTC, then :07/:22/:37/:52 during 10 and 11 UTC). These are expected trigger slots, not health measurements or proven dropped events; delayed triggers remain possible.
- Repository Actions-policy inspection returned `Resource not accessible by integration` (403). Policy settings could not be independently checked. No disabling policy, service downtime or specific root cause is inferred.

## Preserved raw samples

Seven run records are archived: four scheduled and three manual, all with successful Actions conclusions. **Six actual CSV samples** were recovered and hash-validated; the earliest manual run (43566650792) has no artifact in the API listing, so it has no independently archived status/latency sample here. Actions success is not substituted for that missing CSV.

| Actual check time (UTC) | Event | HTTP | Seconds | Run |
| --- | --- | ---: | ---: | --- |
| 2026-11-14 13:45:07 | Scheduled | 200 | 32.700909 | [43601319394](https://github.com/Raksha269/Event-Management-System/actions/runs/43601319394) |
| 2026-11-14 18:55:38 | Scheduled | 200 | 41.639877 | [43629277239](https://github.com/Raksha269/Event-Management-System/actions/runs/43629277239) |
| 2026-11-14 22:51:08 | Scheduled | 200 | 31.755677 | [43650227798](https://github.com/Raksha269/Event-Management-System/actions/runs/43650227798) |
| 2026-11-15 02:20:13 | Scheduled | 200 | 32.817167 | [43667292046](https://github.com/Raksha269/Event-Management-System/actions/runs/43667292046) |
| 2026-11-15 08:16:58 | Manual | 200 | 0.184001 | [43693758441](https://github.com/Raksha269/Event-Management-System/actions/runs/43693758441) |
| 2026-11-15 12:03:55 | Manual | 200 | 31.834339 | [43711931757](https://github.com/Raksha269/Event-Management-System/actions/runs/43711931757) |

The final manual check was dispatched once for this review to verify the current default-branch workflow. Readiness executes read-only `SELECT 1`; no production data was mutated, no load or restore test was performed, and no repeated manual bursts were used. Its success establishes one current readiness sample, not functioning scheduled cadence or availability between samples. Slow successful responses are retained without inventing a latency acceptance threshold.

Raw CSVs, API run/job metadata, artifact metadata, CSV/archive hashes and machine-readable summary are in [uptime-evidence](uptime-evidence/summary.json). Archive SHA-256 values match the API artifact digests; CSV hashes and manifest rows are checked by the offline summarizer. Connector artifact download succeeded during this review after an earlier CLI download had been denied. This supersedes the earlier inability to inspect these particular CSVs, not their historical scope.

## Interpretation and limits

Missing observations remain **UNKNOWN**, not UP or DOWN. No availability percentage, downtime duration, reliable 15-minute cadence or monthly SLO compliance is established. Manual runs are separate from scheduled runs. No maintenance exclusions were supplied or applied. No failures appear in the six recovered CSVs; that does not prove no failures occurred between them.

The current collector substitutes `000,0` when curl returns nonzero. Thus a future transport-failure row's zero latency must not be treated as measured instantaneous failure. No such row occurs in this snapshot. Preserve the failed job/log evidence if one occurs; recording transport exit code and true elapsed time is a collector follow-up, not an implemented change in this documentation PR.

## Next actions before submission

1. **Raksha/team:** confirm the accepted available-window criteria and proposal, including nominal versus best-effort cadence. Record the decision; do not silently weaken a requirement to close an issue.
2. **Raksha/deployment owner:** inspect Actions UI/policies and continue post-merge observation. If no scheduled runs appear, report that gap; do not backfill it with manual checks. A stricter external monitor would require its own agreed setup and observations.
3. **Raksha:** around 08:30 IST on 16 November, retrieve newly available scheduled runs and CSVs, retain failure/unknown cases, and record the actual final cutoff before 09:00 submission. Existing workflow artifact retention is 35 days; archived copies here preserve recovered samples beyond that window.
4. **Reviewer/team:** review the final available evidence against the accepted academic criteria. If inadequate, submit a partial status with limitations and leave #38 open. Review #9's other criteria separately.

## Local reproduction of this snapshot summary

```bash
python3 scripts/summarize_uptime_evidence.py > /tmp/uptime-summary.json
```

The command only reads archived evidence and writes the requested output. It performs no network calls or live health checks. It verifies artifact/CSV hashes, one-row CSV consistency, status/result consistency and nonnegative latency before summarizing run counts/gaps, manual versus scheduled samples and nominal post-change slots.
