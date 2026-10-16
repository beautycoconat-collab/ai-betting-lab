import json
import unittest
from pathlib import Path
from experts.walkforward import evaluate


class WalkForwardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((Path(__file__).resolve().parents[1]/'reports/phase2/bundesliga/dataset.json').read_text())

    def test_disjoint_folds_and_retraining(self):
        r = evaluate(self.rows, [('2025-01-01', '2025-02-01', '2025-03-01'), ('2025-02-01', '2025-03-01', '2025-04-01')])
        self.assertEqual(r['unique_test_matches'], sum(f['test_n'] for f in r['folds']))
        self.assertGreater(r['folds'][1]['train_n'], r['folds'][0]['train_n'])

    def test_overlap_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(self.rows, [('2025-01-01', '2025-02-01', '2025-03-01')]*2)

    def test_invalid_boundaries(self):
        with self.assertRaises(ValueError):
            evaluate(self.rows, [('2025-03-01', '2025-02-01', '2025-04-01')])

    def test_empty_folds(self):
        with self.assertRaises(ValueError):
            evaluate(self.rows, [])
