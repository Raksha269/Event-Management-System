"""Collect one HTTP readiness observation without losing transport failures."""
import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


FIELDS = (
    'timestamp_utc', 'url', 'http_status', 'response_seconds', 'result',
    'run_id', 'event', 'transport_exit_code', 'transport_error', 'error_detail',
)


def collect(url, timeout, run_id, event, *, opener=urlopen, clock=time.perf_counter, now=None):
    """Return one record; response_seconds is measured client elapsed time."""
    start = clock()
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    status = '000'
    transport_error = ''
    error_detail = ''
    exit_code = 0
    try:
        request = Request(url, headers={'User-Agent': 'EMS-Uptime-Monitor/1.0'})
        with opener(request, timeout=timeout) as response:
            status = str(response.status)
    except HTTPError as exc:
        # HTTP errors are valid server responses, not transport failures.
        status = str(exc.code)
        error_detail = f'HTTPError: {exc.reason}'
        exit_code = 0
    except (URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, 'reason', exc)
        transport_error = f'{type(reason).__name__}: {reason}'
        error_detail = transport_error
        exit_code = 28 if isinstance(reason, (TimeoutError,)) else 7
    except Exception as exc:  # preserve unexpected collector failures too
        transport_error = f'{type(exc).__name__}: {exc}'
        error_detail = transport_error
        exit_code = 1
    elapsed = max(0.0, clock() - start)
    result = 'UP' if status.isdigit() and 200 <= int(status) < 300 and not transport_error else 'DOWN'
    return {
        'timestamp_utc': timestamp,
        'url': url,
        'http_status': status,
        'response_seconds': f'{elapsed:.6f}',
        'result': result,
        'run_id': str(run_id),
        'event': event,
        'transport_exit_code': str(exit_code),
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
    print(f"Response time (seconds): {record['response_seconds']}")
    print(f"Result: {record['result']}")
    if record['error_detail']:
        print(f"Error: {record['error_detail']}")
    if record['result'] == 'DOWN':
        print('Readiness check failed; the CSV evidence was retained.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
