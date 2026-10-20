import tempfile
import unittest
from pathlib import Path
from foundation.runtime import Runtime
from experts.dispatcher import Dispatcher, validation_handler
from foundation.contracts import JobRequest


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.now = '2026-10-16T10:00:00+00:00'
        self.r = Runtime(Path(self.tmp.name) / 'test.db', clock=lambda: self.now)

    def tearDown(self):
        self.r.queue.close()
        self.tmp.cleanup()

    def job(self, key='test-job-1', kind='collect', deps=()):
        return self.r.enqueue(dict(schema_version='1.0', kind=kind, idempotency_key=key), deps)

    def test_dependency_output_and_idempotency(self):
        first = self.job()
        self.assertEqual(first, self.job())
        self.job('test-job-2', 'validate', [first])
        def validate(job, deps):
            self.assertEqual(deps[first].data, {'count': 3})
            return dict(schema_version='1.0', status='ready')
        d = Dispatcher(self.r, {'collect': lambda j, deps: dict(schema_version='1.0', status='ready', data={'count': 3}), 'validate': validate})
        self.assertIsNone(d.work_one('v', 'data_validator'))
        self.assertEqual(d.work_one('c', 'source_hunter')['status'], 'done')
        self.assertEqual(d.work_one('v', 'data_validator')['status'], 'done')
        self.assertIsNone(d.work_one('c', 'source_hunter'))
        self.assertTrue(self.r.verify_audit())

    def test_unavailable_handler_blocks_dependents(self):
        first = self.job()
        second = self.job('test-job-2', 'validate', [first])
        d = Dispatcher(self.r, {})
        self.assertEqual(d.work_one('w', 'source_hunter')['status'], 'blocked')
        self.assertIsNone(d.work_one('v', 'data_validator'))
        self.assertEqual(self.r.db.execute('SELECT status FROM f_tasks WHERE id=?', (second,)).fetchone()[0], 'blocked')

    def test_expired_worker_cannot_publish(self):
        self.job()
        def slow(j, deps):
            self.now = '2026-10-16T11:00:00+00:00'
            return dict(schema_version='1.0', status='ready')
        self.assertEqual(Dispatcher(self.r, {'collect': slow}).work_one('w', 'source_hunter')['status'], 'lease_lost')
        self.assertEqual(self.r.db.execute('SELECT count(*) FROM expert_task_outputs').fetchone()[0], 0)

    def test_error_sanitized_and_retried(self):
        tid = self.job()
        def fail(j, deps):
            raise ValueError('secret-do-not-log')
        d = Dispatcher(self.r, {'collect': fail})
        self.assertEqual(d.work_one('w', 'source_hunter')['status'], 'retry_or_failed')
        self.assertEqual(self.r.db.execute('SELECT last_error FROM f_tasks WHERE id=?', (tid,)).fetchone()[0], 'ValueError')
        self.assertIsNone(d.work_one('w', 'source_hunter'))

    def test_cancel_and_append_only(self):
        tid = self.job()
        d = Dispatcher(self.r, {})
        self.assertTrue(d.cancel(tid))
        self.assertFalse(d.cancel(tid))
        self.assertIsNone(d.work_one('w', 'source_hunter'))

    def test_real_validator_binding(self):
        from tests_experts.test_experts import fixture, claim, snapshot, REGISTRY, NOW
        f, c = fixture(), claim()
        payload = dict(fixture=f.model_dump(mode='json'), claims=[c], as_of=NOW, snapshots=snapshot(c))
        handler = validation_handler(REGISTRY, lambda job: payload)
        job = JobRequest(schema_version='1.0', kind='validate', fixture_id=f.id, idempotency_key='validation-test')
        self.assertEqual(handler(job, {}).status, 'ready')
        payload['snapshots'] = {}
        self.assertEqual(handler(job, {}).status, 'blocked')

    def test_outputs_are_append_only(self):
        import sqlite3
        self.job()
        d = Dispatcher(self.r, {'collect': lambda j, deps: dict(schema_version='1.0', status='ready')})
        d.work_one('w', 'source_hunter')
        with self.assertRaises(sqlite3.IntegrityError):
            self.r.db.execute("UPDATE expert_task_outputs SET body='{}'")
        self.r.db.rollback()

    def test_other_worker_cannot_take_live_lease(self):
        self.job()
        self.assertIsNotNone(self.r.claim('first', 'source_hunter'))
        other = Runtime(Path(self.tmp.name) / 'test.db', clock=lambda: self.now)
        try:
            self.assertIsNone(other.claim('second', 'source_hunter'))
        finally:
            other.queue.close()

    def test_cancel_during_handler_fences_output(self):
        tid = self.job()
        d = Dispatcher(self.r, {})
        def cancelled(j, deps):
            d.cancel(tid)
            return dict(schema_version='1.0', status='ready')
        d.handlers['collect'] = cancelled
        self.assertEqual(d.work_one('w', 'source_hunter')['status'], 'lease_lost')
        self.assertEqual(self.r.db.execute('SELECT count(*) FROM expert_task_outputs').fetchone()[0], 0)
