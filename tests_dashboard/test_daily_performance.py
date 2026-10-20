import json
import sqlite3
import unittest
from datetime import datetime, timezone
from dashboard.daily_performance import forward_metrics
T=datetime(2026,10,19,12,tzinfo=timezone.utc)
class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''CREATE TABLE lab_locked_predictions(prediction_id TEXT,fixture_id TEXT,captured_at TEXT,probabilities TEXT);
        CREATE TABLE lab_prediction_grades(prediction_id TEXT,recorded_at TEXT,log_loss REAL,brier REAL);
        CREATE TABLE lab_verified_results(fixture_id TEXT,result_body TEXT);''')
    def tearDown(self): self.db.close()
    def test_missing_tables(self):
        self.db.execute('DROP TABLE lab_verified_results')
        self.assertEqual(forward_metrics(self.db,T)['status'],'not_available')
    def test_verified_forward_only(self):
        self.db.execute('INSERT INTO lab_locked_predictions VALUES(?,?,?,?)',('p','f','2026-10-18T12:00:00+00:00',json.dumps([.6,.2,.2])))
        self.db.execute('INSERT INTO lab_prediction_grades VALUES(?,?,?,?)',('p','2026-10-19T11:00:00+00:00',.5108,.24))
        self.db.execute('INSERT INTO lab_verified_results VALUES(?,?)',('f',json.dumps({'status':'final','target':'regulation90','home':2,'away':0})))
        x=forward_metrics(self.db,T)
        self.assertEqual(x['windows']['7']['coverage'],1)
        self.assertAlmostEqual(x['windows']['7']['brier'],.24)
        self.assertEqual(sum(b['count'] for b in x['windows']['7']['calibration']),1)
        self.assertIsNone(x['roi'])
    def test_ungraded_not_in_metrics(self):
        self.db.execute('INSERT INTO lab_locked_predictions VALUES(?,?,?,?)',('p','f','2026-10-18T12:00:00+00:00',json.dumps([.6,.2,.2])))
        x=forward_metrics(self.db,T)
        self.assertEqual(x['windows']['7']['coverage'],0)
        self.assertIsNone(x['windows']['7']['brier'])
    def test_bad_target_fails(self):
        self.db.execute('INSERT INTO lab_locked_predictions VALUES(?,?,?,?)',('p','f','2026-10-18T12:00:00+00:00',json.dumps([.6,.2,.2])))
        self.db.execute('INSERT INTO lab_prediction_grades VALUES(?,?,?,?)',('p','2026-10-19T11:00:00+00:00',.51,.24))
        self.db.execute('INSERT INTO lab_verified_results VALUES(?,?)',('f',json.dumps({'status':'final','target':'provider_final_unknown','home':2,'away':0})))
        with self.assertRaises(ValueError): forward_metrics(self.db,T)
if __name__=='__main__': unittest.main()
