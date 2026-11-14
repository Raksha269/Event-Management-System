"""Concurrent HTTP probe for the EMS-NF-001 public search endpoint.

Set NFR_BENCHMARK_URL and NFR_BENCHMARK_CLIENTS before running. Use a staging
deployment with representative published-event data; this script is not a load
generator for payment or registration endpoints.
"""

import concurrent.futures
import json
import math
import os
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone


URL = os.environ.get(
    "NFR_BENCHMARK_URL",
    "http://127.0.0.1:8000/api/v1/events/?q=Benchmark&limit=50&offset=0",
)
CLIENTS = int(os.environ.get("NFR_BENCHMARK_CLIENTS", "500"))
REQUEST_TIMEOUT = float(os.environ.get("NFR_BENCHMARK_REQUEST_TIMEOUT", "30"))
barrier = threading.Barrier(CLIENTS + 1)


def request_once(_):
    barrier.wait(timeout=60)
    started = time.perf_counter()
    status = None
    error = None
    try:
        with urllib.request.urlopen(URL, timeout=REQUEST_TIMEOUT) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        error = f"HTTPError: {error.code}"
    except Exception as exception:
        error = f"{type(exception).__name__}: {str(exception)[:120]}"
    return status, error, time.perf_counter() - started


with concurrent.futures.ThreadPoolExecutor(max_workers=CLIENTS) as pool:
    futures = [pool.submit(request_once, index) for index in range(CLIENTS)]
    time.sleep(1)
    wall_started = time.perf_counter()
    barrier.wait(timeout=60)
    results = [future.result(timeout=REQUEST_TIMEOUT + 90) for future in futures]
    elapsed = time.perf_counter() - wall_started

durations = sorted(duration for _, _, duration in results)


def percentile(values, quantile):
    return values[max(0, math.ceil(quantile * len(values)) - 1)]


statuses = [status for status, _, _ in results]
errors = [error for _, error, _ in results if error]
successful = sum(status == 200 for status in statuses)
connection_refusals = [
    error
    for error in errors
    if "ConnectionRefusedError" in error
    or "WinError 10061" in error
    or "Connection refused" in error
]
error_counts = Counter(errors)
report = {
    "measured_at_utc": datetime.now(timezone.utc).isoformat(),
    "url": URL,
    "concurrent_clients": CLIENTS,
    "total_requests": len(results),
    "successful_responses": successful,
    "failed_requests": len(results) - successful,
    "connection_refusals": len(connection_refusals),
    "other_transport_errors": sum(
        not error.startswith("HTTPError:")
        and "ConnectionRefusedError" not in error
        and "WinError 10061" not in error
        and "Connection refused" not in error
        for error in errors
    ),
    "response_status_counts": dict(Counter(str(status) for status in statuses)),
    "average_seconds": sum(durations) / len(durations),
    "p50_seconds": percentile(durations, 0.50),
    "p95_seconds": percentile(durations, 0.95),
    "p99_seconds": percentile(durations, 0.99),
    "max_seconds": max(durations),
    "wall_time_seconds": elapsed,
    "throughput_requests_per_second": len(results) / elapsed if elapsed else None,
    "srs_p95_target_seconds": 2.0,
    "srs_target_met_in_this_run": percentile(durations, 0.95) < 2.0 and successful == len(results),
    "error_counts": dict(error_counts),
}
print(json.dumps(report, indent=2))
