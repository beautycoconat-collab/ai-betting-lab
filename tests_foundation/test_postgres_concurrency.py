"""Opt-in NATIVE PostgreSQL sessions, NOT a PGlite simulation.

Requires a NEW disposable database named ai_betting_lab_test* and psycopg 3.
No databases/schemas are dropped. Set both explicit environment gates to run.
These tests are skipped in the delivered environment; see TEST_REPORT.md.
"""
import os,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
ENABLED=bool(os.getenv('LAB_TEST_POSTGRES_DSN')) and os.getenv('LAB_TEST_POSTGRES_DISPOSABLE')=='1'

@unittest.skipUnless(ENABLED,'Native PostgreSQL DSN and disposable-database opt-in absent')
class NativePostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.connect=lambda:psycopg.connect(os.environ['LAB_TEST_POSTGRES_DSN'],autocommit=True)
        cls.db=cls.connect()
        database=cls.db.execute('select current_database()').fetchone()[0]
        if not database.startswith('ai_betting_lab_test'):raise RuntimeError('requires_disposable_database_name')
        if cls.db.execute("select 1 from pg_namespace where nspname='lab'").fetchone():raise RuntimeError('requires_empty_database_no_existing_lab_schema')
        root=Path(__file__).resolve().parents[1]
        for p in sorted((root/'supabase/migrations').glob('*.sql')):cls.db.execute(p.read_text())
        cls.db.execute("insert into lab.sources(id,status,license_url,review_expires) values('native-test','approved','https://example.invalid',now()+interval '1 day')")
        cls.raw=cls.db.execute("insert into lab.raw_snapshots(source_id,request_url,received_at,content_sha256,payload,data_kind) values('native-test','https://example.invalid',now()-interval '1 hour',repeat('a',64),'{}','real') returning id").fetchone()[0]
        cls.home=cls.db.execute("insert into lab.teams(name) values('SYNTHETIC A') returning id").fetchone()[0]
        cls.away=cls.db.execute("insert into lab.teams(name) values('SYNTHETIC B') returning id").fetchone()[0]
        cls.model=cls.db.execute("insert into lab.model_versions(name,code_sha,parameters,trained_through,role,dataset_hash) values('SYNTHETIC','test','{}',now()-interval '2 hours','champion','test') returning id").fetchone()[0]
        cls.db.execute("update lab.paper_wallet set betting_enabled=true,pilot_start=now()-interval '1 hour',pilot_end=now()-interval '1 hour'+interval '7 days'")
    @classmethod
    def tearDownClass(cls):cls.db.close()
    def fixture(self):
        m=self.db.execute("insert into lab.matches(competition,season,home_id,away_id,kickoff_at,status) values('SYNTHETIC','TEST',%s,%s,now()+interval '1 day','scheduled') returning id",(self.home,self.away)).fetchone()[0]
        p=self.db.execute("insert into lab.predictions(match_id,model_id,feature_cutoff,kickoff_at,p_home,p_draw,p_away,score_grid,input_snapshot_ids) values(%s,%s,now()-interval '30 minutes',(select kickoff_at from lab.matches where id=%s),.5,.3,.2,'{}',%s) returning id",(m,self.model,m,[self.raw])).fetchone()[0]
        o=self.db.execute("insert into lab.odds_snapshots(match_id,source_id,bookmaker,market,outcome,decimal_odds,source_updated_at,observed_at,raw_snapshot_id) values(%s,'native-test','SYNTHETIC','1X2','H',2,now(),now(),%s) returning id",(m,self.raw)).fetchone()[0]
        return m,p,o
    def test_independent_sessions_claim_once(self):
        m,_,_=self.fixture();self.db.execute('set role lab_coordinator');self.db.execute("select lab.enqueue_workflow('native-claim-once','validate',%s)",(m,));self.db.execute('reset role')
        barrier=Barrier(2)
        def worker(i):
            with type(self).connect() as db:
                db.execute('set role lab_data_validator');barrier.wait();return db.execute("select * from lab.claim_workflow('data_validator',%s)",(str(i),)).fetchall()
        with ThreadPoolExecutor(2) as ex:results=list(ex.map(worker,range(2)))
        self.assertEqual(sum(len(r) for r in results),1)
    def test_daily_cap_under_twelve_parallel_transactions(self):
        fixtures=[self.fixture() for _ in range(12)];barrier=Barrier(12)
        def worker(i):
            with type(self).connect() as db:
                barrier.wait()
                try:db.execute('select lab.place_paper_bet(%s,%s,%s,1000)',('native-stake-'+str(i),fixtures[i][1],fixtures[i][2]));return 'accepted'
                except Exception as e:
                    if 'daily_limit' not in str(e):raise
                    return 'limited'
        with ThreadPoolExecutor(12) as ex:results=list(ex.map(worker,range(12)))
        self.assertEqual(results.count('accepted'),10);self.assertEqual(results.count('limited'),2)
        self.assertEqual(self.db.execute('select sum(stake_kurus) from lab.paper_bets').fetchone()[0],10000)
        self.assertEqual(self.db.execute('select balance_kurus from lab.paper_wallet').fetchone()[0],90000)
