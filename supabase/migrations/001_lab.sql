-- Phase 1 schema, isolated from existing public application tables.
-- Do not expose lab through Supabase Data API. No browser write grants.
BEGIN;
CREATE SCHEMA lab;
REVOKE ALL ON SCHEMA lab FROM PUBLIC;
CREATE TABLE lab.sources (
 id text PRIMARY KEY, status text NOT NULL CHECK(status IN ('approved','blocked','pending')),
 license_url text NOT NULL, reviewed_at timestamptz, review_expires timestamptz,
 request_policy jsonb NOT NULL DEFAULT '{}', attribution text
);
CREATE TABLE lab.raw_snapshots (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_id text NOT NULL REFERENCES lab.sources,
 request_url text NOT NULL, received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 source_updated_at timestamptz, content_sha256 text NOT NULL CHECK(length(content_sha256)=64),
 payload jsonb NOT NULL, data_kind text NOT NULL CHECK(data_kind IN ('real','synthetic')),
 UNIQUE(source_id,request_url,received_at,content_sha256)
);
CREATE TABLE lab.ingestion_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_id text REFERENCES lab.sources,
 started_at timestamptz NOT NULL DEFAULT clock_timestamp(), finished_at timestamptz,
 status text NOT NULL, accepted integer NOT NULL DEFAULT 0, rejected integer NOT NULL DEFAULT 0, reason text
);
CREATE TABLE lab.source_observations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), snapshot_id uuid NOT NULL REFERENCES lab.raw_snapshots,
 source_match_id text NOT NULL, observed_at timestamptz NOT NULL, payload jsonb NOT NULL,
 UNIQUE(snapshot_id,source_match_id)
);
CREATE TABLE lab.quarantine (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), snapshot_id uuid NOT NULL REFERENCES lab.raw_snapshots,
 row_index integer NOT NULL, reason text NOT NULL, resolved_at timestamptz, UNIQUE(snapshot_id,row_index)
);
CREATE TABLE lab.teams (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL, country text, gender text, squad_type text);
CREATE TABLE lab.team_aliases (
 source_id text REFERENCES lab.sources, source_team_id text, competition text,
 team_id uuid NOT NULL REFERENCES lab.teams, reviewed_at timestamptz NOT NULL, evidence text NOT NULL,
 PRIMARY KEY(source_id,source_team_id,competition)
);
CREATE TABLE lab.matches (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), competition text NOT NULL, season text NOT NULL,
 home_id uuid NOT NULL REFERENCES lab.teams, away_id uuid NOT NULL REFERENCES lab.teams,
 kickoff_at timestamptz, status text NOT NULL CHECK(status IN ('scheduled','live','finished','postponed','cancelled','unknown')),
 CHECK(home_id<>away_id)
);
CREATE TABLE lab.match_aliases (
 source_id text REFERENCES lab.sources, source_match_id text, match_id uuid NOT NULL REFERENCES lab.matches,
 reviewed_at timestamptz NOT NULL, evidence text NOT NULL, PRIMARY KEY(source_id,source_match_id)
);
CREATE TABLE lab.match_versions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), match_id uuid NOT NULL REFERENCES lab.matches,
 observed_at timestamptz NOT NULL DEFAULT clock_timestamp(), snapshot_id uuid REFERENCES lab.raw_snapshots,
 kickoff_at timestamptz, status text NOT NULL, home_goals smallint CHECK(home_goals>=0), away_goals smallint CHECK(away_goals>=0)
);
CREATE TABLE lab.model_versions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL, code_sha text NOT NULL,
 parameters jsonb NOT NULL, trained_through timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 role text NOT NULL CHECK(role IN ('candidate','challenger','champion','retired')),
 metrics jsonb NOT NULL DEFAULT '{}', dataset_hash text NOT NULL
);
CREATE UNIQUE INDEX one_champion ON lab.model_versions ((role)) WHERE role='champion';
CREATE TABLE lab.predictions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), match_id uuid NOT NULL REFERENCES lab.matches,
 model_id uuid NOT NULL REFERENCES lab.model_versions, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 feature_cutoff timestamptz NOT NULL, kickoff_at timestamptz NOT NULL,
 p_home numeric NOT NULL CHECK(p_home BETWEEN 0 AND 1), p_draw numeric NOT NULL CHECK(p_draw BETWEEN 0 AND 1),
 p_away numeric NOT NULL CHECK(p_away BETWEEN 0 AND 1), score_grid jsonb NOT NULL,
 input_snapshot_ids uuid[] NOT NULL, CHECK(abs(p_home+p_draw+p_away-1)<0.000001),
 CHECK(feature_cutoff<=created_at AND created_at<kickoff_at)
);
CREATE TABLE lab.odds_snapshots (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), match_id uuid NOT NULL REFERENCES lab.matches,
 source_id text NOT NULL REFERENCES lab.sources, bookmaker text NOT NULL,
 market text NOT NULL CHECK(market='1X2'), outcome text NOT NULL CHECK(outcome IN ('H','D','A')),
 decimal_odds numeric(10,4) NOT NULL CHECK(decimal_odds>1 AND decimal_odds<10000),
 source_updated_at timestamptz NOT NULL, observed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 raw_snapshot_id uuid NOT NULL REFERENCES lab.raw_snapshots, CHECK(source_updated_at<=observed_at)
);
CREATE TABLE lab.external_predictions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_id text NOT NULL REFERENCES lab.sources,
 match_id uuid NOT NULL REFERENCES lab.matches, observed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 published_at timestamptz, probabilities jsonb, selection text, raw_snapshot_id uuid NOT NULL REFERENCES lab.raw_snapshots,
 upstream_cluster text, CHECK(probabilities IS NOT NULL OR selection IS NOT NULL)
);
CREATE TABLE lab.evaluation_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), model_id uuid REFERENCES lab.model_versions,
 source_id text REFERENCES lab.sources, split_manifest jsonb NOT NULL, metrics jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), CHECK(num_nonnulls(model_id,source_id)=1)
);
CREATE TABLE lab.quota_usage (
 source_id text REFERENCES lab.sources, window_start timestamptz, window_end timestamptz NOT NULL,
 used integer NOT NULL DEFAULT 0 CHECK(used>=0), ceiling integer NOT NULL CHECK(ceiling>=0),
 PRIMARY KEY(source_id,window_start), CHECK(used<=ceiling AND window_end>window_start)
);
CREATE TABLE lab.paper_wallet (
 id smallint PRIMARY KEY CHECK(id=1), balance_kurus bigint NOT NULL CHECK(balance_kurus>=0),
 betting_enabled boolean NOT NULL DEFAULT false, pilot_start timestamptz, pilot_end timestamptz,
 CHECK((pilot_start IS NULL AND pilot_end IS NULL) OR (pilot_start IS NOT NULL AND pilot_end=pilot_start+interval '7 days'))
);
INSERT INTO lab.paper_wallet(id,balance_kurus) VALUES(1,100000);
CREATE TABLE lab.paper_bets (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), idempotency_key text NOT NULL UNIQUE,
 prediction_id uuid NOT NULL REFERENCES lab.predictions, odds_id uuid NOT NULL REFERENCES lab.odds_snapshots,
 match_id uuid NOT NULL REFERENCES lab.matches, stake_kurus integer NOT NULL CHECK(stake_kurus>0 AND stake_kurus<=1000),
 locked_odds numeric(10,4) NOT NULL CHECK(locked_odds>1), outcome text NOT NULL CHECK(outcome IN ('H','D','A')),
 placed_at timestamptz NOT NULL DEFAULT clock_timestamp(), budget_day date NOT NULL,
 status text NOT NULL DEFAULT 'open' CHECK(status IN ('open','won','lost','void')),
 UNIQUE(match_id)
);
CREATE TABLE lab.wallet_ledger (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, bet_id uuid REFERENCES lab.paper_bets,
 event_key text NOT NULL UNIQUE, kind text NOT NULL CHECK(kind IN ('opening','stake','settlement','correction')),
 amount_kurus bigint NOT NULL, balance_after_kurus bigint NOT NULL CHECK(balance_after_kurus>=0),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), evidence jsonb NOT NULL DEFAULT '{}'
);
INSERT INTO lab.wallet_ledger(event_key,kind,amount_kurus,balance_after_kurus) VALUES('opening-v1','opening',100000,100000);
CREATE TABLE lab.settlements (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), bet_id uuid NOT NULL UNIQUE REFERENCES lab.paper_bets,
 result_snapshot_id uuid NOT NULL REFERENCES lab.raw_snapshots, settled_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 payout_kurus bigint NOT NULL CHECK(payout_kurus>=0), rule_version text NOT NULL
);

CREATE FUNCTION lab.reject_mutation() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'append_only_table'; END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['raw_snapshots','source_observations','match_versions','predictions','odds_snapshots','external_predictions','wallet_ledger','settlements'] LOOP
  EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON lab.%I FOR EACH ROW EXECUTE FUNCTION lab.reject_mutation()',t);
 END LOOP;
END $$;

-- Atomic paper stake reservation. Disabled until pilot acceptance gates pass.
-- This RPC does not infer results, produce predictions or contact bookmakers.
CREATE FUNCTION lab.place_paper_bet(p_key text,p_prediction uuid,p_odds uuid,p_stake integer)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE w lab.paper_wallet%ROWTYPE; old lab.paper_bets%ROWTYPE;
 p lab.predictions%ROWTYPE; o lab.odds_snapshots%ROWTYPE; m lab.matches%ROWTYPE;
 n timestamptz; d date; spent bigint; exposure bigint; bid uuid;
BEGIN
 SELECT * INTO STRICT w FROM lab.paper_wallet WHERE id=1 FOR UPDATE;
 -- Retry key is validated against the original payload, even after the pilot closes.
 SELECT * INTO old FROM lab.paper_bets WHERE idempotency_key=p_key;
 IF FOUND THEN
  IF old.prediction_id IS DISTINCT FROM p_prediction OR old.odds_id IS DISTINCT FROM p_odds OR old.stake_kurus IS DISTINCT FROM p_stake THEN
   RAISE EXCEPTION 'idempotency_conflict';
  END IF;
  RETURN old.id;
 END IF;
 n:=clock_timestamp(); d:=(n AT TIME ZONE 'Europe/Istanbul')::date;
 IF p_key IS NULL OR length(p_key)<8 OR p_stake IS NULL OR p_stake<=0 OR p_stake>1000 THEN RAISE EXCEPTION 'invalid_stake_request'; END IF;
 IF NOT w.betting_enabled OR w.pilot_start IS NULL OR n<w.pilot_start OR n>=w.pilot_end THEN RAISE EXCEPTION 'pilot_disabled'; END IF;
 SELECT * INTO STRICT p FROM lab.predictions WHERE id=p_prediction;
 SELECT * INTO STRICT o FROM lab.odds_snapshots WHERE id=p_odds;
 SELECT * INTO STRICT m FROM lab.matches WHERE id=p.match_id FOR UPDATE;
 IF m.id<>o.match_id OR m.status<>'scheduled' OR m.kickoff_at IS NULL OR
    m.kickoff_at<=n+interval '5 minutes' OR p.kickoff_at IS DISTINCT FROM m.kickoff_at OR
    p.created_at>n OR p.feature_cutoff>p.created_at OR o.observed_at>n OR
    o.observed_at<n-interval '15 minutes' OR o.source_updated_at<n-interval '15 minutes' THEN
   RAISE EXCEPTION 'ineligible_or_stale_inputs';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM lab.model_versions WHERE id=p.model_id AND role='champion' AND trained_through<=p.feature_cutoff) THEN RAISE EXCEPTION 'no_eligible_champion'; END IF;
 IF NOT EXISTS(SELECT 1 FROM lab.sources WHERE id=o.source_id AND status='approved' AND review_expires>n) THEN RAISE EXCEPTION 'source_not_approved'; END IF;
 IF NOT EXISTS(SELECT 1 FROM lab.raw_snapshots WHERE id=o.raw_snapshot_id AND data_kind='real' AND received_at<=o.observed_at) THEN RAISE EXCEPTION 'invalid_odds_provenance'; END IF;
 IF cardinality(p.input_snapshot_ids)=0 OR EXISTS (
   SELECT 1 FROM unnest(p.input_snapshot_ids) s(id) LEFT JOIN lab.raw_snapshots r ON r.id=s.id
   WHERE r.id IS NULL OR r.data_kind<>'real' OR r.received_at>p.feature_cutoff
 ) THEN RAISE EXCEPTION 'future_or_missing_features'; END IF;
 SELECT coalesce(sum(stake_kurus),0) INTO spent FROM lab.paper_bets WHERE budget_day=d;
 -- Voided/settled stakes still count against their original day. Returns do not replenish cap.
 IF spent+p_stake>10000 THEN RAISE EXCEPTION 'daily_limit'; END IF;
 SELECT coalesce(sum(stake_kurus),0) INTO exposure FROM lab.paper_bets WHERE status='open';
 IF exposure+p_stake>10000 THEN RAISE EXCEPTION 'exposure_limit'; END IF;
 IF w.balance_kurus<p_stake THEN RAISE EXCEPTION 'insufficient_funds'; END IF;
 INSERT INTO lab.paper_bets(idempotency_key,prediction_id,odds_id,match_id,stake_kurus,locked_odds,outcome,placed_at,budget_day)
 VALUES(p_key,p_prediction,p_odds,m.id,p_stake,o.decimal_odds,o.outcome,n,d) RETURNING id INTO bid;
 UPDATE lab.paper_wallet SET balance_kurus=balance_kurus-p_stake WHERE id=1;
 INSERT INTO lab.wallet_ledger(bet_id,event_key,kind,amount_kurus,balance_after_kurus)
 VALUES(bid,'stake:'||p_key,'stake',-p_stake,w.balance_kurus-p_stake);
 RETURN bid;
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA lab FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA lab FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA lab FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA lab REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA lab REVOKE ALL ON FUNCTIONS FROM PUBLIC;
DO $$ DECLARE t record; BEGIN
 FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='lab' LOOP
  EXECUTE format('ALTER TABLE lab.%I ENABLE ROW LEVEL SECURITY',t.tablename);
 END LOOP;
END $$;
-- No roles are granted execution yet. Dedicated worker + authenticated read policies
-- are phase 2/4 gates. DB owner always has administrative override, as in any PostgreSQL DB.
COMMIT;
