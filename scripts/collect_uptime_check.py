"""Collect one HTTP readiness observation without losing transport failures."""
import argparse
import csv
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


FIELDS = (
    'timestamp_utc', 'url', 'http_status', 'response_seconds', 'result',
    'run_id', 'event', 'curl_exit_code', 'latency_source',
    'transport_error', 'error_detail',
)


def _parse_curl_output(output):
    if isinstance(output, bytes):
        output = output.decode('utf-8', errors='replace')
    parts = output.strip().split(',')
    if len(parts) != 2 or not parts[0].isdigit() or len(parts[0]) != 3:
        return None
    try:
        latency = float(parts[1])
    except ValueError:
        return None
    if not math.isfinite(latency) or latency < 0:
        return None
    return parts[0], latency


def collect(url, timeout, run_id, event, *, runner=subprocess.run, clock=time.perf_counter, now=None):
    """Run curl with a total timeout and retain its actual timing/error output."""
    start = clock()
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    command = [
        'curl', '--location', '--silent', '--show-error',
        '--max-time', str(timeout), '--output', os.devnull,
        '--write-out', '%{http_code},%{time_total}', url,
    ]
    status = '000'
    transport_error = ''
    error_detail = ''
    exit_code = 0
    latency_source = 'curl'
    curl_latency = None
    try:
        completed = runner(command, capture_output=True, text=True, check=False, timeout=timeout + 10)
        parsed = _parse_curl_output(completed.stdout or '')
        if parsed:
            status, curl_latency = parsed
        else:
            latency_source = 'monotonic_fallback'
            error_detail = 'curl did not return a parseable HTTP status and time_total'
        exit_code = completed.returncode
        stderr = completed.stderr or ''
        if exit_code:
            transport_error = stderr.strip() or f'curl exited with code {exit_code}'
            error_detail = transport_error
    except subprocess.TimeoutExpired as exc:
        latency_source = 'monotonic_fallback'
        parsed = _parse_curl_output(exc.stdout or '')
        if parsed:
            status = parsed[0]
        exit_code = 28
        transport_error = f'curl exceeded the {timeout + 10:g}-second process timeout'
        error_detail = transport_error
    except OSError as exc:
        latency_source = 'monotonic_fallback'
        exit_code = 127
        transport_error = f'{type(exc).__name__}: {exc}'
        error_detail = transport_error

    elapsed = max(0.0, clock() - start)
    response_seconds = curl_latency if curl_latency is not None else elapsed
    received_http_response = status.isdigit() and status != '000' and 100 <= int(status) <= 599
    if exit_code != 0 or not received_http_response:
        # The probe did not produce a complete, classifiable HTTP result.
        # This is missing health evidence, not proof the application is DOWN.
        result = 'UNKNOWN'
    else:
        result = 'UP' if 200 <= int(status) < 300 else 'DOWN'
    return {
        'timestamp_utc': timestamp,
        'url': url,
        'http_status': status,
        'response_seconds': f'{response_seconds:.6f}',
        'result': result,
        'run_id': str(run_id),
        'event': event,
        'curl_exit_code': str(exit_code),
        'latency_source': latency_source,
        'transport_error': transport_error,
        'error_detail': error_detail,
    }


def write_record(path, record):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerow(record)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--event', required=True)
    parser.add_argument('--output', type=Path, default=Path('uptime-results/check.csv'))
    args = parser.parse_args(argv)
    record = collect(args.url, args.timeout, args.run_id, args.event)
    write_record(args.output, record)
    print(f"Timestamp (UTC): {record['timestamp_utc']}")
    print(f"Readiness endpoint: {record['url']}")
    print(f"HTTP status: {record['http_status']}")
    print(f"Response time (seconds): {record['response_seconds']} ({record['latency_source']})")
    print(f"Result: {record['result']}")
    if record['error_detail']:
        print(f"Error: {record['error_detail']}")
    if record['result'] != 'UP':
        if record['result'] == 'UNKNOWN':
            print('Readiness result is UNKNOWN; the CSV evidence was retained.', file=sys.stderr)
        else:
            print('Readiness returned a non-2xx HTTP status; the CSV evidence was retained.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
