"""Concurrent HTTP probe for the EMS-NF-001 public search endpoint.

Set NFR_BENCHMARK_URL and NFR_BENCHMARK_CLIENTS before running. Use a staging
deployment with representative published-event data; this script is not a load
generator for payment or registration endpoints.
"""

import concurrent.futures
import json
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
    try:
        with urllib.request.urlopen(URL, timeout=REQUEST_TIMEOUT) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    except Exception as error:
        status = f"{type(error).__name__}: {str(error)[:120]}"
    return status, time.perf_counter() - started


with concurrent.futures.ThreadPoolExecutor(max_workers=CLIENTS) as pool:
    futures = [pool.submit(request_once, index) for index in range(CLIENTS)]
    time.sleep(1)
    barrier.wait(timeout=60)
    results = [future.result(timeout=REQUEST_TIMEOUT + 90) for future in futures]

durations = sorted(duration for _, duration in results)
p95 = durations[int(0.95 * (len(durations) - 1))]
report = {
    "measured_at_utc": datetime.now(timezone.utc).isoformat(),
    "url": URL,
    "concurrent_clients": CLIENTS,
    "successful_responses": sum(status == 200 for status, _ in results),
    "non_200_responses": sum(status != 200 for status, _ in results),
    "response_status_counts": dict(Counter(str(status) for status, _ in results)),
    "p50_seconds": durations[len(durations) // 2],
    "p95_seconds": p95,
    "max_seconds": max(durations),
    "srs_p95_target_seconds": 2.0,
    "srs_target_met_in_this_run": p95 <= 2.0 and all(status == 200 for status, _ in results),
}
print(json.dumps(report, indent=2))
