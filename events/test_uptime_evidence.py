import csv
import hashlib
import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from scripts.summarize_uptime_evidence import summarize


class UptimeEvidenceSummaryTests(SimpleTestCase):
    def test_summary_accepts_windows_crlf_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_id = 123
            canonical_csv = (
                "timestamp_utc,url,http_status,response_seconds,result\n"
                "2026-11-14T13:45:07Z,https://example.test/health/ready/,200,0.25,UP\n"
            ).encode("utf-8")
            row = next(csv.DictReader(canonical_csv.decode("utf-8").splitlines()))
            archive_digest = "a" * 64

            run_directory = root / str(run_id)
            run_directory.mkdir()
            (run_directory / "check.csv").write_bytes(
                canonical_csv.replace(b"\n", b"\r\n")
            )
            (run_directory / "jobs.json").write_text("[]", encoding="utf-8")
            (root / "run-history.json").write_text(
                json.dumps([{
                    "databaseId": run_id,
                    "event": "schedule",
                    "createdAt": "2026-11-14T13:45:04Z",
                }]),
                encoding="utf-8",
            )
            (root / "sample-manifest.json").write_text(
                json.dumps([{
                    "run_id": run_id,
                    "archive_sha256": archive_digest,
                    "csv_sha256": hashlib.sha256(canonical_csv).hexdigest(),
                    "row": row,
                }]),
                encoding="utf-8",
            )
            (root / "artifact-metadata.json").write_text(
                json.dumps([{
                    "run_id": run_id,
                    "digest": f"sha256:{archive_digest}",
                }]),
                encoding="utf-8",
            )
            (root / "snapshot.json").write_text(
                json.dumps({
                    "schedule_change_merged_at_utc": "2026-11-14T13:40:00Z",
                    "captured_at_utc": "2026-11-14T13:50:00Z",
                }),
                encoding="utf-8",
            )

            summary = summarize(root)

            self.assertEqual(summary["samples"][0]["http_status"], "200")
            self.assertEqual(summary["runs_without_archived_csv"], [])
