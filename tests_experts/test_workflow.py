import unittest
from experts.workflow import ResearchLab, StrategyExperiments
from experts.review import ReviewSession
from tests_experts import test_experts as support
from tests_experts.test_experts import LocalCase, fixture, NOW, REGISTRY


class WorkflowTests(LocalCase):
    @classmethod
    def setUpClass(cls):
        support.FootballTests.setUpClass()

    def lab(self):
        return ResearchLab(support.FootballTests.engine, support.FootballTests.synth, REGISTRY, self.runtime)

    def test_end_to_end_missing_evidence_abstains(self):
        output = self.lab().run(fixture(), NOW, [], {})
        self.assertEqual(output['reviews'][-1]['status'], 'abstain')
        self.assertEqual(output['risk_preview']['action'], 'skip')
        self.assertFalse(output['execution_enabled'])
        self.assertEqual(output['markets']['half1']['status'], 'insufficient_data')
        self.assertTrue(self.runtime.verify_audit())

    def test_team_total_markets_visible_without_prospectively_placing_bet(self):
        output = self.lab().run(fixture(), NOW, [], {})
        for key in ('over_2.5', 'under_2.5', 'home_over_1.5', 'away_over_1.5'):
            self.assertEqual(output['markets'][key]['status'], 'supported')
        self.assertAlmostEqual(
            output['markets']['home_over_1.5']['win']
            + output['markets']['home_over_1.5']['lose'], 1, places=9)
        self.assertFalse(output['execution_enabled'])

    def test_workflow_retry_does_not_add_review_rounds(self):
        lab = self.lab()
        a = lab.run(fixture(), NOW, [], {})
        b = lab.run(fixture(), NOW, [], {})
        self.assertEqual(a, b)
        self.assertEqual(self.runtime.db.execute("SELECT count(*) FROM f_audit WHERE event='expert_review'").fetchone()[0], 2)

    def test_retrospective_model_not_live(self):
        with self.assertRaises(ValueError):
            self.lab().run(fixture(), NOW, [], {}, mode='prematch')

    def test_critical_quarantine_blocks_even_with_lineup(self):
        a = support.claim()
        b = support.claim(id='bad', topic='injury', published_at=None)
        output = self.lab().run(fixture(), NOW, [a, b], support.snapshot(a))
        self.assertEqual(output['reviews'][-1]['status'], 'abstain')
        self.assertIn('source_conflict', [f['issue_type'] for f in output['findings']])

    def test_prediction_record_append_only_and_idempotent(self):
        lab = self.lab()
        lab.run(fixture(), NOW, [], {})
        lab.run(fixture(), NOW, [], {})
        self.assertEqual(self.runtime.db.execute("SELECT count(*) FROM f_audit WHERE event='research_completed'").fetchone()[0], 1)
        with self.assertRaises(Exception):
            self.runtime.db.execute("UPDATE f_audit SET event='changed' WHERE event='research_completed'")
        self.runtime.db.rollback()

    def test_experiment_aggregate_only(self):
        result = StrategyExperiments().evaluate(support.FootballTests.synth, support.FootballTests.test_rows)
        self.assertEqual(result['stored_coupons'], 0)
        self.assertIsNone(result['roi'])

    def test_experiment_overlap_refused(self):
        with self.assertRaises(ValueError):
            StrategyExperiments().evaluate(support.FootballTests.synth, support.FootballTests.validation)


if __name__ == '__main__':
    unittest.main()
