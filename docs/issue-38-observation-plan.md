# Issue #38: proposed submission observation plan

Status: PROPOSAL FOR TEAM REVIEW, not a claim of faculty approval or completed observation. Owner: Raksha269.

The user confirmed submission on 16 November 2026 at 09:00 IST (03:30 UTC). The revised SRS PDF page 15 and Test Plan PDF page 25 call for documented scheduled readiness checks over the available project observation window; monthly 99.5% uptime is a longer-term operational objective. They do not prescribe a fixed 24/48-hour duration. Amendment approval caveats remain; the team should record which baseline it accepts.

## Concrete proposal

1. Retain the historical samples since monitoring began on 14 November, separating scheduled and manually dispatched runs. Preserve failed checks and missing artifacts as well as successful samples.
2. Review post-change history separately from PR #40's merge at 2026-11-15 09:38:07 UTC (15:08:07 IST). The latest possible submission cutoff is 2026-11-16 03:30 UTC (09:00 IST), only 17 hours 51 minutes 53 seconds after merge, not a full day. Start the final review at about 08:30 IST and record the actual snapshot cutoff before submission; do not pretend it includes later samples. Continue the existing scheduled workflow at minutes 7/22/37/52 UTC; do not fabricate observations or backfill gaps with manual bursts.
3. For each available run, preserve run/event identity, actual check timestamp, HTTP status, latency, result, artifact metadata and hashes. Archive CSVs before their 35-day expiry. Re-run the offline summary against each refreshed snapshot; do not silently overwrite the earlier review's cutoff.
4. Treat absent measurements as UNKNOWN. Treat runs without a CSV as missing raw status/latency evidence even when Actions reports success. Preserve actual DOWN samples and report them. Delayed execution is not an observation at the nominal scheduled instant.
5. Report coverage and gaps, not a continuous uptime percentage. No downtime duration is inferred solely from sparse samples. No planned-maintenance exclusion is assumed without a documented interval/reason approved by the team.
6. Before submission, the team reviews the report and records whether this available-window evidence meets the accepted academic criteria. If not accepted, leave #38 partial and state the missing evidence in the submission. Do not change the baseline solely to close the issue.

## Remaining confirmation

- Actual final evidence snapshot cutoff before the confirmed 09:00 IST submission.
- Team acceptance of the observation interval and best-effort GitHub scheduling, or a requirement for stricter independent cadence.
- Any approved maintenance intervals/exclusions (none supplied in this evidence).
- Reviewer decision on acceptance after the final snapshot.

If reliable 15-minute sampling is mandatory, GitHub cron alone is not a guarantee. An external monitor requires deployment-owner agreement and its own recorded setup/observations; no such monitor is claimed here. #38 and #9 remain open until their agreed criteria and evidence are reviewed.
