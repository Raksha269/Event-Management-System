"""Run the agreed local production baseline using rootless Podman or Docker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]

DB_IMAGE = "docker.io/library/postgres:16-bookworm"
APP_IMAGE = "localhost/ems-staging:local"


def read_limits(cpu, memory):
    """Reject silently ignored quotas, including rootless runtime limitations."""
    quota, period = cpu.split()
    if quota == "max" or int(quota) != int(period) or int(memory) <= 0:
        raise RuntimeError("Expected an enforced one-CPU quota and finite memory limit")
    return {"cpu.max": cpu.strip(), "memory.max": int(memory)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", choices=["podman", "docker"], default="podman")
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix:
        parser.error("Run with .venv/bin/python")
    runtime = shutil.which(args.runtime)
    if not runtime:
        parser.error(f"{args.runtime} is not installed")
    os.umask(0o077)
    run_id = timestamp().replace("-", "").replace(":", "").split(".")[0] + "Z-container"
    private = ROOT / ".staging" / run_id
    private.mkdir(parents=True)
    evidence = ROOT / "docs/staging/evidence" / run_id
    evidence.mkdir(parents=True)
    password = secrets.token_urlsafe(32)
    names = {key: "ems-" + key + "-" + secrets.token_hex(4) for key in ("source", "restore", "app", "restored-app")}
    created = []
    ports = {key: free_port() for key in ("source", "restore", "http", "restored-http")}
    env = dict(os.environ, DJANGO_SETTINGS_MODULE="config.staging_settings", DJANGO_DEBUG="false",
               DJANGO_SECRET_KEY=secrets.token_urlsafe(48), EMS_DB_ENGINE="postgresql", EMS_DB_NAME="ems_staging",
               EMS_DB_USER="ems_runner", EMS_DB_PASSWORD=password, EMS_DB_HOST="127.0.0.1",
               EMS_DB_PORT=str(ports["source"]), EMS_DB_SSLMODE="disable", EMS_DB_CONN_MAX_AGE="60",
               EMS_ISOLATED_STAGING="synthetic-only", EMS_AUDIT_RETENTION_DAYS="1095")
    report = {"scope": "Owner-approved local production-comparable baseline; no hosted deployment claimed",
              "started_at_utc": timestamp(), "operator": os.environ.get("USER", "unknown"),
              "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "status": "running", "runtime": args.runtime,
              "baseline": {"app": {"cpus": 1, "memory_bytes": 536870912, "workers": 2, "threads": 4},
                           "database": {"cpus": 1, "memory_bytes": 1073741824, "max_connections": 64,
                                        "shared_buffers": "128MB"},
                           "swap": "disabled for each container", "load_generator": "host .venv, outside service quotas"},
              "backup_policy": {"frequency": "on demand once per verification session", "retention": "manual; no automatic expiry",
                                "encryption": "no harness-managed TLS/dump encryption; loopback only", "rpo": "no guaranteed time-based RPO",
                                "rto": "measured restore only; no guaranteed incident RTO"},
              "audit_policy": {"retention_days": 1095, "archive": "none", "purge_schedule": "none; manual command only"}}
    print(f"Evidence: {evidence.relative_to(ROOT)}", flush=True)

    def save():
        (evidence / "environment.json").write_text(json.dumps(report, indent=2) + "\n")

    def call(command, *, output=None, command_env=None, stdin=None, binary=False):
        if output:
            with (evidence / output).open("wb") as log:
                result = subprocess.run(command, cwd=ROOT, env=command_env or env, stdin=stdin,
                                        stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                raise RuntimeError(f"Command failed: inspect {output}")
            return None
        result = subprocess.run(command, cwd=ROOT, env=command_env or env, input=stdin,
                                capture_output=True, text=not binary)
        if result.returncode:
            # Full diagnostics remain private because runtime errors may include configuration.
            (private / "last-error.log").write_bytes(result.stderr if binary else result.stderr.encode())
            raise RuntimeError(f"Command failed; inspect {private / 'last-error.log'}")
        return result.stdout

    def container(*parts, **kwargs):
        return call([runtime, *parts], **kwargs)

    def manage(*parts, output, command_env=None):
        call([sys.executable, "manage.py", *parts], output=output, command_env=command_env)

    def start_db(key, database):
        config = private / f"{key}.env"
        config.write_text(f"POSTGRES_DB={database}\nPOSTGRES_USER=ems_runner\nPOSTGRES_PASSWORD={password}\n"
                          "POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256\n")
        created.append(names[key])
        container("run", "--detach", "--name", names[key], "--cpus=1", "--memory=1g", "--memory-swap=1g",
                  "--shm-size=256m", "--env-file", str(config),
                  "--publish", f"127.0.0.1:{ports[key]}:5432",
                  "--publish", f"127.0.0.1:{ports['http' if key == 'source' else 'restored-http']}:8000",
                  DB_IMAGE, "postgres", "-c", "max_connections=64", "-c", "shared_buffers=128MB")
        for _ in range(120):
            result = subprocess.run([runtime, "exec", names[key], "pg_isready", "-U", "ems_runner", "-d", database],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                # pg_isready can succeed during temporary init; verify published TCP too.
                try:
                    with connect(key, database):
                        return
                except Exception:
                    pass
            time.sleep(0.5)
        raise RuntimeError(f"{key} PostgreSQL readiness timed out")

    def start_app(key, database_key, database):
        config = private / f"{key}.env"
        config.write_text("\n".join(f"{k}={v}" for k, v in dict(env, EMS_DB_NAME=database, EMS_DB_PORT="5432").items()
                                    if k.startswith(("DJANGO_", "EMS_"))) + "\n")
        created.append(names[key])
        container("run", "--detach", "--name", names[key], "--network", f"container:{names[database_key]}",
                  "--cpus=1", "--memory=512m", "--memory-swap=512m", "--env-file", str(config), APP_IMAGE)
        http_port = ports["http" if database_key == "source" else "restored-http"]
        base = f"http://127.0.0.1:{http_port}"
        for _ in range(120):
            try:
                with urlopen(base + "/health/ready/", timeout=2) as response:
                    if response.status == 200:
                        return base, json.load(response)
            except OSError:
                time.sleep(0.5)
        raise RuntimeError(f"{key} HTTP readiness timed out")

    def verify_limits(key, memory):
        cpu = container("exec", names[key], "cat", "/sys/fs/cgroup/cpu.max")
        mem = container("exec", names[key], "cat", "/sys/fs/cgroup/memory.max")
        limits = read_limits(cpu, mem)
        if limits["memory.max"] != memory:
            raise RuntimeError(f"{key} memory quota was not enforced")
        limits["memory.swap.max"] = container("exec", names[key], "cat", "/sys/fs/cgroup/memory.swap.max").strip()
        if limits["memory.swap.max"] != "0":
            raise RuntimeError("Container swap was not disabled")
        return limits

    import psycopg
    from psycopg import sql

    def connect(key, database):
        return psycopg.connect(host="127.0.0.1", port=ports[key], user="ems_runner", password=password, dbname=database)

    def snapshot(key, database):
        with connect(key, database) as conn:
            tables = [row[0] for row in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
            counts, hashes = {}, {}
            for table in tables:
                rows = conn.execute(sql.SQL("SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text").format(sql.Identifier(table))).fetchall()
                counts[table] = len(rows)
                hashes[table] = hashlib.sha256("\n".join(row[0] for row in rows).encode()).hexdigest()
            return {"row_counts": counts, "table_sha256": hashes,
                    "invalid_indexes": conn.execute("SELECT count(*) FROM pg_index WHERE NOT indisvalid").fetchone()[0],
                    "unvalidated_constraints": conn.execute("SELECT count(*) FROM pg_constraint WHERE NOT convalidated").fetchone()[0]}

    save()
    try:
        print("Building application image with /opt/venv", flush=True)
        container("build", "--file", "infra/staging/Containerfile", "--tag", APP_IMAGE, ".", output="image-build.log")
        for label, image in (("database", DB_IMAGE), ("application", APP_IMAGE)):
            inspected = json.loads(container("image", "inspect", image))[0]
            report[f"{label}_image"] = {"id": inspected["Id"], "digests": inspected.get("RepoDigests", [])}
        files = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
        (evidence / "source-manifest.json").write_text(json.dumps({name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in sorted(set(files)) if (name.endswith(".py") or name in {"requirements.txt", "infra/staging/Containerfile"})
            and (ROOT / name).is_file()}, indent=2) + "\n")
        start_db("source", "ems_staging")
        report["source_database_limits"] = verify_limits("source", 1073741824)
        with connect("source", "ems_staging") as conn:
            report["postgres_version"] = conn.execute("SELECT version()").fetchone()[0]
        manage("migrate", "--noinput", output="migrate.log")
        manage("seed_postgres_staging", output="dataset.json")
        with connect("source", "ems_staging") as conn:
            conn.execute("ANALYZE")
        base, report["source_readiness"] = start_app("app", "source", "ems_staging")
        report["app_limits"] = verify_limits("app", 536870912)
        endpoint = base + "/api/v1/events/?q=Sample&limit=50&offset=0"
        with urlopen(endpoint, timeout=10) as response:
            payload = json.load(response)
        if not payload or (isinstance(payload, dict) and not payload.get("results")):
            raise RuntimeError("Search returned no matching published records")
        report["search_smoke_test"] = "HTTP 200, nonempty matching records"
        for clients in (10, 50, 100):
            print(f"Measuring {clients} clients under enforced CPU/memory quotas", flush=True)
            call([sys.executable, "scripts/nfr_search_benchmark.py"], output=f"search-{clients}.json",
                 command_env=dict(env, NFR_BENCHMARK_URL=endpoint, NFR_BENCHMARK_CLIENTS=str(clients)))
        report["service_stats_after_search"] = json.loads(container("stats", "--no-stream", "--format", "json", names["app"], names["source"]))
        container("stop", names["app"])
        before = snapshot("source", "ems_staging")
        report["backup_started_at_utc"] = timestamp()
        dump = call([runtime, "exec", names["source"], "pg_dump", "-U", "ems_runner", "-d", "ems_staging",
                     "--format=custom", "--no-owner", "--no-acl"], binary=True)
        (private / "staging.dump").write_bytes(dump)
        report.update(backup_completed_at_utc=timestamp(), backup_identifier=f"{run_id}/staging.dump",
                      backup_sha256=hashlib.sha256(dump).hexdigest(), backup_bytes=len(dump))
        start_db("restore", "ems_restore_test")
        report["restore_database_limits"] = verify_limits("restore", 1073741824)
        report["restore_started_at_utc"] = timestamp()
        started = time.monotonic()
        container("exec", "--interactive", names["restore"], "pg_restore", "-U", "ems_runner", "-d", "ems_restore_test",
                  "--exit-on-error", "--no-owner", "--no-acl", stdin=dump, binary=True)
        report.update(restore_seconds=time.monotonic() - started, restore_completed_at_utc=timestamp())
        after = snapshot("restore", "ems_restore_test")
        if before != after or after["invalid_indexes"] or after["unvalidated_constraints"]:
            raise RuntimeError("Source/restore data or integrity indicators differ")
        (evidence / "restore-validation.json").write_text(json.dumps({"source": before, "restored": after, "exact_match": True}, indent=2) + "\n")
        container("exec", names["restore"], "pg_amcheck", "-U", "ems_runner", "--database=ems_restore_test",
                  "--install-missing", "--heapallindexed", "--parent-check", "--verbose", output="restore-integrity.log")
        restore_env = dict(env, EMS_DB_PORT=str(ports["restore"]), EMS_DB_NAME="ems_restore_test")
        manage("migrate", "--check", output="restored-migrations.log", command_env=restore_env)
        manage("check", output="restored-check.log", command_env=restore_env)
        _, report["restored_readiness"] = start_app("restored-app", "restore", "ems_restore_test")
        report["restored_app_limits"] = verify_limits("restored-app", 536870912)
        print("Running Django tests against containerized PostgreSQL 16", flush=True)
        test_env = dict(env, DJANGO_SETTINGS_MODULE="config.settings", DJANGO_DEBUG="true")
        manage("test", "--noinput", output="postgres-tests.log", command_env=test_env)
        call([sys.executable, "-m", "unittest", "discover", "-s", "scripts", "-p", "test_*.py"], output="script-tests.log")
        # Dependencies in the image can differ from the host virtual environment: record both.
        container("exec", names["restored-app"], "/opt/venv/bin/python", "-m", "pip", "freeze", output="app-python-packages.txt")
        call([sys.executable, "-m", "pip", "freeze"], output="host-python-packages.txt")
        report.update(status="completed", completed_at_utc=timestamp(), tests="Django and script regressions passed",
                      restore_integrity="table hashes/counts, constraints/indexes, pg_amcheck, migrations and readiness passed")
    except Exception as exception:
        report.update(status="failed", error=str(exception))
        raise
    finally:
        cleanup = {}
        for name in reversed(created):
            # Only unique containers created by this run are removed, including anonymous PG volumes.
            with (private / f"{name}.log").open("wb") as log:
                subprocess.run([runtime, "logs", name], stdout=log, stderr=subprocess.STDOUT)
            result = subprocess.run([runtime, "rm", "--force", "--volumes", name], capture_output=True)
            cleanup[name] = result.returncode == 0
        report["containers_removed"] = cleanup
        save()
    print("Completed resource-limited staging, performance and cross-container recovery", flush=True)


if __name__ == "__main__":
    main()
