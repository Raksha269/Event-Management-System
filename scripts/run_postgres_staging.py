"""Provision, measure and recover disposable local PostgreSQL staging. Run in .venv."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clients", type=int, nargs="+", default=[10, 50, 100])
    parser.add_argument("--skip-tests", action="store_true", help="Explicitly record tests as skipped")
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix:
        parser.error("Run using .venv/bin/python; system Python is not supported.")
    if any(n < 1 or n > 100 for n in args.clients):
        parser.error("Client counts must be between 1 and 100 for this local harness.")
    for executable in ["initdb", "pg_ctl", "pg_dump", "pg_restore"]:
        if not shutil.which(executable):
            parser.error(f"Install PostgreSQL server/client utilities: missing {executable}")
    extras = ROOT / ".staging" / "pg-extra"
    amcheck = shutil.which("pg_amcheck") or str(extras / "usr/bin/pg_amcheck")
    if not Path(amcheck).is_file():
        parser.error("Install matching PostgreSQL contrib utilities or unpack them in .staging/pg-extra")
    os.umask(0o077)
    private = ROOT / ".staging"
    private.mkdir(exist_ok=True)
    lock = (private / "runner.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    work = private / run_id
    work.mkdir()
    evidence = ROOT / "docs" / "staging" / "evidence" / run_id
    evidence.mkdir(parents=True)
    print(f"Evidence: {evidence.relative_to(ROOT)}", flush=True)
    env = os.environ.copy()
    password = secrets.token_urlsafe(32)
    db_port, http_port = free_port(), free_port()
    env.update({
        "DJANGO_SETTINGS_MODULE": "config.staging_settings", "DJANGO_DEBUG": "false",
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(48), "EMS_DB_ENGINE": "postgresql",
        "EMS_DB_NAME": "ems_staging", "EMS_DB_USER": "ems_runner", "EMS_DB_PASSWORD": password,
        "EMS_DB_HOST": "127.0.0.1", "EMS_DB_PORT": str(db_port), "EMS_DB_SSLMODE": "disable",
        "EMS_DB_CONN_MAX_AGE": "60", "EMS_ISOLATED_STAGING": "synthetic-only",
        "EMS_AUDIT_RETENTION_DAYS": "1095", "PGPASSWORD": password,
        "PGHOST": "127.0.0.1", "PGPORT": str(db_port), "PGUSER": "ems_runner",
    })
    report = {"started_at_utc": timestamp(), "operator": os.environ.get("USER", "unknown"),
              "scope": "local synthetic PostgreSQL; not deployed production verification",
              "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "working_tree_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).splitlines(),
              "platform": platform.platform(), "python": platform.python_version(),
              "logical_cpu_count": os.cpu_count(), "memory_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
              "resource_limits": "No imposed CPU/RAM limits; app, DB and load generator share host",
              "gunicorn_workers": 2, "gunicorn_threads_per_worker": 4,
              "database_port": db_port, "http_port": http_port,
              "audit_retention_days": 1095, "audit_purge_schedule": "not configured",
              "production_baseline": "pending team agreement", "status": "running"}
    def save():
        (evidence / "environment.json").write_text(json.dumps(report, indent=2) + "\n")
    def run(command, output, run_env=None):
        with (evidence / output).open("w") as log:
            result = subprocess.run(command, cwd=ROOT, env=run_env or env, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f"Command failed ({result.returncode}); inspect {evidence / output}")
    def manage(*arguments, output, run_env=None):
        run([sys.executable, "manage.py", *arguments], output, run_env)
    server = None
    postgres_started = False
    server_log = None
    source_files = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    manifest = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in sorted(set(source_files))
                if (name.endswith(".py") or name == "requirements.txt") and (ROOT / name).is_file()}
    (evidence / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for name in ("cpu.max", "memory.max"):
        path = Path("/sys/fs/cgroup") / name
        if path.exists():
            report[f"cgroup_{name}"] = path.read_text().strip()
    save()
    try:
        pwfile = work / "postgres-password"
        pwfile.write_text(password)
        run(["initdb", "-D", str(work / "pgdata"), "-U", "ems_runner", "--pwfile", str(pwfile),
             "--auth", "scram-sha-256", "--encoding=UTF8", "--no-locale"], "initdb.log")
        pwfile.unlink()
        postgres_options = ["-h", "127.0.0.1", "-p", str(db_port), "-k", "", "-c", "max_connections=120"]
        extension_dir = extras / "usr/share/pgsql/extension"
        if extension_dir.is_dir():
            # PostgreSQL 18 supports isolated extension controls. Do not touch system files.
            for name in ("pg_trgm", "amcheck"):
                control = extension_dir / f"{name}.control"
                content = control.read_text().replace("$libdir/", str(extras / "usr/lib64/pgsql") + "/")
                control.write_text(content)
            postgres_options += ["-c", f"extension_control_path={extension_dir.parent}:$system"]
        options = shlex.join(postgres_options)
        run(["pg_ctl", "-D", str(work / "pgdata"), "-l", str(work / "postgres.log"),
             "-o", options, "-w", "start"], "postgres-start.log")
        postgres_started = True
        import psycopg
        from psycopg import sql
        def connect(database, **kwargs):
            return psycopg.connect(host="127.0.0.1", port=db_port, user="ems_runner",
                                   password=password, dbname=database, **kwargs)
        with connect("postgres", autocommit=True) as admin:
            admin.execute("CREATE DATABASE ems_staging")
            admin.execute("CREATE DATABASE ems_restore_test")
            report["postgres_version"] = admin.execute("SELECT version()").fetchone()[0]
            report["postgres_max_connections"] = admin.execute("SHOW max_connections").fetchone()[0]
        manage("check", output="django-check.log")
        manage("makemigrations", "--check", "--dry-run", output="migration-drift.log")
        manage("migrate", "--noinput", output="migrate.log")
        manage("seed_postgres_staging", output="dataset.json")
        with connect("ems_staging", autocommit=True) as source:
            source.execute("ANALYZE")
        manage("collectstatic", "--noinput", output="static.log")
        server_log = (work / "gunicorn.log").open("w")
        url = f"http://127.0.0.1:{http_port}"
        def start_server(server_env):
            return subprocess.Popen([sys.executable, "-m", "gunicorn", "config.wsgi:application",
                                     "--bind", f"127.0.0.1:{http_port}", "--workers", "2", "--threads", "4"],
                                    cwd=ROOT, env=server_env, stdout=server_log, stderr=subprocess.STDOUT)
        def ready(process):
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Gunicorn exited; inspect private gunicorn.log")
                try:
                    with urlopen(url + "/health/ready/", timeout=2) as response:
                        if response.status == 200:
                            return json.load(response)
                except OSError:
                    time.sleep(0.1)
            raise RuntimeError("Application readiness timed out")
        server = start_server(env)
        report["source_readiness"] = ready(server)
        endpoint = url + "/api/v1/events/?q=Sample&limit=50&offset=0"
        with urlopen(endpoint, timeout=10) as response:
            payload = json.load(response)
        if not payload or (isinstance(payload, dict) and not payload.get("results")):
            raise RuntimeError("Benchmark query returned no matching events")
        report["search_smoke_test"] = "HTTP 200 with nonempty results"
        for clients in args.clients:
            print(f"Running {clients}-client search burst", flush=True)
            bench_env = dict(env, NFR_BENCHMARK_URL=endpoint, NFR_BENCHMARK_CLIENTS=str(clients))
            run([sys.executable, "scripts/nfr_search_benchmark.py"], f"search-{clients}.json", bench_env)
        server.terminate()
        server.wait(timeout=30)
        server = None
        def snapshot(database):
            with connect(database) as conn:
                tables = [row[0] for row in conn.execute(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")]
                counts, digests = {}, {}
                for table in tables:
                    counts[table] = conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]
                    rows = conn.execute(sql.SQL("SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text").format(sql.Identifier(table))).fetchall()
                    digests[table] = hashlib.sha256("\n".join(row[0] for row in rows).encode()).hexdigest()
                invalid_indexes = conn.execute("SELECT count(*) FROM pg_index WHERE NOT indisvalid").fetchone()[0]
                invalid_constraints = conn.execute("SELECT count(*) FROM pg_constraint WHERE NOT convalidated").fetchone()[0]
                return {"row_counts": counts, "table_content_sha256": digests,
                        "invalid_indexes": invalid_indexes, "unvalidated_constraints": invalid_constraints}
        before = snapshot("ems_staging")
        dump = work / "staging.dump"
        report["backup_started_at_utc"] = timestamp()
        run(["pg_dump", "--dbname=ems_staging", "--format=custom", "--no-owner", "--no-acl", f"--file={dump}"], "backup.log")
        report["backup_completed_at_utc"] = timestamp()
        report["backup_identifier"] = f"{run_id}/staging.dump"
        report["backup_sha256"] = hashlib.sha256(dump.read_bytes()).hexdigest()
        report["backup_bytes"] = dump.stat().st_size
        report["restore_started_at_utc"] = timestamp()
        started = time.monotonic()
        run(["pg_restore", "--dbname=ems_restore_test", "--exit-on-error", "--no-owner", "--no-acl", str(dump)], "restore.log")
        report["restore_seconds"] = time.monotonic() - started
        report["restore_completed_at_utc"] = timestamp()
        after = snapshot("ems_restore_test")
        if before != after or after["invalid_indexes"] or after["unvalidated_constraints"]:
            raise RuntimeError("Restored data/index/constraint verification failed")
        (evidence / "restore-validation.json").write_text(json.dumps({"source": before, "restored": after, "exact_match": True}, indent=2) + "\n")
        run([amcheck, "--database=ems_restore_test", "--install-missing", "--heapallindexed", "--parent-check", "--verbose"], "restore-integrity.log")
        report["restored_integrity_check"] = "pg_amcheck passed; counts/content hashes match; no invalid indexes or unvalidated constraints"
        restored_env = dict(env, EMS_DB_NAME="ems_restore_test")
        manage("migrate", "--check", output="restored-migrations.log", run_env=restored_env)
        manage("check", output="restored-check.log", run_env=restored_env)
        server = start_server(restored_env)
        report["restored_readiness"] = ready(server)
        server.terminate()
        server.wait(timeout=30)
        server = None
        report["tests"] = "skipped explicitly" if args.skip_tests else "pending"
        if not args.skip_tests:
            print("Running full Django suite on PostgreSQL", flush=True)
            test_env = dict(env, DJANGO_SETTINGS_MODULE="config.settings", DJANGO_DEBUG="true")
            manage("test", "--noinput", output="postgres-tests.log", run_env=test_env)
            run([sys.executable, "-m", "unittest", "discover", "-s", "scripts", "-p", "test_*.py"], "script-tests.log", test_env)
            report["tests"] = "Django PostgreSQL suite and benchmark regression tests passed"
        run([sys.executable, "-m", "pip", "freeze"], "python-packages.txt")
        report["status"] = "completed"
        report["completed_at_utc"] = timestamp()
        print("Completed staging, benchmarks and isolated restore verification", flush=True)
    except Exception as exception:
        report["status"] = "failed"
        report["failure"] = str(exception)
        raise
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        if server_log:
            server_log.close()
        if postgres_started:
            stopped = subprocess.run(["pg_ctl", "-D", str(work / "pgdata"), "-m", "fast", "-w", "stop"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            report["postgres_stopped"] = stopped.returncode == 0
        save()


if __name__ == "__main__":
    main()
