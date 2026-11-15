# Issue #38: uptime cadence and evidence review

Owner: Raksha269. **Status: PARTIAL — acceptance and observation evidence remain pending.** Issue #38 and parent #9 remain open.

## Acceptance criteria status

| Acceptance criterion | Status | Evidence / remaining work |
| --- | --- | --- |
| Inspect scheduled Actions history, investigate multi-hour gaps, and document findings/corrections | **PARTIAL** | Four pre-change scheduled runs and their gaps are documented below. PR #40 staggered the schedule; no cause is established. No scheduled run occurred after the change in the latest inventory. |
| Team confirms observation period, cadence, availability method, and missing-sample/maintenance treatment | **PENDING** | A request for team confirmation is recorded in Issue #38; no response/approval is present in the inspected issue. |
| Preserve timestamped status/latency through the observation period, including failed and missed checks | **PARTIAL** | Six real CSV samples are archived for seven workflow runs. One earlier manual run has no CSV. Post-change cron slots are UNKNOWN because there is no run record. New collector changes in this branch retain transport errors and measured elapsed time, but have not yet run in GitHub Actions. |
| Summarize coverage, downtime, gaps, limitations; report availability only if justified | **PARTIAL** | This report and the generated summary identify recorded samples and gaps. Evidence is too sparse to establish downtime duration or calculate availability. |
| Submit evidence/configuration changes in a PR and update NFR status accurately | **PENDING REVIEW** | PR #40 and #41 are merged. Collector, validation, tests, and this report update are prepared on a separate branch for review; they are not yet deployed. Team acceptance is still needed. |

## Configuration and Actions history

- GitHub reports the monitoring workflow as active on the repository's default branch, `main`. Its configured cron is `7,22,37,52 * * * *` UTC. PR #40 merged at **2026-11-15 09:38:07 UTC** and changed the schedule from `*/15` to these staggered minutes. This reduces alignment with the top of the hour; it does not guarantee execution or explain earlier gaps.
- Latest GitHub Actions API inventory captured at **2026-11-15 15:14:50 UTC** contains **7 runs: 4 scheduled and 3 manually dispatched**. All recorded Actions conclusions are success. The latest inventory has no scheduled run created after PR #40. The three later nominal slots before that cutoff (09:52, 10:07, 10:22, … through 15:07 UTC; see the complete slot list in `uptime-evidence/summary.json`) are **UNKNOWN observations**, not proof of application downtime or proof that GitHub dropped each trigger.
- Pre-change scheduled run-creation and measured-sample intervals were **310.52, 235.50, and 209.08 minutes**. Recorded jobs began 2–3 seconds after run creation, so observed runner queue delay does not account for the multi-hour interval between the recorded runs. The trigger creation gap remains unexplained.
- The repository endpoint confirmed `default_branch: main`; GitHub's workflow listing reports this workflow active. The Actions policy endpoint returned **403, “read permissions or fine-grained permission required.”** Repository-level Actions policy/settings and any dispatch suppression therefore could not be inspected. No root cause is asserted.
- Manual runs are kept separate from schedule-triggered runs. The manual readiness checks do not count as scheduled cadence evidence.

## Archived observations

Seven workflow runs are represented in the archived run history. Six real CSV rows are retained and hash-checked. All six report HTTP 200 / UP. There are no recovered failed checks. The first manual run (43566650792) has no archived CSV; its successful Actions conclusion is not used as a substitute for HTTP status or latency evidence.

| Check timestamp (UTC) | Trigger | HTTP | Response seconds | Run |
| --- | --- | ---: | ---: | --- |
| 2026-11-14 13:45:07 | Scheduled | 200 | 32.700909 | [43601319394](https://github.com/Raksha269/Event-Management-System/actions/runs/43601319394) |
| 2026-11-14 18:55:38 | Scheduled | 200 | 41.639877 | [43629277239](https://github.com/Raksha269/Event-Management-System/actions/runs/43629277239) |
| 2026-11-14 22:51:08 | Scheduled | 200 | 31.755677 | [43650227798](https://github.com/Raksha269/Event-Management-System/actions/runs/43650227798) |
| 2026-11-15 02:20:13 | Scheduled | 200 | 32.817167 | [43667292046](https://github.com/Raksha269/Event-Management-System/actions/runs/43667292046) |
| 2026-11-15 08:16:58 | Manual | 200 | 0.184001 | [43693758441](https://github.com/Raksha269/Event-Management-System/actions/runs/43693758441) |
| 2026-11-15 12:03:55 | Manual | 200 | 31.834339 | [43711931757](https://github.com/Raksha269/Event-Management-System/actions/runs/43711931757) |

The report preserves the original PR #41 snapshot at `uptime-evidence/snapshot-pr41-2026-11-15T120538Z.json`; `snapshot.json` and `summary.json` reflect the newer API inventory cutoff. CSV files, artifact metadata/digests, job metadata, manifest rows, and SHA-256 values remain archived. The API artifact digest is retained as reported by GitHub; the original artifact ZIP is not stored here, so its ZIP bytes cannot be independently rehashed from this repository.

## Technical changes in this review branch

- Replaced the shell `curl || RESULT="000,0"` fallback. That fallback concealed transport errors and represented latency as zero when no valid measurement was available.
- Added a standard-library collector that records request-start UTC timestamp, actual client elapsed seconds, HTTP status (or `000` when no HTTP response exists), run ID, trigger event, transport exit classification, transport error, and error detail. HTTP failures and connection/timeouts are classified DOWN; transport failures retain elapsed time instead of substituting zero.
- The collector writes a correctly quoted CSV before returning failure, and the workflow's unconditional artifact-upload step retains the CSV and collector log on failed checks. The schedule and production endpoint are unchanged.
- Strengthened the offline summarizer for schema, CSV row count, status/result and identity consistency, finite nonnegative latency, and CSV/archive digest consistency. It now computes scheduled sample intervals separately from run-creation gaps and marks every nominal post-change slot UNKNOWN.
- Added automated cases for HTTP errors, connection failure, timeout, elapsed latency, manual/scheduled separation, missing samples, malformed CSV, hash mismatch, event mismatch, invalid latency, and CRLF checkouts.

These changes are **not yet in main**. Their tests show local behavior only; no GitHub Actions execution of the new collector or deployed monitoring verification is claimed.

## Limits and remaining approval

- Missing observations are **UNKNOWN**, not UP or DOWN. No uptime percentage, downtime duration, monthly 99.5% compliance, or continuous availability is established by sparse checks.
- No maintenance periods were supplied or excluded. GitHub cron is best effort; nominal schedule instants are not proof that a check ran at that time.
- The observation window, acceptable cadence, availability calculation, maintenance treatment, and missing-sample policy still require team acceptance. A comment requesting that decision is present in Issue #38, without a recorded response at this review.
- This work made no manual workflow dispatch, load test, production-data change, or restore attempt. It did not alter the monitoring cadence.
- A later run inventory and evidence capture are needed; any workflow failures and missing artifacts must be retained. If the team requires guaranteed 15-minute monitoring, it must approve an external monitor and its observation plan.

## Reproduce the archived evidence summary

```bash
python scripts/summarize_uptime_evidence.py
python manage.py test events.test_uptime_evidence
```

The summarizer is offline and does not contact the live endpoint. Local automated test results do not establish production uptime.
