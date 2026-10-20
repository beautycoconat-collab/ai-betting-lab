import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from dashboard.automation import cycle, security_gates


class AutomationTests(unittest.TestCase):
    def test_security_gates_fail_closed(self):
        gates=security_gates({})
        self.assertFalse(gates['hosted_auth_rls_accepted'])
        self.assertFalse(gates['portfolio_execution'])
        self.assertFalse(gates['pilot_enabled'])

    def test_missing_persistent_quota_ledger_blocks_network_cycle(self):
        with tempfile.TemporaryDirectory() as d:
            status=Path(d)/'status.json'
            with self.assertRaisesRegex(ValueError,'persistent_quota_ledger_required'):
                cycle(Path(d)/'q.sqlite',Path(d)/'dashboard.json',status,
                      now=datetime(2026,10,19,tzinfo=timezone.utc),env={})
            body=json.loads(status.read_text())
            self.assertEqual(body['status'],'failed')
            self.assertFalse(body['portfolio_execution'])

    @patch('dashboard.automation.run')
    @patch('dashboard.automation._track_results')
    def test_cycle_publishes_status_and_never_promotes_predictions(self, tracker, runner):
        tracker.return_value={'status':'insufficient_data','reason':'no_approved_locked_predictions',
                              'plans':0,'duplicate_results':0}
        runner.return_value={'fixtures':[{'prediction_status':'conditional_scenarios'},
                                         {'prediction_status':'insufficient_data'}],
                             'collection':{'status':'done'},
                             'execution_enabled':False,'pilot_enabled':False}
        with tempfile.TemporaryDirectory() as d:
            out,status=Path(d)/'dashboard.json',Path(d)/'status.json'
            projection,report=cycle(Path(d)/'q.sqlite',out,status,
                now=datetime(2026,10,19,tzinfo=timezone.utc),
                env={'LAB_QUOTA_LEDGER_RESTORED':'true'})
            self.assertEqual(report['status'],'completed')
            self.assertEqual(report['phases']['research']['approved_forward_predictions'],0)
            self.assertEqual(report['phases']['result_tracking']['status'],'insufficient_data')
            self.assertFalse(projection['automation']['pilot_enabled'])
            self.assertEqual(json.loads(out.read_text())['automation']['status'],'completed')

    @patch('dashboard.automation.run')
    @patch('dashboard.automation._track_results')
    def test_supabase_write_requires_hosted_acceptance(self, tracker, runner):
        tracker.return_value={'status':'insufficient_data','plans':0}
        runner.return_value={'fixtures':[],'collection':{'status':'cached'},
                             'execution_enabled':False,'pilot_enabled':False}
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'hosted_security_acceptance_required'):
                cycle(Path(d)/'q.sqlite',Path(d)/'out.json',Path(d)/'status.json',
                      now=datetime(2026,10,19,tzinfo=timezone.utc),persist=True,
                      env={'LAB_QUOTA_LEDGER_RESTORED':'true'})

    def test_result_tracker_has_no_fake_metrics_without_locked_predictions(self):
        from dashboard.automation import _track_results
        with tempfile.TemporaryDirectory() as d:
            report=_track_results(Path(d)/'q.sqlite',datetime(2026,10,19,tzinfo=timezone.utc))
            self.assertEqual(report['status'],'insufficient_data')
            self.assertEqual(report['plans'],0)
            self.assertEqual(report['performance']['windows']['7']['graded_predictions'],0)


if __name__=='__main__':unittest.main()
