"""Synthetic evidence integration only; numerical models use real archived rows."""
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from pydantic import ValidationError
from dashboard.contracts import ModelSummary
from dashboard.research_feed import read_research
from dashboard.export import build
from api.dashboard import query
from tests_experts import test_worker_pipeline as harness

class ResearchFeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        harness.WorkerPipelineTests.setUpClass()
        cls.engine=harness.WorkerPipelineTests.engine
        cls.synth=harness.WorkerPipelineTests.synth
        cls.row=harness.WorkerPipelineTests.row

    def setUp(self): harness.WorkerPipelineTests.setUp(self)
    def tearDown(self): harness.WorkerPipelineTests.tearDown(self)
    def run_chain(self):
        tasks=harness.WorkerPipelineTests.schedule(self)
        harness.WorkerPipelineTests.drive_tasks(self,tasks)
        return tasks
    def feed(self): return read_research(self.runtime.db,datetime.fromisoformat(self.clock))

    def test_actual_worker_chain_projects_without_promoting_to_live(self):
        self.run_chain(); feed=self.feed()
        self.assertEqual(len(feed['records']),1)
        f=feed['records'][0]
        self.assertEqual(f['mode'],'recorded_research')
        self.assertEqual(f['evidence_status'],'local_record_unverified')
        self.assertEqual(len(f['models']),5)
        self.assertEqual(len(f['roles']),4)
        self.assertEqual(f['market_model'],'ensemble')
        self.assertFalse(f['execution_enabled'])
        self.assertEqual(f['markets']['half1']['status'],'insufficient_data')
        self.assertTrue(f['reviews'])
        self.assertAlmostEqual(sum(f['models']['ensemble']['p_1x2']),1)
        self.assertTrue(self.runtime.verify_audit())

    def test_opt_in_readonly_and_api_lookup(self):
        self.run_chain()
        path=Path(self.tmp.name)/'research.db'
        before=path.read_bytes()
        a=build(root=Path(self.tmp.name),database=path)
        self.assertEqual(a['research']['status'],'not_requested')
        b=build(root=Path(self.tmp.name),database=path,include_research=True,
                now=datetime.fromisoformat(self.clock))
        record=b['research']['records'][0]
        self.assertEqual(query(b,{'fixture':[record['id']]})[0],200)
        self.assertEqual(query(b,{'date':[self.row['date']]})[1]['fixtures'],[])
        self.assertEqual(before,path.read_bytes())

    def test_incomplete_chain_stays_missing(self):
        tasks=harness.WorkerPipelineTests.schedule(self)
        self.pipeline.dispatcher.work_one('worker','data_validator')
        self.assertEqual(self.feed()['records'],[])

    def test_raw_inputs_never_published(self):
        self.claim['value']='PRIVATE_UNPUBLISHED_NEWS'
        self.run_chain()
        text=json.dumps(self.feed())
        self.assertNotIn('PRIVATE_UNPUBLISHED_NEWS',text)
        self.assertNotIn('example.invalid',text)
        self.assertNotIn('synthetic lineup only',text)

    def test_future_cutoff_rejected_without_exception_text(self):
        self.run_chain()
        f=read_research(self.runtime.db,datetime(2020,1,1,tzinfo=timezone.utc))
        self.assertEqual(f['records'],[]);self.assertEqual(f['rejected_records'],1)

    def test_malformed_probability_output_is_quarantined(self):
        old=self.pipeline.dispatcher.handlers['model']
        def broken(job,deps):
            value=old(job,deps)
            value.data['models']['poisson']['p_1x2']=[.9,.9,.9]
            return value
        self.pipeline.dispatcher.handlers['model']=broken
        self.run_chain()
        self.assertEqual(self.feed()['rejected_records'],1)
        self.assertEqual(self.feed()['records'],[])

    def test_old_output_has_no_invented_score_distribution(self):
        old=self.pipeline.dispatcher.handlers['model']
        def legacy(job,deps):
            value=old(job,deps)
            for k in ('models','markets','market_model','display_schema_version'):
                value.data.pop(k,None)
            return value
        self.pipeline.dispatcher.handlers['model']=legacy
        self.run_chain()
        record=self.feed()['records'][0]
        self.assertEqual(record['models'],{})
        self.assertEqual(record['markets'],{})
        self.assertEqual(len(record['roles']),4)

    def test_contract_rejects_unknown_version_nonfinite_and_duplicate_scores(self):
        self.run_chain(); m=self.feed()['records'][0]['models']['poisson']
        for changed in (m|{'schema_version':'2.0'},m|{'p_1x2':[float('nan'),.2,.3]},
                m|{'top_scores':[m['top_scores'][0],m['top_scores'][0]]}):
            with self.assertRaises(ValidationError):ModelSummary.model_validate(changed)

    def test_retry_does_not_duplicate_research_record(self):
        self.run_chain();self.run_chain()
        self.assertEqual(len(self.feed()['records']),1)
