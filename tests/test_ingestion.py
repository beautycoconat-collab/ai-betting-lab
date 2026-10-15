import copy
import json
import tempfile
import unittest
import urllib.error
from datetime import datetime,timedelta,timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from betting_lab.adapters import ADAPTERS
from betting_lab.collector import collect
from betting_lab.domain import aware
from betting_lab.identity import reconcile
from betting_lab.store import Store,StopCollection

# SYNTHETIC fixtures only. These fictional teams never enter real-data deliverables.
NOW='2026-10-14T12:00:00+00:00'
POLICY={'status':'approved','review_expires':'2026-11-13','requests_per_24h':4,'requests_per_31d':124,'min_interval_seconds':3600,'cache_seconds':21600}
ROW={'matchID':1,'leagueShortcut':'bl1','leagueSeason':2024,'team1':{'teamId':1,'teamName':'TEST Alpha'},'team2':{'teamId':2,'teamName':'TEST Beta'},'matchDateTimeUTC':'2024-08-23T18:30:00Z','lastUpdateDateTime':'2024-08-24T12:00:00','matchIsFinished':True,'matchResults':[{'resultTypeID':1,'pointsTeam1':0,'pointsTeam2':0},{'resultTypeID':2,'pointsTeam1':2,'pointsTeam2':1}]}
OF={'round':'Test 1','date':'2024-08-23','time':'20:30','team1':'TEST Alpha','team2':'TEST Beta','score':{'ft':[2,1]}}

class AdapterTests(unittest.TestCase):
 def test_openliga_fulltime_not_halftime(self):
  m=ADAPTERS['openliga'].parse(ROW,2024); self.assertEqual((m.home_goals,m.away_goals),(2,1))
 def test_openliga_unknown_timezone_preserved(self):
  m=ADAPTERS['openliga'].parse(ROW,2024); self.assertIsNone(m.source_updated_at); self.assertIsNotNone(m.source_updated_raw)
 def test_openliga_no_partial_live_score(self):
  r=copy.deepcopy(ROW);r['matchIsFinished']=False
  m=ADAPTERS['openliga'].parse(r,2024);self.assertIsNone(m.home_goals);self.assertEqual(m.status,'unknown')
 def test_openliga_missing_fulltime(self):
  r=copy.deepcopy(ROW);r['matchResults']=[]
  with self.assertRaises(ValueError):ADAPTERS['openliga'].parse(r,2024)
 def test_openliga_wrong_season(self):
  with self.assertRaises(ValueError):ADAPTERS['openliga'].parse(ROW,2025)
 def test_openliga_negative_goals(self):
  r=copy.deepcopy(ROW);r['matchResults'][1]['pointsTeam1']=-1
  with self.assertRaises(ValueError):ADAPTERS['openliga'].parse(r,2024)
 def test_openliga_timezone_required(self):
  r=copy.deepcopy(ROW);r['matchDateTimeUTC']='2024-08-23T18:30:00'
  with self.assertRaises(ValueError):ADAPTERS['openliga'].parse(r,2024)
 def test_openfootball_score(self):
  self.assertEqual(ADAPTERS['openfootball'].parse(OF,2024).home_goals,2)
 def test_openfootball_no_invented_kickoff(self):
  self.assertIsNone(ADAPTERS['openfootball'].parse(OF,2024).kickoff_at)
 def test_openfootball_missing_score(self):
  r=copy.deepcopy(OF);r.pop('score');self.assertIsNone(ADAPTERS['openfootball'].parse(r,2024).home_goals)
 def test_openfootball_boolean_score_rejected(self):
  r=copy.deepcopy(OF);r['score']['ft']=[True,1]
  with self.assertRaises(ValueError):ADAPTERS['openfootball'].parse(r,2024)
 def test_openfootball_identity_survives_reschedule(self):
  r=copy.deepcopy(OF);r['date']='2024-08-24'
  self.assertEqual(ADAPTERS['openfootball'].parse(r,2024).source_match_id,ADAPTERS['openfootball'].parse(OF,2024).source_match_id)
 def test_openfootball_same_team_rejected(self):
  r=copy.deepcopy(OF);r['team2']=r['team1']
  with self.assertRaises(ValueError):ADAPTERS['openfootball'].parse(r,2024)
 def test_both_reject_wrong_envelope(self):
  for source,adapter in ADAPTERS.items():
   with self.subTest(source=source),self.assertRaises(ValueError):adapter.rows('html')

class CollectorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite';self.store=Store(self.path)
 def tearDown(self):self.store.close();self.tmp.cleanup()
 def collect(self,rows=None,**kw):
  return collect(self.store,'openliga',kw.get('policy',POLICY),2024,kw.get('fetcher',lambda u:(json.dumps([ROW] if rows is None else rows).encode(),{})),kw.get('clock',lambda:NOW))
 def test_collect_and_export(self):
  self.assertEqual(self.collect()['accepted'],1);self.assertEqual(len(self.store.latest()),1)
 def test_retry_is_cached(self):
  self.collect();r=self.collect(fetcher=lambda u:self.fail('must not call network'));self.assertEqual(r['reason'],'cached')
 def test_partial_row_quarantine(self):
  r=self.collect([ROW,{}]);self.assertEqual((r['accepted'],r['rejected'],r['status']),(1,1,'partial'))
 def test_duplicate_row_quarantine(self):
  self.assertEqual(self.collect([ROW,ROW])['rejected'],1)
 def test_disabled_does_not_fetch(self):
  r=self.collect(policy=dict(POLICY,status='blocked'),fetcher=lambda u:self.fail());self.assertEqual(r['reason'],'source_not_approved')
 def test_expired_review_stops(self):
  r=self.collect(policy=dict(POLICY,review_expires='2026-10-01'));self.assertEqual(r['reason'],'source_review_expired')
 def test_quota_counts_failed_attempt(self):
  def fail(u):raise TimeoutError()
  self.assertEqual(self.collect(fetcher=fail)['status'],'error')
  r=self.collect(policy=dict(POLICY,requests_per_24h=1));self.assertEqual(r['reason'],'quota_exhausted')
 def test_http_429_circuit_breaker(self):
  def fail(u):raise urllib.error.HTTPError(u,429,'limit',{'Retry-After':'172800'},None)
  self.collect(fetcher=fail)
  self.assertEqual(self.collect()['reason'],'cooldown')
 def test_bad_json(self):
  self.assertEqual(self.collect(fetcher=lambda u:(b'<html>',{}))['status'],'error')
 def test_empty_data_not_success(self):self.assertEqual(self.collect([])['status'],'invalid')
 def test_new_receipt_appends_same_raw_hash_once(self):
  self.collect();later='2026-10-15T12:00:00+00:00';self.collect(clock=lambda:later)
  self.assertEqual(self.store.db.execute('select count(*) from snapshots').fetchone()[0],2)
  self.assertEqual(self.store.db.execute('select count(*) from blobs').fetchone()[0],1)
  self.assertEqual(len(self.store.latest()),1)
 def test_timestamp_after_receipt(self):
  times=iter([NOW,'2026-10-14T12:00:02+00:00']);self.collect(clock=lambda:next(times))
  self.assertEqual(self.store.latest()[0]['observed_at'],'2026-10-14T12:00:02+00:00')
 def test_raw_hash_reproducible(self):
  import zlib,hashlib
  self.collect();r=self.store.db.execute('select * from blobs').fetchone()
  self.assertEqual(hashlib.sha256(zlib.decompress(r['body'])).hexdigest(),r['hash'])
 def test_parallel_reservations_cannot_exceed_limit(self):
  def worker(_):
   s=Store(self.path)
   try:
    s.reserve('openliga',dict(POLICY,requests_per_24h=1,min_interval_seconds=0),NOW);return True
   except StopCollection:return False
   finally:s.close()
  with ThreadPoolExecutor(max_workers=6) as ex:self.assertEqual(sum(ex.map(worker,range(6))),1)
 def test_storage_budget_stops(self):
  self.store.db.execute('CREATE TABLE padding(x BLOB)');self.store.db.execute('INSERT INTO padding VALUES (zeroblob(40000001))');self.store.db.commit()
  self.assertEqual(self.collect()['reason'],'local_storage_budget')

class IdentityTests(unittest.TestCase):
 def rows(self):return [ADAPTERS['openliga'].parse(ROW,2024).to_dict(),ADAPTERS['openfootball'].parse(OF,2024).to_dict()]
 def aliases(self):return {'openliga:DE-BL1:1':'a','openliga:DE-BL1:2':'b','openfootball:DE-BL1:TEST Alpha':'a','openfootball:DE-BL1:TEST Beta':'b'}
 def test_no_guessing(self):self.assertEqual(len(reconcile(self.rows(),{})['unresolved']),2)
 def test_explicit_candidate_requires_review(self):
  c=reconcile(self.rows(),self.aliases())['candidates'][0];self.assertEqual(c['status'],'candidate');self.assertTrue(c['requires_review'])
 def test_conflicting_scores_block(self):
  rows=self.rows();rows[1]['home_goals']=3;self.assertEqual(reconcile(rows,self.aliases())['candidates'][0]['status'],'conflict')
 def test_home_away_not_swapped(self):
  rows=self.rows();rows[1]['home_key'],rows[1]['away_key']=rows[1]['away_key'],rows[1]['home_key']
  self.assertEqual(len(reconcile(rows,self.aliases())['candidates']),2)

if __name__=='__main__':unittest.main()
