import csv
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import TestCase

from django.test import SimpleTestCase

from scripts.collect_uptime_check import collect, write_record
from scripts.summarize_uptime_evidence import summarize


class UptimeCollectorTests(TestCase):
    def clock(self):
        values = iter((10.0, 12.345678))
        return lambda: next(values)

    @staticmethod
    def completed(returncode=0, stdout='200,2.345678', stderr=''):
        return subprocess.CompletedProcess(['curl'], returncode, stdout, stderr)

    def test_http_success_records_elapsed_time_and_identity(self):
        record = collect(
            'https://example.test/health/', 120, '321', 'schedule',
            runner=lambda *args, **kwargs: self.completed(),
            clock=self.clock(),
            now=datetime(2026, 11, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(record['http_status'], '200')
        self.assertEqual(record['response_seconds'], '2.345678')
        self.assertEqual(record['result'], 'UP')
        self.assertEqual(record['event'], 'schedule')
        self.assertEqual(record['run_id'], '321')
        self.assertEqual(record['curl_exit_code'], '0')
        self.assertEqual(record['latency_source'], 'curl')

    def test_http_failure_is_down_but_not_a_transport_failure(self):
        record = collect(
            'https://example.test/', 5, '322', 'schedule',
            runner=lambda *args, **kwargs: self.completed(stdout='503,1.500000'),
            clock=self.clock(),
        )
        self.assertEqual(record['http_status'], '503')
        self.assertEqual(record['result'], 'DOWN')
        self.assertEqual(record['transport_error'], '')
        self.assertEqual(record['response_seconds'], '1.500000')

    def test_connection_failure_is_unknown_and_keeps_measured_time_and_error(self):
        record = collect(
            'https://example.test/', 5, '323', 'schedule',
            runner=lambda *args, **kwargs: self.completed(7, '000,0.003210', 'curl: connection refused'),
            clock=self.clock(),
        )
        self.assertEqual(record['http_status'], '000')
        self.assertEqual(record['result'], 'UNKNOWN')
        self.assertIn('connection refused', record['transport_error'])
        self.assertEqual(record['curl_exit_code'], '7')
        self.assertEqual(record['response_seconds'], '0.003210')

    def test_timeout_is_recorded_as_transport_failure(self):
        def fail(*args, **kwargs):
            raise subprocess.TimeoutExpired(['curl'], 11, output='000,')

        record = collect('https://example.test/', 1, '324', 'schedule', runner=fail, clock=self.clock())
        self.assertEqual(record['curl_exit_code'], '28')
        self.assertEqual(record['result'], 'UNKNOWN')
        self.assertIn('process timeout', record['error_detail'])
        self.assertEqual(record['response_seconds'], '2.345678')
        self.assertEqual(record['latency_source'], 'monotonic_fallback')

    def test_csv_quotes_error_text_and_keeps_header(self):
        record = collect(
            'https://example.test/', 5, '325', 'workflow_dispatch',
            runner=lambda *args, **kwargs: self.completed(7, '000,0.5', 'curl: failed, retry later'),
            clock=self.clock(),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'nested/check.csv'
            write_record(path, record)
            with path.open(newline='', encoding='utf-8') as source:
                row = next(csv.DictReader(source))
            self.assertEqual(row['error_detail'], 'curl: failed, retry later')
            self.assertEqual(row['event'], 'workflow_dispatch')


class UptimeEvidenceSummaryTests(SimpleTestCase):
    def make_evidence(self, root, rows, extra_runs=()):
        history = [
            {'databaseId': 101, 'event': 'schedule', 'createdAt': '2026-11-14T13:45:04Z', 'conclusion': 'success'},
            {'databaseId': 102, 'event': 'workflow_dispatch', 'createdAt': '2026-11-14T13:46:04Z', 'conclusion': 'success'},
            *extra_runs,
        ]
        manifest = []
        metadata = []
        for run_id, event, row in rows:
            row = dict(row, run_id=str(run_id), event=event,
                       curl_exit_code='0' if not row.get('transport_error') else '7',
                       latency_source='curl',
                       transport_error=row.get('transport_error', ''),
                       error_detail=row.get('error_detail', ''))
            directory = root / str(run_id)
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / 'check.csv'
            write_record(path, row)
            canonical_csv = path.read_bytes()
            archive_digest = f'{run_id:064x}'
            manifest.append({
                'run_id': run_id,
                'archive_sha256': archive_digest,
                'csv_sha256': hashlib.sha256(canonical_csv).hexdigest(),
                'row': row,
            })
            metadata.append({'run_id': run_id, 'digest': f'sha256:{archive_digest}'})
            (directory / 'jobs.json').write_text('[]', encoding='utf-8')
        (root / 'run-history.json').write_text(json.dumps(history), encoding='utf-8')
        (root / 'sample-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        (root / 'artifact-metadata.json').write_text(json.dumps(metadata), encoding='utf-8')
        (root / 'snapshot.json').write_text(json.dumps({
            'schedule_change_merged_at_utc': '2026-11-14T13:40:00Z',
            'captured_at_utc': '2026-11-14T13:50:00Z',
        }), encoding='utf-8')

    @staticmethod
    def sample(status='200', seconds='0.25', result='UP', timestamp='2026-11-14T13:45:07Z', **extra):
        return {
            'timestamp_utc': timestamp,
            'url': 'https://example.test/health/ready/',
            'http_status': status,
            'response_seconds': seconds,
            'result': result,
            **extra,
        }

    def test_manual_and_scheduled_samples_stay_separate_and_missing_is_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            extra = ({'databaseId': 103, 'event': 'schedule', 'createdAt': '2026-11-14T13:47:04Z'},)
            self.make_evidence(root, [
                (101, 'schedule', self.sample()),
                (102, 'workflow_dispatch', self.sample(timestamp='2026-11-14T13:46:07Z')),
            ], extra_runs=extra)
            summary = summarize(root)
            self.assertEqual(summary['scheduled_run_count'], 2)
            self.assertEqual(summary['manual_run_count'], 1)
            self.assertEqual(summary['scheduled_samples'], 1)
            self.assertEqual(summary['runs_without_archived_csv'], [103])
            self.assertEqual(summary['samples'][1]['event'], 'workflow_dispatch')
            self.assertTrue(all(slot['observation'] == 'UNKNOWN' for slot in summary['nominal_post_change_cron_slots']))

    def test_http_failure_is_counted_as_failed_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_evidence(root, [(101, 'schedule', self.sample('503', '1.5', 'DOWN'))])
            self.assertEqual(summarize(root)['failed_samples'], [101])
            self.assertEqual(summarize(root)['unknown_samples'], [])

    def test_transport_failure_is_unknown_not_counted_as_downtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_evidence(root, [(
                101, 'schedule', self.sample(
                    '000', '0.25', 'UNKNOWN',
                    transport_error='curl: connection refused',
                    error_detail='curl: connection refused',
                ),
            )])
            summary = summarize(root)
            self.assertEqual(summary['failed_samples'], [])
            self.assertEqual(summary['unknown_samples'], [101])

    def test_failed_workflow_without_csv_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            extra = ({
                'databaseId': 103, 'event': 'schedule',
                'createdAt': '2026-11-14T13:47:04Z', 'conclusion': 'failure',
            },)
            self.make_evidence(root, [(101, 'schedule', self.sample())], extra_runs=extra)
            summary = summarize(root)
            self.assertEqual(summary['unsuccessful_workflow_runs'], [103])
            self.assertEqual(summary['runs_without_archived_csv'], [102, 103])

    def test_windows_crlf_checkout_hashes_canonical_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_evidence(root, [(101, 'schedule', self.sample())])
            path = root / '101/check.csv'
            path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
            self.assertEqual(summarize(root)['samples'][0]['http_status'], '200')

    def test_invalid_csv_rows_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_evidence(root, [(101, 'schedule', self.sample())])
            path = root / '101/check.csv'
            path.write_text(path.read_text(encoding='utf-8') + 'bad,extra,row\n', encoding='utf-8')
            manifest_path = root / 'sample-manifest.json'
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            manifest[0]['csv_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'well-formed CSV row'):
                summarize(root)

    def test_bad_latency_and_hash_are_rejected(self):
        for seconds, message in (('NaN', 'Invalid latency'), ('-0.2', 'Invalid latency')):
            with self.subTest(seconds=seconds), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_evidence(root, [(101, 'schedule', self.sample(seconds=seconds))])
                with self.assertRaisesRegex(ValueError, message):
                    summarize(root)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_evidence(root, [(101, 'schedule', self.sample())])
            path = root / '101/check.csv'
            path.write_text(path.read_text(encoding='utf-8').replace(',200,', ',302,'), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'CSV hash mismatch'):
                summarize(root)

    def test_archive_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_evidence(root, [(101, 'schedule', self.sample())])
            metadata_path = root / 'artifact-metadata.json'
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            metadata[0]['digest'] = 'sha256:' + 'f' * 64
            metadata_path.write_text(json.dumps(metadata), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Archive digest mismatch'):
                summarize(root)

    def test_csv_event_must_match_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_evidence(root, [(101, 'workflow_dispatch', self.sample())])
            with self.assertRaisesRegex(ValueError, 'event does not match'):
                summarize(root)


class UptimeWorkflowConfigurationTests(SimpleTestCase):
    def test_checkout_and_output_directory_precede_collector_execution(self):
        workflow_path = Path(__file__).resolve().parents[1] / '.github/workflows/uptime-monitoring.yml'
        workflow = workflow_path.read_text(encoding='utf-8')
        self.assertLess(workflow.index('uses: actions/checkout@v7'), workflow.index('python scripts/collect_uptime_check.py'))
        self.assertLess(workflow.index('mkdir -p uptime-results'), workflow.index('> uptime-results/collector.log'))
