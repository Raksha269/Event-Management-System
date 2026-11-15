"""Summarize archived uptime evidence locally; never issue network requests."""
import argparse
import csv
import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


LEGACY_FIELDS = {
    'timestamp_utc', 'url', 'http_status', 'response_seconds', 'result',
}
CURRENT_FIELDS = LEGACY_FIELDS | {
    'run_id', 'event', 'transport_exit_code', 'transport_error', 'error_detail',
}
SCHEDULE_MINUTES = (7, 22, 37, 52)


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError(f'Timestamp must include a timezone: {value}')
    return parsed.astimezone(timezone.utc)


def read_single_csv(path, run_id):
    raw = path.read_bytes()
    # Git may check these text CSVs out with CRLF on Windows. Hash the
    # canonical LF representation used when the manifest was created.
    canonical = raw.replace(b'\r\n', b'\n')
    try:
        text = canonical.decode('utf-8')
        reader = csv.DictReader(text.splitlines())
        fields = set(reader.fieldnames or ())
        if fields not in (LEGACY_FIELDS, CURRENT_FIELDS):
            raise ValueError(f'Unexpected CSV columns for {run_id}: {reader.fieldnames}')
        if len(reader.fieldnames) != len(fields):
            raise ValueError(f'Duplicate CSV columns for {run_id}')
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValueError(f'Invalid CSV for {run_id}: {exc}') from exc
    if len(rows) != 1 or None in rows[0] or any(value is None for value in rows[0].values()):
        raise ValueError(f'Expected exactly one well-formed CSV row for {run_id}')
    return canonical, rows[0]


def validate_sample(row, run_id, record):
    try:
        instant(row['timestamp_utc'])
        latency = float(row['response_seconds'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f'Invalid timestamp or latency for {run_id}: {exc}') from exc
    if not math.isfinite(latency) or latency < 0:
        raise ValueError(f'Invalid latency for {run_id}: {row["response_seconds"]}')

    status = row.get('http_status', '')
    if status != '000' and (not status.isdigit() or not 100 <= int(status) <= 599):
        raise ValueError(f'Invalid HTTP status for {run_id}: {status}')
    if row.get('result') not in ('UP', 'DOWN'):
        raise ValueError(f'Invalid result for {run_id}: {row.get("result")}')
    error = row.get('transport_error', '')
    expected = 'UP' if status.isdigit() and status != '000' and 200 <= int(status) < 300 and not error else 'DOWN'
    if row['result'] != expected:
        raise ValueError(f'Inconsistent status/result for {run_id}')
    if 'run_id' in row and str(row['run_id']) != str(run_id):
        raise ValueError(f'CSV run id does not match archive directory for {run_id}')
    if 'event' in row and row['event'] != record['event']:
        raise ValueError(f'CSV event does not match run history for {run_id}')
    if 'transport_exit_code' in row:
        try:
            client_exit = int(row['transport_exit_code'])
        except ValueError as exc:
            raise ValueError(f'Invalid transport exit code for {run_id}') from exc
        if (client_exit == 0) != (not error):
            raise ValueError(f'Inconsistent exit code/transport error for {run_id}')
        if client_exit == 0 and status == '000':
            raise ValueError(f'No HTTP status despite successful request for {run_id}')


def summarize(root):
    history = json.loads((root / 'run-history.json').read_text(encoding='utf-8'))
    manifest = json.loads((root / 'sample-manifest.json').read_text(encoding='utf-8'))
    metadata = json.loads((root / 'artifact-metadata.json').read_text(encoding='utf-8'))
    snapshot = json.loads((root / 'snapshot.json').read_text(encoding='utf-8'))
    records = {r['databaseId']: r for r in history}
    if len(records) != len(history):
        raise ValueError('Duplicate run id in run history')
    manifest_ids = [item['run_id'] for item in manifest]
    if len(set(manifest_ids)) != len(manifest_ids):
        raise ValueError('Duplicate run id in sample manifest')
    artifacts = {a['run_id']: a for a in metadata}
    if len(artifacts) != len(metadata):
        raise ValueError('Duplicate run id in artifact metadata')

    samples = []
    for item in manifest:
        run_id = item['run_id']
        if run_id not in records:
            raise ValueError(f'Manifest run {run_id} is missing from run history')
        if run_id not in artifacts:
            raise ValueError(f'Artifact metadata is missing for run {run_id}')
        canonical_data, row = read_single_csv(root / str(run_id) / 'check.csv', run_id)
        csv_digest = item.get('csv_sha256', '')
        archive_digest = item.get('archive_sha256', '')
        if not re.fullmatch(r'[0-9a-f]{64}', csv_digest):
            raise ValueError(f'Invalid CSV SHA-256 format for {run_id}')
        if not re.fullmatch(r'[0-9a-f]{64}', archive_digest):
            raise ValueError(f'Invalid archive SHA-256 format for {run_id}')
        if hashlib.sha256(canonical_data).hexdigest() != csv_digest:
            raise ValueError(f'CSV hash mismatch for {run_id}')
        artifact = artifacts[run_id]
        if artifact.get('digest') != 'sha256:' + archive_digest:
            raise ValueError(f'Archive digest mismatch for {run_id}')
        if str(artifact.get('run_id')) != str(run_id):
            raise ValueError(f'Artifact run id mismatch for {run_id}')
        if row != item['row']:
            raise ValueError(f'CSV/manifest mismatch for {run_id}')
        validate_sample(row, run_id, records[run_id])
        samples.append(dict(row, run_id=run_id, event=records[run_id]['event']))

    scheduled = sorted((r for r in history if r['event'] == 'schedule'), key=lambda r: instant(r['createdAt']))
    creation_gaps = [
        {'from_run': a['databaseId'], 'to_run': b['databaseId'],
         'minutes': (instant(b['createdAt']) - instant(a['createdAt'])).total_seconds() / 60}
        for a, b in zip(scheduled, scheduled[1:])
    ]
    scheduled_samples = sorted((s for s in samples if s['event'] == 'schedule'), key=lambda s: instant(s['timestamp_utc']))
    sample_intervals = [
        {'from_run': a['run_id'], 'to_run': b['run_id'],
         'minutes': (instant(b['timestamp_utc']) - instant(a['timestamp_utc'])).total_seconds() / 60}
        for a, b in zip(scheduled_samples, scheduled_samples[1:])
    ]
    merged = instant(snapshot['schedule_change_merged_at_utc'])
    cutoff = instant(snapshot['captured_at_utc'])
    first_minute = merged.replace(second=0, microsecond=0) + timedelta(minutes=1)
    slots = []
    minute = first_minute
    while minute <= cutoff:
        if minute.minute in SCHEDULE_MINUTES:
            slots.append({'nominal_time_utc': minute.isoformat().replace('+00:00', 'Z'), 'observation': 'UNKNOWN'})
        minute += timedelta(minutes=1)

    delays = []
    for run in history:
        jobs_path = root / str(run['databaseId']) / 'jobs.json'
        jobs = json.loads(jobs_path.read_text(encoding='utf-8')) if jobs_path.exists() else []
        for job in jobs:
            if job.get('started_at'):
                delays.append({'run_id': run['databaseId'],
                               'seconds_after_run_creation': (instant(job['started_at']) - instant(run['createdAt'])).total_seconds()})

    missing_csv = sorted(set(records) - set(manifest_ids))
    if not set(manifest_ids).issubset(records):
        raise ValueError('Manifest references a run absent from run history')
    return {
        'snapshot': snapshot,
        'run_count': len(history),
        'scheduled_run_count': len(scheduled),
        'manual_run_count': sum(r['event'] == 'workflow_dispatch' for r in history),
        'unsuccessful_workflow_runs': [
            r['databaseId'] for r in history
            if r.get('conclusion') not in (None, 'success')
        ],
        'samples': sorted(samples, key=lambda s: instant(s['timestamp_utc'])),
        'scheduled_samples': len(scheduled_samples),
        'failed_samples': [s['run_id'] for s in samples if s['result'] == 'DOWN'],
        'runs_without_archived_csv': missing_csv,
        'scheduled_run_creation_gaps': creation_gaps,
        'scheduled_sample_intervals': sample_intervals,
        'job_start_delays': delays,
        'post_change_scheduled_runs': [r['databaseId'] for r in scheduled if instant(r['createdAt']) >= merged],
        'nominal_post_change_cron_slots': slots,
        'interpretation': 'Missing observations are UNKNOWN. Nominal cron slots are expected trigger times, not observed health checks or proven dropped events. Manual runs are separate. No uptime percentage, downtime duration, or continuous-availability claim is supported by this evidence.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/uptime-evidence')
    args = parser.parse_args()
    print(json.dumps(summarize(args.evidence_dir), indent=2))
