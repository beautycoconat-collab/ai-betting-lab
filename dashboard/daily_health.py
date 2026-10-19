"""Bounded, read-only public status for the existing daily source/worker queues.

Does not trigger a fetch, write to Supabase, reset quota, schedule a cron,
or enable the virtual portfolio. Raw task inputs and error strings stay private.
"""
from datetime import datetime, timezone

SOURCE_STATES = frozenset({'pending', 'running', 'done', 'blocked', 'failed'})
EXPERT_STATES = frozenset({'pending', 'running', 'done', 'blocked', 'failed', 'cancelled'})


def summary(db, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('timezone_required')
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    def counts(table, allowed):
        if table not in tables:
            return {'status': 'unavailable', 'counts': {}}
        result = {}
        for state, count in db.execute('SELECT status, COUNT(*) FROM ' + table + ' GROUP BY status'):
            label = state if state in allowed else 'other'
            result[label] = result.get(label, 0) + count
        return {'status': 'observed', 'counts': result}

    sources = []
    if 'v2_health' in tables:
        for source, successes, failures, consecutive, last_success in db.execute(
                'SELECT source, successes, failures, consecutive_failures, last_success '
                'FROM v2_health ORDER BY source LIMIT 100'):
            sources.append({'source': source, 'successes': successes,
                            'failures': failures, 'consecutive_failures': consecutive,
                            'last_success': last_success})

    return {'schema_version': '1.0', 'as_of': now.isoformat(),
            'status': 'observed_local_only', 'schedule_enabled': False,
            'hosted_worker_verified': False, 'pilot_enabled': False,
            'source_jobs': counts('v2_jobs', SOURCE_STATES),
            'expert_tasks': counts('f_tasks', EXPERT_STATES),
            'source_health': sources,
            'note': 'Local queue observation; not proof of a daily hosted run.'}
