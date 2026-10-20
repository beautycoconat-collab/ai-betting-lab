import copy
import json
import unittest
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from dashboard.hosted import reconcile
from dashboard.supabase_store import plan,persist

class Result:
    def __init__(self,rows):self.rows=rows
    def fetchall(self):return self.rows
    def fetchone(self):return self.rows[0] if self.rows else None
class Connection:
    def __init__(self,f,scenarios):self.f=f;self.scenarios=scenarios;self.statements=[]
    def transaction(self):return nullcontext()
    def execute(self,query,params=None):
        self.statements.append(query)
        if query.startswith('SELECT m.id'):return Result([(self.f['id'],self.f['home'],self.f['away'],datetime.fromisoformat(self.f['kickoff_at']),self.f['snapshot_sha256'],datetime.fromisoformat(self.f['observed_at']))])
        if query.startswith('SELECT payload'):return Result([(s,) for s in self.scenarios])
        return Result([])

class HostedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed=json.loads((Path(__file__).resolve().parents[1]/'public/data/dashboard.json').read_text())
        cls.fixture=next(f for f in cls.seed['fixtures'] if f.get('scenarios'))

    def payloads(self):return [s|{'schema_version':'1.0','execution_enabled':False} for s in self.fixture['scenarios']]
    def test_real_public_artifact_reconciles_with_matching_cloud_rows(self):
        c=Connection(self.fixture,self.payloads());result=reconcile(c,self.seed)
        self.assertEqual(len(result['fixtures'][0]['scenarios']),2)
        self.assertIn('SET TRANSACTION READ ONLY',c.statements)
        self.assertFalse(any('wallet' in s for s in c.statements))
    def test_mismatched_cloud_identity_not_published(self):
        f=self.fixture|{'home':'wrong team'}
        self.assertEqual(reconcile(Connection(f,[]),self.seed)['fixtures'],[])
    def test_missing_cloud_prediction_not_replaced_with_fake(self):
        result=reconcile(Connection(self.fixture,[]),self.seed)
        self.assertEqual(result['fixtures'][0]['prediction_status'],'insufficient_data')
        self.assertEqual(result['fixtures'][0]['scenarios'],[])
    def test_store_plan_uses_only_existing_allowlisted_tables(self):
        sql=plan(self.seed)
        self.assertTrue(sql)
        self.assertFalse(any(any(x in q.upper() for x in ('DELETE','ALTER ','DROP ','GRANT ','TRUNCATE','UPDATE ')) for q,v in sql))
        self.assertTrue(all(q.count('%s')==len(v) for q,v in sql))
        self.assertFalse(any('wallet' in q for q,v in sql))
