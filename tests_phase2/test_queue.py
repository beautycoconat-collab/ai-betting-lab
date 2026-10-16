"""Synthetic HTTP stubs: these tests make zero external requests."""
import unittest,tempfile,json,sqlite3,zlib
from pathlib import Path
from datetime import datetime,timedelta
from urllib.error import HTTPError
from engine.queue import Queue
from engine.normalization import replay
from engine.external import ingest
NOW='2026-10-14T10:00:00+00:00'
PARAMS={'league':'eng.1','season':'2023-24'}
BODY=json.dumps({'matches':[{'date':'2023-08-01','team1':'A','team2':'B','score':{'ft':[2,1]}}]}).encode()
def registry():return {'openfootball':{'status':'approved','license':'CC0-1.0','terms_url':'https://example.invalid/terms','reviewed_at':'2026-10-01','review_expires':'2026-11-13','requests_per_24h':4,'requests_per_31d':124,'min_interval_seconds':3600},'blocked':{'status':'pending','review_expires':'2026-11-13'}}
class QueueTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.q=Queue(Path(self.tmp.name)/'db.sqlite',registry())
 def tearDown(self):self.q.close();self.tmp.cleanup()
 def enqueue(self,params=PARAMS):return self.q.enqueue('openfootball','collect',params,NOW)
 def work(self,f=None,now=NOW):return self.q.work_one(f or (lambda u:(BODY,{})),lambda:now)
 def test_job_idempotency(self):self.assertEqual(self.enqueue(),self.enqueue());self.assertEqual(self.q.db.execute('select count(*) from v2_jobs').fetchone()[0],1)
 def test_live_shape_parsed_and_provenance(self):
  self.enqueue();self.assertEqual(self.work()['accepted'],1);r=self.q.db.execute('select * from v2_snapshots').fetchone();self.assertEqual(zlib.decompress(r['body']),BODY);self.assertEqual(r['observed_at'],NOW)
 def test_finished_job_not_requested_again(self):self.enqueue();self.work();self.assertIsNone(self.work());self.assertEqual(self.q.db.execute('select count(*) from requests').fetchone()[0],1)
 def test_preserves_phase1_budget(self):
  self.q.store.reserve('openfootball',self.q.registry['openfootball'],NOW);self.enqueue();result=self.work(lambda u:self.fail('must not fetch'));self.assertEqual(result['reason'],'minimum_interval')
 def test_budget_cap(self):
  with self.q.db:
   for h in (1,3,5,7):self.q.db.execute('insert into requests(source,at) values (?,?)',('openfootball',f'2026-10-14T0{h}:00:00+00:00'))
  self.enqueue();self.assertEqual(self.work(lambda u:self.fail('no request'))['reason'],'quota_exhausted')
 def test_policy_expiry(self):self.q.registry['openfootball']['review_expires']='2026-01-01';self.enqueue();self.assertEqual(self.work(lambda u:self.fail('no request'))['status'],'blocked')
 def test_unapproved_source(self):self.q.enqueue('blocked','collect',{},NOW);self.assertEqual(self.work(lambda u:self.fail('no request'))['reason'],'source_not_approved')
 def test_malformed_json_retained(self):
  self.enqueue();r=self.work(lambda u:(b'not JSON',{}));self.assertEqual(r['status'],'failed');self.assertEqual(self.q.db.execute('select count(*) from v2_snapshots').fetchone()[0],1);self.assertEqual(self.q.report()['health'][0]['failures'],1)
 def test_429_cooldown(self):
  def fetch(u):raise HTTPError(u,429,'rate limit',{'Retry-After':'172800'},None)
  self.enqueue();r=self.work(fetch);self.assertEqual(r['reason'],'http_429');self.assertEqual(self.q.db.execute('select until_at from cooldowns').fetchone()[0],'2026-10-16T10:00:00+00:00')
 def test_claim_excludes_other_worker(self):
  self.enqueue();first=self.q.claim(NOW);other=Queue(self.q.store.path,registry())
  try:self.assertIsNone(other.claim(NOW))
  finally:other.close()
  self.q.finish(first,'done')
 def test_stale_lease_cannot_finish_new_claim(self):
  self.enqueue();first=self.q.claim(NOW);second=self.q.claim('2026-10-14T10:06:00+00:00');self.assertNotEqual(first['lease_token'],second['lease_token']);self.q.finish(first,'done');self.assertEqual(self.q.report()['jobs'][0]['status'],'running')
 def test_cached_replay_no_network_or_quota_change(self):
  self.enqueue();self.work();sid=self.q.db.execute('select id from v2_snapshots').fetchone()[0];before=self.q.db.execute('select count(*) from requests').fetchone()[0];r=replay(self.q,sid);self.assertEqual(r['accepted'],1);self.assertEqual(r['network_requests'],0);self.assertEqual(self.q.db.execute('select count(*) from requests').fetchone()[0],before)
 def test_corrupt_raw_refuses_replay(self):
  self.enqueue();self.work();self.q.db.execute("update v2_snapshots set sha256='invalid'");self.q.db.commit();sid=self.q.db.execute('select id from v2_snapshots').fetchone()[0]
  with self.assertRaises(ValueError):replay(self.q,sid)
 def test_cache_ttl_preserved_for_same_url(self):
  self.enqueue();self.work();self.enqueue(dict(PARAMS,request_label='second'))
  self.assertEqual(self.work(lambda u:self.fail('cache must prevent HTTP'),now='2026-10-14T12:00:00+00:00')['status'],'cached')
 def test_expired_lease_cannot_complete(self):
  self.enqueue();j=self.q.claim(NOW);self.q.finish(j,'done',at='2026-10-14T10:06:00+00:00');self.assertEqual(self.q.report()['jobs'][0]['status'],'running')
 def test_storage_budget_stop(self):
  # Mock stat avoids writing 40 MB merely to exercise the inherited guard.
  from unittest.mock import patch,Mock
  self.enqueue()
  with patch('pathlib.Path.stat',return_value=Mock(st_size=40_000_001)):
   self.assertEqual(self.work(lambda u:self.fail('no request'))['reason'],'local_storage_budget')
 def test_daily_cycles_do_not_repeat_prior_jobs(self):
  first=self.q.enqueue('openfootball','collect',PARAMS,NOW,cycle='2026-10-14')
  self.assertEqual(first,self.q.enqueue('openfootball','collect',PARAMS,NOW,cycle='2026-10-14'))
  second=self.q.enqueue('openfootball','collect',PARAMS,'2026-10-15T10:00:00+00:00',cycle='2026-10-15')
  self.assertNotEqual(first,second)
  with self.assertRaises(ValueError):
   self.q.enqueue('openfootball','collect',PARAMS,NOW,cycle='not-a-date')
 def test_cached_reuse_links_new_job_without_cloning_snapshot(self):
  first=self.q.enqueue('openfootball','collect',PARAMS,NOW,cycle='2026-10-14')
  self.assertEqual(self.work()['status'],'done')
  second=self.q.enqueue('openfootball','collect',PARAMS,'2026-10-14T12:00:00+00:00',cycle='2026-10-15')
  r=self.work(lambda u:self.fail('cache must skip HTTP'),now='2026-10-14T12:00:00+00:00')
  self.assertEqual(r['status'],'cached')
  self.assertEqual(self.q.db.execute('SELECT count(*) FROM v2_snapshots').fetchone()[0],1)
  self.assertEqual(self.q.db.execute('SELECT count(*) FROM v2_job_snapshots').fetchone()[0],2)
  self.assertEqual(self.q.db.execute('SELECT count(*) FROM requests').fetchone()[0],1)
 def test_unreviewed_permission_blocks_fetch(self):
  self.enqueue();self.q.registry['openfootball'].pop('license')
  r=self.work(lambda u:self.fail('source has no verified license'))
  self.assertEqual((r['status'],r['reason']),('blocked','source_permission_unverified'))
  self.assertEqual(self.q.db.execute('select count(*) from requests').fetchone()[0],0)
 def test_future_review_date_blocks_fetch(self):
  self.enqueue();self.q.registry['openfootball']['reviewed_at']='2026-10-15'
  r=self.work(lambda u:self.fail('future review must block'))
  self.assertEqual(r['reason'],'source_permission_unverified')
 def test_stale_http_worker_cannot_publish(self):
  self.enqueue()
  clock={'now':NOW}
  def fetcher(url):
   clock['now']='2026-10-14T10:06:00+00:00'
   self.assertIsNotNone(self.q.claim(clock['now']))
   return BODY,{}
  r=self.q.work_one(fetcher,lambda:clock['now'])
  self.assertEqual(r['status'],'lease_lost')
  self.assertEqual(self.q.db.execute('select count(*) from v2_snapshots').fetchone()[0],0)
  self.assertEqual(self.q.db.execute('select count(*) from v2_results').fetchone()[0],0)
  self.assertEqual(self.q.db.execute('select status from v2_jobs').fetchone()[0],'running')
 def test_expired_worker_cannot_publish_even_without_reclaim(self):
  self.enqueue();ticks=iter([NOW,'2026-10-14T10:06:00+00:00'])
  r=self.q.work_one(lambda u:(BODY,{}),lambda:next(ticks))
  self.assertEqual(r['status'],'lease_lost')
  self.assertEqual(self.q.db.execute('select count(*) from v2_snapshots').fetchone()[0],0)
 def test_reclaimed_worker_during_decode_cannot_publish_normalized_results(self):
  self.enqueue()
  clock={'now':NOW}
  from unittest.mock import patch
  from engine.adapters import ADAPTERS
  original=ADAPTERS['openfootball'].decode
  def decode(*args):
   clock['now']='2026-10-14T10:06:00+00:00'
   self.assertIsNotNone(self.q.claim(clock['now']))
   return original(*args)
  with patch.object(ADAPTERS['openfootball'],'decode',side_effect=decode):
   r=self.q.work_one(lambda u:(BODY,{}),lambda:clock['now'])
  self.assertEqual(r['status'],'lease_lost')
  self.assertEqual(self.q.db.execute('select count(*) from v2_results').fetchone()[0],0)
  self.assertEqual(self.q.db.execute('select status from v2_jobs').fetchone()[0],'running')
class ExternalTests(unittest.TestCase):
 def setUp(self):self.db=sqlite3.connect(':memory:');self.reg={'x':{'status':'approved','external_predictions_allowed':True,'review_expires':'2026-11-13'}};self.payload={'match_ref':'test-1','score_selection':'1-0','kickoff_at':'2026-10-15T10:00:00+00:00','source_url':'https://example.invalid/test'}
 def tearDown(self):self.db.close()
 def call(self,p=None):return ingest(self.db,'x',p or self.payload,self.reg,lambda:NOW)
 def test_verified_prematch_still_zero_weight(self):r=self.call();self.assertTrue(r['prematch_verified']);self.assertEqual(r['ensemble_weight'],0)
 def test_backfill_not_prematch(self):self.payload['kickoff_at']='2020-01-01T00:00:00+00:00';self.assertFalse(self.call()['prematch_verified'])
 def test_unapproved_block(self):
  self.reg['x']['external_predictions_allowed']=False
  with self.assertRaises(ValueError):self.call()
 def test_future_publication_block(self):
  self.payload['published_at']='2027-01-01T00:00:00+00:00'
  with self.assertRaises(ValueError):self.call()
 def test_probability_mass_required(self):
  self.payload['score_probabilities']={'1-0':.2}
  with self.assertRaises(ValueError):self.call()
  self.payload['other_scores_probability']=.8;self.assertEqual(self.call()['ensemble_weight'],0)
 def test_retry_preserves_original_prematch_status(self):
  first=self.call();later=ingest(self.db,'x',self.payload,self.reg,lambda:'2026-10-16T10:00:00+00:00');self.assertEqual(first,later)
 def test_idempotency(self):self.assertEqual(self.call()['id'],self.call()['id']);self.assertEqual(self.db.execute('select count(*) from v2_external').fetchone()[0],1)
