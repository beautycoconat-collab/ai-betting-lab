import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from dashboard.export import build
from api.dashboard import query

ROOT = Path(__file__).resolve().parents[1]

class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build(now=datetime(2026,10,16,tzinfo=timezone.utc))

    def test_real_archive_not_live(self):
        self.assertEqual(len(self.data['history']),18)
        self.assertTrue(all(f['mode']=='retrospective' for f in self.data['history']))
        self.assertEqual(query(self.data,{'date':['2026-10-16']})[1]['fixtures'],[])

    def test_models_preserved_and_mass_conserved(self):
        for f in self.data['history']:
            self.assertEqual(set(f['models']),{'elo','poisson','dixon_coles','baseline'})
            for m in f['models'].values():
                self.assertAlmostEqual(sum(m['p_1x2']),1)
                self.assertLess(m['training_end'],f['date'])
                self.assertGreaterEqual(m['outside_grid_probability'],0)

    def test_no_claimed_reviews_or_wallet(self):
        self.assertIsNone(self.data['portfolio']['balance'])
        self.assertFalse(self.data['pilot_enabled'])
        self.assertFalse(self.data['execution_enabled'])
        self.assertEqual(len(self.data['roles']),14)
        self.assertTrue(all(not f['reviews'] for f in self.data['history']))

    def test_markets_and_unsupported_half(self):
        m=self.data['history'][0]['markets']
        self.assertEqual(m['half1']['status'],'insufficient_data')
        self.assertAlmostEqual(m['over_2.5']['win']+m['under_2.5']['win'],1)
        self.assertIn('home_over_1.5',m)

    def test_lookup_and_missing_fixture(self):
        f=self.data['history'][0]
        self.assertEqual(query(self.data,{'fixture':[f['id']]})[1],f)
        self.assertEqual(query(self.data,{'fixture':['not-found']})[0],404)

    def test_bad_date_and_schema_rejected(self):
        with self.assertRaises(ValueError): query(self.data,{'date':['no-date']})
        with self.assertRaises(ValueError): query(self.data|{'execution_enabled':True},{})
        with self.assertRaises(ValueError): build(now=datetime(2026,10,16))

    def test_unverified_runtime_fixtures_never_daily(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'runtime.sqlite'; db=sqlite3.connect(p)
            db.execute('CREATE TABLE f_fixtures(id,home,away,kickoff_at,target)')
            db.execute('INSERT INTO f_fixtures VALUES(?,?,?,?,?)',('f','A','B','2026-10-16T18:00:00+00:00','regulation90'))
            db.execute('CREATE TABLE private_secrets(value)');db.execute("INSERT INTO private_secrets VALUES('never-publish-this')")
            db.commit();db.close()
            data=build(root=Path(d),database=p)
            self.assertEqual(len(data['fixtures']),1)
            self.assertEqual(query(data,{'date':['2026-10-16']})[1]['fixtures'],[])
            self.assertNotIn('never-publish-this',json.dumps(data))
            db=sqlite3.connect(p);self.assertEqual(db.execute('SELECT count(*) FROM f_fixtures').fetchone()[0],1);db.close()

    def test_missing_database_not_created(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'absent.sqlite'
            with self.assertRaises(sqlite3.OperationalError):build(root=Path(d),database=p)
            self.assertFalse(p.exists())

    def test_reproducible_publication(self):
        self.assertEqual(self.data,build(now=datetime(2026,10,16,tzinfo=timezone.utc)))

    def test_public_bundle_no_runtime_secrets(self):
        raw=json.dumps(self.data)
        for forbidden in ('service_role','postgresql://','password','numeric_override'):
            self.assertNotIn(forbidden,raw)
        self.assertTrue(all(len(p['sha256'])==64 for p in self.data['provenance']))
