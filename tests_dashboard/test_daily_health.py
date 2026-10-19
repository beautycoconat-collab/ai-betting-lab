import json
import sqlite3
import unittest
from datetime import datetime, timezone
from dashboard.daily_health import summary


class DailyHealthTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.now = datetime(2026, 10, 19, 18, tzinfo=timezone.utc)

    def tearDown(self):
        self.db.close()

    def test_missing_tables_not_claimed_as_success(self):
        status = summary(self.db, self.now)
        self.assertEqual(status['source_jobs']['status'], 'unavailable')
        self.assertEqual(status['expert_tasks']['status'], 'unavailable')
        self.assertFalse(status['schedule_enabled'])
        self.assertFalse(status['pilot_enabled'])

    def test_counts_are_aggregated_without_exposing_sensitive_fields(self):
        self.db.execute('CREATE TABLE v2_jobs(status TEXT, params TEXT, last_error TEXT)')
        self.db.execute('CREATE TABLE f_tasks(status TEXT, body TEXT)')
        self.db.execute('CREATE TABLE v2_health(source TEXT, successes INT, failures INT, consecutive_failures INT, last_success TEXT, last_error TEXT)')
        self.db.executemany('INSERT INTO v2_jobs VALUES(?,?,?)', [
            ('done', 'SECRET_TOKEN_1', 'secret'), ('done', 'SECRET_TOKEN_2', 'secret'),
            ('failed', 'SECRET_TOKEN_3', 'secret')])
        self.db.execute('INSERT INTO f_tasks VALUES(?,?)', ('blocked', 'SECRET_TASK'))
        self.db.execute('INSERT INTO v2_health VALUES(?,?,?,?,?,?)',
                        ('openliga', 2, 1, 1, self.now.isoformat(), 'SECRET_ERROR'))
        report = summary(self.db, self.now)
        self.assertEqual(report['source_jobs']['counts'], {'done': 2, 'failed': 1})
        self.assertEqual(report['expert_tasks']['counts'], {'blocked': 1})
        self.assertEqual(report['source_health'][0]['source'], 'openliga')
        raw = json.dumps(report)
        self.assertNotIn('SECRET', raw)
        self.assertFalse(report['hosted_worker_verified'])

    def test_unknown_status_is_sanitized(self):
        self.db.execute('CREATE TABLE v2_jobs(status TEXT)')
        self.db.executemany('INSERT INTO v2_jobs VALUES(?)', [('surprise-private',), ('surprise-private',)])
        self.assertEqual(summary(self.db, self.now)['source_jobs']['counts'], {'other': 2})

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            summary(self.db, datetime(2026, 10, 19))
