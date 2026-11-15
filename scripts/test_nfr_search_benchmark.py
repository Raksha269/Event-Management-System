"""Exercise actual probe subprocesses, including HTTP errors and transport failures."""
import http.server
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import unittest

SCRIPT = Path(__file__).with_name("nfr_search_benchmark.py")


class ProbeTests(unittest.TestCase):
    def probe(self, url):
        result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True,
                                env=dict(os.environ, NFR_BENCHMARK_URL=url,
                                         NFR_BENCHMARK_CLIENTS="2", NFR_BENCHMARK_REQUEST_TIMEOUT="2"),
                                timeout=15, check=True)
        return json.loads(result.stdout)

    def test_http_failures_are_reported_instead_of_crashing(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(503)
                self.end_headers()
            def log_message(self, *args):
                pass
        with http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                report = self.probe(f"http://127.0.0.1:{server.server_port}/")
            finally:
                server.shutdown()
                thread.join()
        self.assertEqual(report["response_status_counts"], {"503": 2})
        self.assertEqual(report["failed_requests"], 2)
        self.assertEqual(report["error_counts"], {"HTTPError: 503": 2})
        self.assertFalse(report["srs_target_met_in_this_run"])

    def test_connection_refusals_are_counted(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
            # Bound but not listening: connections are refused without a port-reuse race.
            report = self.probe(f"http://127.0.0.1:{port}/")
        self.assertEqual(report["connection_refusals"], 2)
        self.assertEqual(report["failed_requests"], 2)
