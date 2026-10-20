"""Fail-closed GitHub Actions scheduled-run gate; stdlib-only, no secrets logged.

Scheduling a workflow is not authorization to fetch, publish or place wagers.
This gate validates a durable quota database and fresh, independently signed-off
hosted acceptance manifest before the worker is allowed to run. A hosted DB
cannot be replaced with a GitHub cache or a fresh empty SQLite file.
"""
import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dashboard.hosted_readiness import inspect

REQUIRED_TABLES = ('requests', 'cooldowns', 'v2_jobs', 'v2_snapshots', 'lab_daily_runs')


def evaluate(*, manifest_path, db_path, env=None, now=None):
    env = os.environ if env is None else env
    now = now or datetime.now(timezone.utc)
    problems = []
    # Environment variables are an additional switch, never a substitute for proof.
    if env.get('LAB_RESEARCH_ACCEPTED') != 'true':
        problems.append('research_not_accepted')
    if env.get('LAB_DURABLE_QUOTA_VERIFIED') != 'true':
        problems.append('durable_quota_not_accepted')
    if env.get('LAB_HOSTED_SECURITY_ACCEPTED') != 'true':
        problems.append('hosted_security_not_accepted')
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError):
        manifest = {}
    acceptance = inspect(manifest, now=now)
    if acceptance['status'] != 'review_ready':
        problems.extend('acceptance_' + k for k in acceptance['missing'])
    db = Path(db_path)
    if not db.is_file() or db.stat().st_size == 0:
        problems.append('durable_database_missing')
    else:
        try:
            # mode=ro prevents silently creating an empty database.
            uri = db.resolve().as_uri() + '?mode=ro'
            with sqlite3.connect(uri, uri=True, timeout=2) as con:
                integrity = con.execute('PRAGMA quick_check').fetchone()
                if integrity != ('ok',):
                    problems.append('database_integrity_failed')
                tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                problems.extend('missing_table_' + name for name in REQUIRED_TABLES if name not in tables)
        except (sqlite3.Error, OSError, ValueError):
            problems.append('database_unreadable')
    return {'status': 'ready' if not problems else 'blocked',
            'reasons': sorted(set(problems)), 'source_collection_allowed': not problems,
            'portfolio_enabled': False, 'real_money_enabled': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', default='config/hosted-acceptance.json')
    p.add_argument('--database', default='data/dashboard-live.sqlite')
    p.add_argument('--output', default='daily-gate-report.json')
    a = p.parse_args()
    result = evaluate(manifest_path=a.manifest, db_path=a.database)
    Path(a.output).write_text(json.dumps(result, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, sort_keys=True))
    if result['status'] != 'ready':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
