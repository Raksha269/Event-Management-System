"""Summarize archived uptime evidence locally; never issue network requests."""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path


def instant(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def summarize(root):
    history = json.loads((root / 'run-history.json').read_text())
    manifest = json.loads((root / 'sample-manifest.json').read_text())
    metadata = json.loads((root / 'artifact-metadata.json').read_text())
    snapshot = json.loads((root / 'snapshot.json').read_text())
    records = {r['databaseId']: r for r in history}
    samples = []
    for item in manifest:
        run_id = item['run_id']
        data = (root / str(run_id) / 'check.csv').read_bytes()
        if hashlib.sha256(data).hexdigest() != item['csv_sha256']:
            raise ValueError(f'CSV hash mismatch for {run_id}')
        artifact = next(a for a in metadata if a['run_id'] == run_id)
        if artifact.get('digest') != 'sha256:' + item['archive_sha256']:
            raise ValueError(f'Archive digest mismatch for {run_id}')
        rows = list(csv.DictReader(data.decode().splitlines()))
        if len(rows) != 1 or rows[0] != item['row']:
            raise ValueError(f'CSV/manifest mismatch for {run_id}')
        row = rows[0]
        instant(row['timestamp_utc'])
        if float(row['response_seconds']) < 0:
            raise ValueError('Negative latency')
        expected = 'UP' if row['http_status'].isdigit() and 200 <= int(row['http_status']) < 300 else 'DOWN'
        if row['result'] != expected:
            raise ValueError(f'Inconsistent status/result for {run_id}')
        samples.append(dict(row, run_id=run_id, event=records[run_id]['event']))
    scheduled = sorted((r for r in history if r['event'] == 'schedule'), key=lambda r: r['createdAt'])
    gaps = [{'from_run': a['databaseId'], 'to_run': b['databaseId'],
             'minutes': (instant(b['createdAt']) - instant(a['createdAt'])).total_seconds() / 60}
            for a, b in zip(scheduled, scheduled[1:])]
    merged = instant(snapshot['schedule_change_merged_at_utc'])
    cutoff = instant(snapshot['captured_at_utc'])
    slots = []
    minute = merged.replace(second=0, microsecond=0) + timedelta(minutes=1)
    while minute <= cutoff:
        if minute.minute in (7, 22, 37, 52):
            slots.append(minute.isoformat())
        minute += timedelta(minutes=1)
    delays = []
    for r in history:
        jobs = json.loads((root / str(r['databaseId']) / 'jobs.json').read_text())
        for job in jobs:
            if job.get('started_at'):
                delays.append({'run_id': r['databaseId'],
                               'seconds_after_run_creation': (instant(job['started_at']) - instant(r['createdAt'])).total_seconds()})
    return {'snapshot': snapshot, 'run_count': len(history), 'scheduled_run_count': len(scheduled),
            'manual_run_count': sum(r['event'] == 'workflow_dispatch' for r in history),
            'samples': sorted(samples, key=lambda s: s['timestamp_utc']),
            'runs_without_archived_csv': sorted(set(records) - {s['run_id'] for s in samples}),
            'scheduled_run_creation_gaps': gaps, 'job_start_delays': delays,
            'post_change_scheduled_runs': [r['databaseId'] for r in scheduled if instant(r['createdAt']) >= merged],
            'nominal_post_change_cron_slots': slots,
            'interpretation': 'Missing observations are unknown. Nominal cron slots are expected trigger times, not observed health checks or proven dropped events. Manual runs are separate. No uptime percentage or continuous-availability claim.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/uptime-evidence')
    args = parser.parse_args()
    print(json.dumps(summarize(args.evidence_dir), indent=2))
