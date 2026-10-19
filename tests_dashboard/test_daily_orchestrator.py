import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from dashboard.daily_orchestrator import DailyOrchestrator, atomic_write_public_json

T = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.runner = DailyOrchestrator(self.db, clock=lambda:T)

    def tearDown(self):
        self.db.close()

    def test_missing_workers_fail_closed(self):
        x = self.runner.run(now=T)
        self.assertEqual(x['status'], 'partial')
        self.assertFalse(x['hosted_verified'])
        self.assertFalse(x['pilot_enabled'])

    def test_exactly_once_daily_claim(self):
        called = []
        def source():
            called.append(1)
            return None
        one = self.runner.run(source_worker=source,
                              research_worker=lambda:{'fixtures':[], 'status':'verified'}, now=T)
        two = self.runner.run(source_worker=source,
                              research_worker=lambda: {'fixtures':[], 'status':'verified'}, now=T)
        self.assertEqual(one['status'], 'done')
        self.assertEqual(two['status'], 'already_recorded')
        self.assertEqual(len(called), 1)

    def test_partial_retry_after_cooldown_bounded(self):
        from datetime import timedelta
        first = self.runner.run(now=T)
        self.assertEqual(first['status'], 'partial')
        early = self.runner.run(now=T + timedelta(minutes=10))
        self.assertEqual(early['status'], 'already_recorded')
        second = self.runner.run(source_worker=lambda:None,
                                 research_worker=lambda:{'fixtures':[], 'status':'verified'},
                                 now=T+timedelta(minutes=31))
        self.assertEqual(second['status'], 'done')
        self.assertEqual(self.runner.public_status()['runs'][0]['attempts'],2)

    def test_source_failures_are_redacted(self):
        calls = iter([{'status':'failed','secret':'DO_NOT_LEAK'}, None])
        x = self.runner.run(source_worker=lambda:next(calls),
                            research_worker=lambda:{'fixtures':[], 'status':'verified'},now=T)
        self.assertEqual(x['status'], 'partial')
        self.assertNotIn('DO_NOT_LEAK',json.dumps(self.runner.public_status()))

    def test_reconcile_dedupes_plan_ids(self):
        class Scheduler:
            def __init__(self): self.calls=[]
            def reconcile(self, key):
                self.calls.append(key)
                return {'status':'graded','graded':2}
        scheduler = Scheduler()
        x = self.runner.run(source_worker=lambda:None,
                            research_worker=lambda:{'fixtures':[], 'status':'verified'},
                            result_scheduler=scheduler,result_plan_ids=['a','a','b'],now=T)
        self.assertEqual(x['graded'],4)
        self.assertEqual(scheduler.calls,['a','b'])

    def test_duplicate_fixture_fails_closed(self):
        x = self.runner.run(source_worker=lambda:None,
                            research_worker=lambda:{'fixtures':[{'id':'x'},{'id':'x'}], 'status':'verified'},now=T)
        self.assertEqual(x['error_code'],'worker_failure')
        self.assertEqual(x['status'],'partial')

    def test_unexpected_exception_redacted(self):
        def bad(): raise RuntimeError('password=secret')
        x = self.runner.run(source_worker=bad,now=T)
        self.assertEqual(x['error_code'],'worker_failure')
        self.assertNotIn('secret',json.dumps(self.runner.public_status()))

    def test_aware_clock_required(self):
        with self.assertRaises(ValueError):
            self.runner.run(now=datetime(2026,10,19))

    def test_atomic_artifact_and_nonfinite_rejection(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)/'research.json'
            h = atomic_write_public_json(p, {'x':1})
            self.assertEqual(json.loads(p.read_text()), {'x':1})
            self.assertEqual(len(h),64)
            with self.assertRaises(ValueError):
                atomic_write_public_json(p,{'x':float('nan')})
            self.assertEqual(json.loads(p.read_text()), {'x':1})


if __name__ == '__main__': unittest.main()
