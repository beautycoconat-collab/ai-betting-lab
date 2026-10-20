import json
import sqlite3
import unittest
from datetime import datetime,timezone
from pathlib import Path
from dashboard.daily import fixtures,analyze,fit_models
from dashboard.supabase_store import plan,connect_and_persist
from api.dashboard import query

class DailyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.now=datetime(2026,10,19,17,tzinfo=timezone.utc)
        cls.engine,cls.synth=fit_models(cls.now)

    def fixture(self):
        return dict(id='00000000-0000-0000-0000-000000000011',home='FC Bayern München',away='VfB Stuttgart',
            competition='bl1',season='2026',kickoff_at='2026-10-23T18:30:00+00:00',target='regulation90',
            neutral=None,source_id='openliga',snapshot_id='fixture-evidence',snapshot_sha256='0'*64,
            observed_at='2026-10-19T16:00:00+00:00',source_url='https://api.openligadb.de/getmatchdata/bl1/2026',mode='verified_fixture')

    def test_training_observed_before_prediction(self):
        self.assertEqual(self.engine.mode,'prematch')
        self.assertLessEqual(self.synth.validation_observed_end,self.now)
        self.assertGreater(sum(m.n_train for m in self.engine.models.values()),1000)

    def test_unknown_venue_produces_two_unweighted_scenarios(self):
        result=analyze(self.fixture(),self.engine,self.synth,self.now)
        self.assertEqual(result['prediction_status'],'conditional_scenarios')
        self.assertEqual([s['neutral'] for s in result['scenarios']],[False,True])
        self.assertEqual(result['models'] if 'models' in result else {},{})
        for s in result['scenarios']:
            self.assertAlmostEqual(sum(s['models']['ensemble']['p_1x2']),1)
            self.assertEqual(s['reviews'][-1]['status'],'abstain')
        self.assertFalse(result['execution_enabled'])

    def test_unknown_team_not_invented(self):
        result=analyze(self.fixture()|{'home':'UNKNOWN TEAM'},self.engine,self.synth,self.now)
        self.assertEqual(result['prediction_status'],'insufficient_data')
        self.assertNotIn('scenarios',result)

    def test_unvalidated_league_rejected(self):
        self.assertEqual(analyze(self.fixture()|{'competition':'other'},self.engine,self.synth,self.now)['prediction_status'],'insufficient_data')

    def test_api_lists_real_fixture_and_keeps_research_separate(self):
        f=self.fixture();data=dict(schema_version='1.0',execution_enabled=False,fixtures=[f],history=[],research={'records':[]})
        r=query(data,{'date':['2026-10-23']},now=self.now)[1]
        self.assertEqual(len(r['fixtures']),1)
        self.assertIn('2026-10-23',r['available_dates'])

    def test_cloud_wrong_project_rejected_before_connection(self):
        with self.assertRaises(ValueError):connect_and_persist({},env={'LAB_TEST_PROJECT_REF':'another-project'})

    def test_no_sql_for_unsafe_execution(self):
        with self.assertRaises(ValueError):plan({'execution_enabled':True,'pilot_enabled':False})

    def test_stale_source_not_listed_as_current(self):
        f=self.fixture()|{'observed_at':'2026-10-17T16:00:00+00:00'}
        data=dict(schema_version='1.0',execution_enabled=False,fixtures=[f],history=[])
        self.assertEqual(query(data,{'date':['2026-10-23']},now=self.now)[1]['fixtures'],[])
