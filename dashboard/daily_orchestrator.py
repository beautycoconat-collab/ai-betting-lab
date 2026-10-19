"""Durable local research orchestration; deliberately not a hosted authorization proof.

The run ledger is SQLite-backed and idempotent across repeated invocations.  It
coordinates existing source and result workers, but never fabricates research,
changes source quotas, writes hosted data or enables portfolio execution.
"""
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS lab_daily_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    state TEXT NOT NULL CHECK(state IN ('running','done','partial','failed')),
    fixtures INTEGER NOT NULL DEFAULT 0,
    sources INTEGER NOT NULL DEFAULT 0,
    graded INTEGER NOT NULL DEFAULT 0,
    error_code TEXT,
    attempts INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS lab_daily_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES lab_daily_runs(run_id),
    category TEXT NOT NULL,
    status TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    UNIQUE(run_id,category,status,event_id)
);
'''


def utc_now():
    return datetime.now(timezone.utc)


def _instant(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('aware_utc_clock_required')
    return value.astimezone(timezone.utc)


def _event_id(run_id, category, status, index):
    return hashlib.sha256(json.dumps([run_id, category, status, index]).encode()).hexdigest()


class DailyOrchestrator:
    """Single SQLite process gate; only an approved upstream worker may fetch.

    `source_worker` and `research_worker` are injected existing components.
    A source worker returns a dict with a status; a research worker returns a
    dict with `fixtures` and optional `status`. Neither is assumed trustworthy
    for hosted publication or model approval. `result_scheduler` must be an
    existing ResultScheduler instance, not a replacement verifier.
    """

    def __init__(self, db, *, clock=utc_now):
        self.db, self.clock = db, clock
        db.executescript(SCHEMA)

    def _log(self, run_id, category, status, index, now):
        self.db.execute('INSERT OR IGNORE INTO lab_daily_events VALUES(?,?,?,?,?)',
                        (_event_id(run_id, category, status, index), run_id,
                         category, status, now.isoformat()))

    def run(self, *, source_worker=None, research_worker=None, result_scheduler=None,
            result_plan_ids=(), max_source_jobs=20, now=None):
        now = _instant(now or self.clock())
        if type(max_source_jobs) is not int or not 0 <= max_source_jobs <= 200:
            raise ValueError('invalid_source_job_limit')
        run_id = now.date().isoformat()
        # Atomic run claim: concurrent workers cannot both claim the same day.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            existing = self.db.execute('SELECT * FROM lab_daily_runs WHERE run_id=?',
                                       (run_id,)).fetchone()
            if existing:
                # Retry only a finished partial run after a cooldown. An active
                # or successful run is never stolen. Source jobs and journal
                # writes retain their own idempotency and lease fencing.
                from datetime import timedelta
                prior = _instant(datetime.fromisoformat(existing['finished_at'])) if existing['finished_at'] else None
                if (existing['state'] != 'partial' or prior is None or
                        now - prior < timedelta(minutes=30) or existing['attempts'] >= 3):
                    self.db.commit()
                    return {'run_id': run_id, 'status': 'already_recorded',
                            'previous_status': existing['state'],
                            'fixtures': existing['fixtures'], 'sources': existing['sources'],
                            'graded': existing['graded']}
                self.db.execute('''UPDATE lab_daily_runs SET state='running',started_at=?,
                    finished_at=NULL,error_code=NULL,attempts=attempts+1 WHERE run_id=?''',
                    (now.isoformat(),run_id))
            else:
                self.db.execute('INSERT INTO lab_daily_runs(run_id,started_at,state) VALUES(?,?,?)',
                                (run_id, now.isoformat(), 'running'))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        sources = graded = fixtures = 0
        partial = False
        error_code = None
        try:
            if source_worker is None:
                partial = True
                with self.db:
                    self._log(run_id, 'source', 'not_configured', 0, now)
            else:
                for i in range(max_source_jobs):
                    item = source_worker()
                    if item is None:
                        break
                    if not isinstance(item, dict):
                        raise ValueError('invalid_source_worker_response')
                    sources += 1
                    status = item.get('status', 'unknown')
                    safe_status = status if status in ('done','cached','deferred','blocked','failed','lease_lost') else 'unknown'
                    with self.db:
                        self._log(run_id, 'source', safe_status, i, now)
                    if safe_status not in ('done','cached'):
                        partial = True
            if research_worker is None:
                partial = True
                with self.db:
                    self._log(run_id, 'research', 'not_configured', 0, now)
            else:
                outcome = research_worker()
                if not isinstance(outcome, dict) or not isinstance(outcome.get('fixtures'), list):
                    raise ValueError('invalid_research_response')
                ids = set()
                for item in outcome['fixtures']:
                    if not isinstance(item, dict) or not isinstance(item.get('id'), str):
                        raise ValueError('invalid_fixture_identity')
                    if item['id'] in ids:
                        raise ValueError('duplicate_fixture_identity')
                    ids.add(item['id'])
                fixtures = len(ids)
                # No publication or 'approved' inference from this count.
                if outcome.get('status') != 'verified':
                    partial = True
                with self.db:
                    self._log(run_id, 'research', 'observed', 0, now)
            if result_plan_ids:
                if result_scheduler is None:
                    partial = True
                    with self.db:
                        self._log(run_id, 'result', 'not_configured', 0, now)
                else:
                    for i, plan_id in enumerate(dict.fromkeys(result_plan_ids)):
                        response = result_scheduler.reconcile(plan_id)
                        if not isinstance(response, dict):
                            raise ValueError('invalid_result_response')
                        graded += int(response.get('graded', 0))
                        status = response.get('status')
                        safe = status if status in ('graded','waiting_for_final','source_pending',
                                'source_running','source_blocked','source_failed','stale_snapshot_repoll_next_cycle',
                                'snapshot_missing_or_ambiguous','manual_review_required') else 'unknown'
                        if safe != 'graded':
                            partial = True
                        with self.db:
                            self._log(run_id, 'result', safe, i, now)
        except (ValueError, sqlite3.Error, OSError, TimeoutError, RuntimeError):
            # Fail closed. Do not serialize raw exceptions, provider URLs or secrets.
            partial, error_code = True, 'worker_failure'
        state = 'partial' if partial else 'done'
        with self.db:
            self.db.execute('''UPDATE lab_daily_runs SET state=?,finished_at=?,fixtures=?,sources=?,
                graded=?,error_code=? WHERE run_id=? AND state='running' ''',
                (state, _instant(self.clock()).isoformat(), fixtures, sources, graded,
                 error_code, run_id))
        return {'run_id':run_id, 'status':state, 'fixtures':fixtures,
                'sources':sources, 'graded':graded, 'error_code':error_code,
                'hosted_verified':False, 'pilot_enabled':False}

    def public_status(self, *, limit=7):
        if type(limit) is not int or not 1 <= limit <= 31:
            raise ValueError('invalid_limit')
        rows = self.db.execute('''SELECT run_id,started_at,finished_at,state,fixtures,sources,graded,error_code,attempts
            FROM lab_daily_runs ORDER BY run_id DESC LIMIT ?''', (limit,)).fetchall()
        return {'schema_version':'1.0', 'schedule_enabled':False,
                'hosted_worker_verified':False, 'pilot_enabled':False,
                'runs':[dict(row) for row in rows]}


def atomic_write_public_json(path, payload):
    """Safe publication of a local research artifact, not hosted deployment."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True).encode('utf-8')
    if len(encoded) > 5_000_000:
        raise ValueError('public_artifact_too_large')
    temp = target.with_name(target.name + '.tmp.' + str(os.getpid()))
    try:
        with open(temp, 'xb') as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()
    return hashlib.sha256(encoded).hexdigest()
