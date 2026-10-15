-- Only synthetic test records. Does not enable pilot, debit wallet or place a wager.
DO $$ DECLARE a uuid;b uuid;m uuid;s uuid;f uuid;p uuid;o uuid;i integer; BEGIN
 IF EXISTS(SELECT 1 FROM lab.paper_bets) THEN RAISE EXCEPTION 'requires_empty_test_bets'; END IF;
 INSERT INTO lab.sources(id,status,license_url) VALUES('hosted-synthetic-test','pending','https://example.invalid');
 INSERT INTO lab.raw_snapshots(source_id,request_url,content_sha256,payload,data_kind) VALUES('hosted-synthetic-test','https://example.invalid',repeat('a',64),'{}','synthetic') RETURNING id INTO s;
 INSERT INTO lab.teams(name) VALUES('SYNTHETIC hosted A') RETURNING id INTO a;
 INSERT INTO lab.teams(name) VALUES('SYNTHETIC hosted B') RETURNING id INTO b;
 INSERT INTO lab.model_versions(name,code_sha,parameters,trained_through,role,dataset_hash) VALUES('SYNTHETIC test model','test','{}',now()-interval '2 days','candidate','test') RETURNING id INTO m;
 FOR i IN 0..11 LOOP
  INSERT INTO lab.matches(competition,season,home_id,away_id,kickoff_at,status) VALUES('SYNTHETIC TEST',i::text,a,b,now()+interval '1 day','scheduled') RETURNING id INTO f;
  INSERT INTO lab.predictions(match_id,model_id,feature_cutoff,kickoff_at,p_home,p_draw,p_away,score_grid,input_snapshot_ids) VALUES(f,m,now()-interval '1 hour',now()+interval '1 day',.5,.3,.2,'{}',ARRAY[s]) RETURNING id INTO p;
  INSERT INTO lab.odds_snapshots(match_id,source_id,bookmaker,market,outcome,decimal_odds,source_updated_at,raw_snapshot_id) VALUES(f,'hosted-synthetic-test','SYNTHETIC','1X2','H',2,now(),s) RETURNING id INTO o;
 END LOOP;
END $$;
SET ROLE lab_coordinator;
SELECT lab.enqueue_workflow('hosted-native-claim-20261015','validate',NULL);
RESET ROLE;
