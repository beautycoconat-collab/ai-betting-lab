"""CLI execution paths use existing locked test fixtures; never contact a network."""
import unittest
from experts.result_scheduler import ResultScheduler
from scripts.result_cycle import cycle
import tests_experts.test_outcome_journal as outcome_tests


class ResultCycleCommandTests(unittest.TestCase):
    def setUp(self):
        self.test_fixture=outcome_tests.ForwardOutcomeTests('test_verified_result_and_graded_prediction_with_audit')
        self.test_fixture.setUp()
        self.test_fixture.locked()

    def tearDown(self):
        self.test_fixture.tearDown()

    def test_explicit_plan_reconcile_report(self):
        h=self.test_fixture
        manifest=[{'fixture_id':h.fid,'source_id':'openfootball','params':h.source_params,'native_id':h.nid}]
        created=cycle(h.r,'plan',manifest)
        self.assertEqual(len(created['plans']),1)
        self.assertFalse(created['live_fetch'])
        waiting=cycle(h.r,'reconcile')
        self.assertEqual(waiting['results'][0]['status'],'source_pending')
        report=cycle(h.r,'report')
        self.assertEqual(report['performance']['windows']['7']['pending_predictions'],1)

    def test_wrong_or_bulk_manifest_rejected(self):
        h=self.test_fixture
        with self.assertRaisesRegex(ValueError,'invalid_plan_manifest_entry'):
            cycle(h.r,'plan',[{'fixture_id':h.fid}])
        with self.assertRaisesRegex(ValueError,'too_large'):
            cycle(h.r,'plan',[{}]*501)
        with self.assertRaisesRegex(ValueError,'unknown_cycle_mode'):
            cycle(h.r,'really-publish')
