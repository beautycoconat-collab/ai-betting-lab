-- Phase 0 additive foundation. Apply AFTER unchanged 001 and 002.
-- No external service, no bookmaker integration, no automatic paid upgrade.
BEGIN;

CREATE TABLE lab.agent_roles (
 id text PRIMARY KEY, ordinal smallint NOT NULL UNIQUE CHECK(ordinal BETWEEN 1 AND 14),
 engine text NOT NULL CHECK(engine IN ('A','B','C','D')), description text NOT NULL,
 numeric_authority boolean NOT NULL DEFAULT false, implementation text NOT NULL DEFAULT 'contract_only'
);
INSERT INTO lab.agent_roles(id,ordinal,engine,description,numeric_authority) VALUES
 ('coordinator',1,'A','Schedule dependencies and budgets',false),
 ('source_hunter',2,'A','Discover permitted sources',false),
 ('data_validator',3,'A','Validate identities, provenance and targets',false),
 ('lineup_researcher',4,'A','Extract sourced lineup and tactical evidence',false),
 ('external_researcher',5,'A','Collect permitted external forecasts',false),
 ('team_strength',6,'B','Estimate team strength numerically',true),
 ('score_engine',7,'B','Compute score probability distributions',true),
 ('market_specialist',8,'B','Derive only supported markets',true),
 ('synthesizer',9,'B','Validated numerical synthesis',true),
 ('red_team',10,'C','Issue evidence-based objections; no overrides',false),
 ('scientific_referee',11,'C','Apply review rules, at most two rounds',false),
 ('odds_analyst',12,'D','Validate market prices and timestamps',false),
 ('risk_manager',13,'D','Paper-only bet/wait/skip risk gate',false),
 ('learning_auditor',14,'D','Evaluate models and promotion evidence',false);
DO $$ DECLARE r record; BEGIN
 FOR r IN SELECT id FROM lab.agent_roles LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='lab_'||r.id) THEN
   EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS','lab_'||r.id);
  END IF;
  EXECUTE format('GRANT USAGE ON SCHEMA lab TO %I','lab_'||r.id);
 END LOOP;
 IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='lab_dashboard') THEN CREATE ROLE lab_dashboard NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; END IF;
 GRANT USAGE ON SCHEMA lab TO lab_dashboard;
END $$;
CREATE FUNCTION lab.assert_agent(p_role text) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,lab AS $$
DECLARE actor text:=coalesce(nullif(current_setting('role'),'none'),session_user);
BEGIN
 IF NOT EXISTS(SELECT 1 FROM lab.agent_roles WHERE id=p_role) OR NOT pg_has_role(actor,'lab_'||p_role,'member') THEN RAISE EXCEPTION 'agent_permission_denied'; END IF;
END $$;

-- Retain legacy sources.status; richer versioned policy is authoritative for new RPCs.
CREATE TABLE lab.source_access_policies (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),source_id text NOT NULL REFERENCES lab.sources,
 revision integer NOT NULL CHECK(revision>0),status text NOT NULL CHECK(status IN ('approved','conditional','blocked','pending_review','disabled')),
 permission_url text NOT NULL,license text NOT NULL,review_expires timestamptz NOT NULL,
 max_daily integer NOT NULL CHECK(max_daily BETWEEN 0 AND 10000),min_interval_seconds integer NOT NULL CHECK(min_interval_seconds>=0),
 coverage jsonb NOT NULL DEFAULT '{}',created_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(source_id,revision)
);
CREATE TABLE lab.source_dependencies (
 source_id text REFERENCES lab.sources,upstream_id text REFERENCES lab.sources,
 relationship text NOT NULL CHECK(relationship IN ('mirror','derived','suspected')),evidence_snapshot_id uuid NOT NULL REFERENCES lab.raw_snapshots,
 PRIMARY KEY(source_id,upstream_id),CHECK(source_id<>upstream_id)
);
CREATE TABLE lab.competitions(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),canonical_key text NOT NULL UNIQUE,name text NOT NULL);
CREATE TABLE lab.seasons(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),competition_id uuid NOT NULL REFERENCES lab.competitions,label text NOT NULL,starts_on date,ends_on date,UNIQUE(competition_id,label),CHECK(ends_on IS NULL OR starts_on IS NULL OR ends_on>=starts_on));
CREATE TABLE lab.fixture_contexts (
 fixture_id uuid PRIMARY KEY REFERENCES lab.matches,season_id uuid NOT NULL REFERENCES lab.seasons,
 score_target text NOT NULL CHECK(score_target IN ('regulation90','final_including_extra_time','provider_final_unknown')),
 identity_status text NOT NULL CHECK(identity_status IN ('verified','unknown','conflicting','unverified')),
 neutral boolean
);
CREATE TABLE lab.canonical_mappings (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),source_id text NOT NULL REFERENCES lab.sources,native_id text NOT NULL,
 team_id uuid REFERENCES lab.teams,fixture_id uuid REFERENCES lab.matches,competition_id uuid REFERENCES lab.competitions,
 snapshot_id uuid NOT NULL REFERENCES lab.raw_snapshots,quality text NOT NULL CHECK(quality IN ('verified','unknown','conflicting','unverified')),
 CHECK(num_nonnulls(team_id,fixture_id,competition_id)=1),UNIQUE(source_id,native_id,team_id,fixture_id,competition_id)
);
CREATE TABLE lab.fixture_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),fixture_id uuid NOT NULL REFERENCES lab.matches,snapshot_id uuid NOT NULL REFERENCES lab.raw_snapshots,
 event_type text NOT NULL,occurred_at timestamptz,observed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 quality text NOT NULL CHECK(quality IN ('verified','unknown','conflicting','unverified')),payload jsonb NOT NULL
);
CREATE UNIQUE INDEX canonical_team_key ON lab.canonical_mappings(source_id,native_id) WHERE team_id IS NOT NULL;
CREATE UNIQUE INDEX canonical_fixture_key ON lab.canonical_mappings(source_id,native_id) WHERE fixture_id IS NOT NULL;
CREATE UNIQUE INDEX canonical_competition_key ON lab.canonical_mappings(source_id,native_id) WHERE competition_id IS NOT NULL;
CREATE TABLE lab.feature_snapshots (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),fixture_id uuid NOT NULL REFERENCES lab.matches,
 score_target text NOT NULL CHECK(score_target IN ('regulation90','final_including_extra_time','provider_final_unknown')),
 feature_time timestamptz NOT NULL,available_at timestamptz NOT NULL,
 content_sha256 text NOT NULL CHECK(content_sha256 ~ '^[a-f0-9]{64}$'),features jsonb NOT NULL CHECK(pg_column_size(features)<=65536),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE lab.feature_snapshot_inputs(feature_id uuid REFERENCES lab.feature_snapshots,snapshot_id uuid REFERENCES lab.raw_snapshots,PRIMARY KEY(feature_id,snapshot_id));
CREATE TABLE lab.model_version_contracts (
 model_version_id uuid PRIMARY KEY REFERENCES lab.model_versions,dataset_id uuid NOT NULL REFERENCES lab.dataset_manifests,
 score_target text NOT NULL CHECK(score_target IN ('regulation90','final_including_extra_time','provider_final_unknown')),
 artifact_uri text NOT NULL,artifact_sha256 text NOT NULL CHECK(artifact_sha256 ~ '^[a-f0-9]{64}$')
);
CREATE TABLE lab.agent_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),role_id text NOT NULL REFERENCES lab.agent_roles,fixture_id uuid NOT NULL REFERENCES lab.matches,
 as_of timestamptz NOT NULL,mode text NOT NULL CHECK(mode IN ('prematch','retrospective')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),CHECK(as_of<=created_at),UNIQUE(id,role_id,fixture_id)
);
CREATE TABLE lab.evidence_references (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),fixture_id uuid NOT NULL REFERENCES lab.matches,
 source_id text NOT NULL REFERENCES lab.sources,snapshot_id uuid NOT NULL REFERENCES lab.raw_snapshots,
 score_target text NOT NULL CHECK(score_target IN ('regulation90','final_including_extra_time','provider_final_unknown')),
 observed_at timestamptz NOT NULL,published_at timestamptz,quality text NOT NULL CHECK(quality IN ('verified','unknown','conflicting','unverified')),
 claim text NOT NULL CHECK(length(claim) BETWEEN 1 AND 2000),CHECK(published_at IS NULL OR published_at<=observed_at)
);
CREATE FUNCTION lab.check_evidence() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lab AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM lab.raw_snapshots r WHERE r.id=NEW.snapshot_id AND r.source_id=NEW.source_id AND r.received_at=NEW.observed_at AND r.received_at<=clock_timestamp()) THEN RAISE EXCEPTION 'evidence_provenance_mismatch'; END IF;
 IF NOT EXISTS(SELECT 1 FROM lab.fixture_contexts WHERE fixture_id=NEW.fixture_id AND score_target=NEW.score_target) THEN RAISE EXCEPTION 'evidence_target_mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER evidence_provenance BEFORE INSERT ON lab.evidence_references FOR EACH ROW EXECUTE FUNCTION lab.check_evidence();
CREATE TABLE lab.agent_messages (
 message_id uuid PRIMARY KEY,schema_version text NOT NULL CHECK(schema_version='1.0'),
 agent_run_id uuid NOT NULL,fixture_id uuid NOT NULL,agent_role text NOT NULL,
 created_at timestamptz NOT NULL,received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 issue_type text NOT NULL CHECK(issue_type IN ('lineup_uncertainty','source_conflict','data_leakage','identity_error','low_sample','model_disagreement','overconfidence','shared_upstream','coupon_dependency','validation')),
 severity text NOT NULL CHECK(severity IN ('low','medium','high','critical')),
 requested_action text NOT NULL CHECK(requested_action IN ('review','scenario_analysis','recalculate','quarantine','abstain')),
 status text NOT NULL CHECK(status='pending_review'),numeric_override jsonb CHECK(numeric_override IS NULL),
 model_version_id uuid REFERENCES lab.model_versions,payload jsonb NOT NULL CHECK(pg_column_size(payload)<=16384),
 FOREIGN KEY(agent_run_id,agent_role,fixture_id) REFERENCES lab.agent_runs(id,role_id,fixture_id),CHECK(created_at<=received_at)
);
CREATE TABLE lab.message_evidence(message_id uuid REFERENCES lab.agent_messages,evidence_id uuid REFERENCES lab.evidence_references,PRIMARY KEY(message_id,evidence_id));
CREATE TABLE lab.message_snapshots(message_id uuid REFERENCES lab.agent_messages,snapshot_id uuid REFERENCES lab.raw_snapshots,PRIMARY KEY(message_id,snapshot_id));
CREATE TABLE lab.review_findings (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),message_id uuid NOT NULL UNIQUE REFERENCES lab.agent_messages,
 fixture_id uuid NOT NULL REFERENCES lab.matches,severity text NOT NULL CHECK(severity IN ('low','medium','high','critical')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE lab.review_cycles (
 fixture_id uuid PRIMARY KEY REFERENCES lab.matches,rounds integer NOT NULL DEFAULT 0 CHECK(rounds BETWEEN 0 AND 2),
 status text NOT NULL DEFAULT 'pending',risk_action text NOT NULL DEFAULT 'wait' CHECK(risk_action IN ('wait','skip'))
);
CREATE TABLE lab.review_decisions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),idempotency_key text NOT NULL UNIQUE,
 finding_id uuid NOT NULL REFERENCES lab.review_findings,reviewer_run_id uuid NOT NULL REFERENCES lab.agent_runs,
 fixture_id uuid NOT NULL REFERENCES lab.matches,round_no integer NOT NULL CHECK(round_no BETWEEN 1 AND 2),
 status text NOT NULL CHECK(status IN ('approved','needs_reanalysis','insufficient_evidence','rejected','abstain')),
 risk_action text NOT NULL CHECK(risk_action IN ('wait','skip')),reason text NOT NULL,
 resolution_evidence_id uuid REFERENCES lab.evidence_references,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(fixture_id,round_no)
);
CREATE TABLE lab.reanalysis_requests(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),decision_id uuid NOT NULL UNIQUE REFERENCES lab.review_decisions,fixture_id uuid NOT NULL REFERENCES lab.matches,requested_action text NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp());
CREATE TABLE lab.prediction_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),fixture_id uuid NOT NULL REFERENCES lab.matches,
 model_version_id uuid NOT NULL REFERENCES lab.model_version_contracts,feature_snapshot_id uuid NOT NULL REFERENCES lab.feature_snapshots,
 agent_run_id uuid NOT NULL REFERENCES lab.agent_runs,revision integer NOT NULL CHECK(revision>0),previous_id uuid REFERENCES lab.prediction_runs,
 as_of timestamptz NOT NULL,mode text NOT NULL CHECK(mode IN ('prematch','retrospective')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(fixture_id,model_version_id,revision)
);
CREATE TABLE lab.score_probability_distributions (
 prediction_run_id uuid PRIMARY KEY REFERENCES lab.prediction_runs,
 home_rate double precision NOT NULL CHECK(home_rate BETWEEN 0.02 AND 8),away_rate double precision NOT NULL CHECK(away_rate BETWEEN 0.02 AND 8),
 rho double precision NOT NULL CHECK(rho BETWEEN -0.12 AND 0.015),grid jsonb NOT NULL CHECK(pg_column_size(grid)<=131072),
 tail double precision NOT NULL CHECK(tail BETWEEN 0 AND 1),p_home double precision NOT NULL CHECK(p_home BETWEEN 0 AND 1),
 p_draw double precision NOT NULL CHECK(p_draw BETWEEN 0 AND 1),p_away double precision NOT NULL CHECK(p_away BETWEEN 0 AND 1),
 CHECK(abs(p_home+p_draw+p_away-1)<1e-8)
);
CREATE TABLE lab.champion_promotions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),previous_model_id uuid REFERENCES lab.model_versions,
 new_model_id uuid NOT NULL REFERENCES lab.model_versions,evaluation_id uuid NOT NULL REFERENCES lab.evaluation_runs,
 auditor_run_id uuid NOT NULL REFERENCES lab.agent_runs,decision text NOT NULL CHECK(decision IN ('proposed','approved','rejected')),
 justification jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),CHECK(previous_model_id IS DISTINCT FROM new_model_id)
);
CREATE TABLE lab.workflow_jobs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),idempotency_key text NOT NULL UNIQUE,
 kind text NOT NULL CHECK(kind IN ('collect','validate','model','red_team','referee','reanalysis','save_prediction','settle')),
 role_id text NOT NULL REFERENCES lab.agent_roles,fixture_id uuid REFERENCES lab.matches,
 collection_job_id uuid REFERENCES lab.collection_jobs,parameters jsonb NOT NULL DEFAULT '{}' CHECK(pg_column_size(parameters)<=16384),
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','running','done','failed','blocked')),
 attempts integer NOT NULL DEFAULT 0 CHECK(attempts>=0),max_attempts integer NOT NULL DEFAULT 3 CHECK(max_attempts BETWEEN 1 AND 5),
 timeout_seconds integer NOT NULL DEFAULT 300 CHECK(timeout_seconds BETWEEN 1 AND 3600),not_before timestamptz NOT NULL DEFAULT clock_timestamp(),
 lease_token uuid,lease_until timestamptz,worker_id text,last_error text,
 CHECK((status='running')=(lease_token IS NOT NULL AND lease_until IS NOT NULL)),CHECK(attempts<=max_attempts)
);
CREATE INDEX workflow_due ON lab.workflow_jobs(role_id,status,not_before);
CREATE TABLE lab.workflow_dependencies(job_id uuid REFERENCES lab.workflow_jobs,depends_on uuid REFERENCES lab.workflow_jobs,PRIMARY KEY(job_id,depends_on),CHECK(job_id<>depends_on));
CREATE TABLE lab.workflow_attempts(id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,job_id uuid NOT NULL REFERENCES lab.workflow_jobs,token uuid NOT NULL UNIQUE,worker_id text NOT NULL,started_at timestamptz NOT NULL,lease_until timestamptz NOT NULL);
CREATE TABLE lab.calibration_reports(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),evaluation_id uuid NOT NULL REFERENCES lab.evaluation_runs,market text NOT NULL,score_target text NOT NULL,bins jsonb NOT NULL,n integer NOT NULL CHECK(n>0));
CREATE TABLE lab.ablation_results(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),baseline_evaluation_id uuid NOT NULL REFERENCES lab.evaluation_runs,treatment_evaluation_id uuid NOT NULL REFERENCES lab.evaluation_runs,module text NOT NULL,split_sha256 text NOT NULL CHECK(length(split_sha256)=64),metrics jsonb NOT NULL,CHECK(baseline_evaluation_id<>treatment_evaluation_id));
CREATE TABLE lab.source_performance(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),source_id text NOT NULL REFERENCES lab.sources,evaluation_id uuid NOT NULL REFERENCES lab.evaluation_runs,metrics jsonb NOT NULL,coverage numeric NOT NULL CHECK(coverage BETWEEN 0 AND 1));
CREATE TABLE lab.model_performance(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),model_id uuid NOT NULL REFERENCES lab.model_versions,evaluation_id uuid NOT NULL REFERENCES lab.evaluation_runs,metrics jsonb NOT NULL);

-- Coupon versus selection amounts are separate. 50 TRY is UNVERIFIED, configurable.
CREATE TABLE lab.coupon_rule_versions (
 id text PRIMARY KEY,minimum_cost_kurus integer NOT NULL CHECK(minimum_cost_kurus>0),
 assumption_status text NOT NULL CHECK(assumption_status IN ('user_reported_unverified','verified')),
 source_url text,enabled boolean NOT NULL DEFAULT false,maximum_cost_kurus integer NOT NULL CHECK(maximum_cost_kurus BETWEEN 1 AND 10000),
 strategy text NOT NULL CHECK(strategy='Balanced'),mbs integer NOT NULL CHECK(mbs>=1),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),CHECK(minimum_cost_kurus<=maximum_cost_kurus)
);
INSERT INTO lab.coupon_rule_versions VALUES('paper-assumption-v1',5000,'user_reported_unverified',NULL,false,10000,'Balanced',1,clock_timestamp());
CREATE TABLE lab.betting_decisions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),prediction_run_id uuid NOT NULL REFERENCES lab.prediction_runs,
 review_decision_id uuid NOT NULL REFERENCES lab.review_decisions,odds_id uuid REFERENCES lab.odds_snapshots,
 action text NOT NULL CHECK(action IN ('bet','wait','skip')),maximum_stake_kurus integer NOT NULL CHECK(maximum_stake_kurus BETWEEN 0 AND 10000),
 reason text NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),CHECK(action<>'bet' OR (odds_id IS NOT NULL AND maximum_stake_kurus>0))
);
CREATE TABLE lab.virtual_coupons (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),idempotency_key text NOT NULL UNIQUE,decision_id uuid NOT NULL REFERENCES lab.betting_decisions,
 rule_version text NOT NULL REFERENCES lab.coupon_rule_versions,type text NOT NULL CHECK(type IN ('single','combined','system')),
 total_cost_kurus integer NOT NULL CHECK(total_cost_kurus>0),columns integer NOT NULL CHECK(columns>0),multiplier integer NOT NULL CHECK(multiplier>0),
 budget_day date NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),status text NOT NULL CHECK(status IN ('open','settled'))
);
CREATE TABLE lab.coupon_selections (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),coupon_id uuid NOT NULL REFERENCES lab.virtual_coupons,fixture_id uuid NOT NULL REFERENCES lab.matches,
 prediction_run_id uuid NOT NULL REFERENCES lab.prediction_runs,odds_id uuid NOT NULL REFERENCES lab.odds_snapshots,
 market text NOT NULL,outcome text NOT NULL,locked_odds numeric NOT NULL CHECK(locked_odds>1),UNIQUE(coupon_id,fixture_id,market)
);
ALTER TABLE lab.wallet_ledger ADD COLUMN coupon_id uuid REFERENCES lab.virtual_coupons;
ALTER TABLE lab.wallet_ledger ADD CONSTRAINT one_wager_reference CHECK(num_nonnulls(bet_id,coupon_id)<=1);
CREATE TABLE lab.coupon_settlement_records (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),coupon_id uuid NOT NULL UNIQUE REFERENCES lab.virtual_coupons,
 event_id uuid NOT NULL REFERENCES lab.fixture_events,kind text NOT NULL CHECK(kind='void'),payout_kurus integer NOT NULL CHECK(payout_kurus>=0),
 idempotency_key text NOT NULL UNIQUE,settled_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX coupon_day ON lab.virtual_coupons(budget_day);
CREATE INDEX coupon_open ON lab.virtual_coupons(status);
CREATE TABLE lab.storage_policies (
 data_class text PRIMARY KEY,location text NOT NULL,retention_days integer NOT NULL CHECK(retention_days>0),
 max_object_bytes bigint NOT NULL CHECK(max_object_bytes>0),soft_budget_bytes bigint NOT NULL CHECK(soft_budget_bytes>0),
 archive_before_delete boolean NOT NULL DEFAULT true
);
INSERT INTO lab.storage_policies VALUES
 ('raw','local_or_existing_storage',30,2000000,40000000,true),
 ('normalized','postgres',730,65536,100000000,true),
 ('artifact','local_or_existing_storage',730,20000000,100000000,true),
 ('audit','postgres_and_export',2555,16384,50000000,true);
CREATE TABLE lab.integrity_exports(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),created_at timestamptz NOT NULL DEFAULT clock_timestamp(),last_event_id bigint NOT NULL,content_sha256 text NOT NULL CHECK(length(content_sha256)=64),archive_uri text NOT NULL);
CREATE TABLE lab.audit_events(id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),actor text NOT NULL,event_type text NOT NULL,entity_id text NOT NULL,payload jsonb NOT NULL CHECK(pg_column_size(payload)<=16384));
CREATE FUNCTION lab.reject_large_raw_payload() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF octet_length(NEW.payload::text)>65536 THEN RAISE EXCEPTION 'raw_payload_store_externally'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER raw_payload_budget BEFORE INSERT ON lab.raw_snapshots FOR EACH ROW EXECUTE FUNCTION lab.reject_large_raw_payload();

-- New prediction revisions reuse canonical fixture/model IDs, with strict time/target guards.
CREATE FUNCTION lab.check_prediction_run() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lab AS $$
DECLARE f lab.feature_snapshots%ROWTYPE;m lab.model_versions%ROWTYPE;c lab.model_version_contracts%ROWTYPE;
 r lab.agent_runs%ROWTYPE;ctx lab.fixture_contexts%ROWTYPE;match lab.matches%ROWTYPE;previous lab.prediction_runs%ROWTYPE;ds lab.dataset_manifests%ROWTYPE;
BEGIN
 SELECT * INTO STRICT f FROM lab.feature_snapshots WHERE id=NEW.feature_snapshot_id;
 SELECT * INTO STRICT c FROM lab.model_version_contracts WHERE model_version_id=NEW.model_version_id;
 SELECT * INTO STRICT m FROM lab.model_versions WHERE id=NEW.model_version_id;
 SELECT * INTO STRICT ds FROM lab.dataset_manifests WHERE id=c.dataset_id;
 SELECT * INTO STRICT r FROM lab.agent_runs WHERE id=NEW.agent_run_id;
 SELECT * INTO STRICT ctx FROM lab.fixture_contexts WHERE fixture_id=NEW.fixture_id;
 SELECT * INTO STRICT match FROM lab.matches WHERE id=NEW.fixture_id FOR UPDATE;
 IF r.role_id<>'score_engine' OR r.fixture_id<>NEW.fixture_id OR r.mode<>NEW.mode OR r.as_of<>NEW.as_of OR f.fixture_id<>NEW.fixture_id THEN RAISE EXCEPTION 'prediction_identity_mismatch'; END IF;
 IF ctx.score_target<>c.score_target OR c.score_target<>f.score_target OR ds.score_definition<>c.score_target THEN RAISE EXCEPTION 'prediction_target_mismatch'; END IF;
 IF match.kickoff_at IS NULL OR m.trained_through>=match.kickoff_at OR m.trained_through>f.feature_time OR f.feature_time>NEW.as_of OR NEW.as_of>NEW.created_at OR m.trained_through::date>=ds.train_end_exclusive THEN RAISE EXCEPTION 'prediction_time_leakage'; END IF;
 IF NOT EXISTS(SELECT 1 FROM lab.feature_snapshot_inputs WHERE feature_id=f.id) THEN RAISE EXCEPTION 'missing_feature_inputs'; END IF;
 IF NEW.mode='prematch' AND (NEW.created_at>=match.kickoff_at OR f.available_at>NEW.as_of OR ctx.identity_status<>'verified' OR EXISTS(SELECT 1 FROM lab.feature_snapshot_inputs i JOIN lab.raw_snapshots s ON s.id=i.snapshot_id WHERE i.feature_id=f.id AND (s.received_at>NEW.as_of OR s.data_kind<>'real'))) THEN RAISE EXCEPTION 'prematch_provenance_invalid'; END IF;
 SELECT * INTO previous FROM lab.prediction_runs WHERE fixture_id=NEW.fixture_id AND model_version_id=NEW.model_version_id ORDER BY revision DESC LIMIT 1;
 IF NEW.revision<>coalesce(previous.revision,0)+1 OR NEW.previous_id IS DISTINCT FROM previous.id THEN RAISE EXCEPTION 'revision_chain_invalid'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER prediction_run_valid BEFORE INSERT ON lab.prediction_runs FOR EACH ROW EXECUTE FUNCTION lab.check_prediction_run();
CREATE FUNCTION lab.check_score_distribution() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lab AS $$
DECLARE row_value jsonb;cell jsonb;mass float8:=0;width integer;h integer:=0;a integer;ph float8;pa float8;expected float8;tau float8;home_mass float8:=0;draw_mass float8:=0;away_mass float8:=0;
BEGIN
 IF jsonb_typeof(NEW.grid)<>'array' OR jsonb_array_length(NEW.grid) NOT BETWEEN 2 AND 101 THEN RAISE EXCEPTION 'invalid_grid'; END IF;
 FOR row_value IN SELECT value FROM jsonb_array_elements(NEW.grid) LOOP
  IF jsonb_typeof(row_value)<>'array' THEN RAISE EXCEPTION 'invalid_grid'; END IF;
  IF width IS NULL THEN width:=jsonb_array_length(row_value); END IF;
  IF width NOT BETWEEN 2 AND 101 OR jsonb_array_length(row_value)<>width THEN RAISE EXCEPTION 'invalid_grid'; END IF;
  ph:=exp(-NEW.home_rate)*power(NEW.home_rate,h)/factorial(h);a:=0;
  FOR cell IN SELECT value FROM jsonb_array_elements(row_value) LOOP
   IF jsonb_typeof(cell)<>'number' OR (cell::text)::float8 NOT BETWEEN 0 AND 1 THEN RAISE EXCEPTION 'invalid_probability'; END IF;
   pa:=exp(-NEW.away_rate)*power(NEW.away_rate,a)/factorial(a);
   tau:=CASE WHEN h=0 AND a=0 THEN 1-NEW.home_rate*NEW.away_rate*NEW.rho WHEN h=0 AND a=1 THEN 1+NEW.home_rate*NEW.rho WHEN h=1 AND a=0 THEN 1+NEW.away_rate*NEW.rho WHEN h=1 AND a=1 THEN 1-NEW.rho ELSE 1 END;
   expected:=ph*pa*tau;
   IF abs((cell::text)::float8-expected)>1e-8 THEN RAISE EXCEPTION 'grid_model_mismatch'; END IF;
   mass:=mass+(cell::text)::float8;
   IF h>a THEN home_mass:=home_mass+expected; ELSIF h=a THEN draw_mass:=draw_mass+expected; ELSE away_mass:=away_mass+expected; END IF;
   a:=a+1;
  END LOOP;
  h:=h+1;
 END LOOP;
 IF abs(mass+NEW.tail-1)>1e-8 THEN RAISE EXCEPTION 'probability_mass'; END IF;
 IF NEW.p_home<home_mass-1e-8 OR NEW.p_home>home_mass+NEW.tail+1e-8 OR NEW.p_draw<draw_mass-1e-8 OR NEW.p_draw>draw_mass+NEW.tail+1e-8 OR NEW.p_away<away_mass-1e-8 OR NEW.p_away>away_mass+NEW.tail+1e-8 THEN RAISE EXCEPTION 'outcome_grid_mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER score_distribution_valid BEFORE INSERT ON lab.score_probability_distributions FOR EACH ROW EXECUTE FUNCTION lab.check_score_distribution();

-- Function-only writes for role-facing messages; raw JSON cannot choose an authority.
CREATE FUNCTION lab.start_agent_run(p_role text,p_fixture uuid,p_as_of timestamptz,p_mode text) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE result uuid;
BEGIN
 PERFORM lab.assert_agent(p_role);
 IF p_mode='prematch' AND NOT EXISTS(SELECT 1 FROM lab.matches WHERE id=p_fixture AND kickoff_at>clock_timestamp() AND kickoff_at>p_as_of) THEN RAISE EXCEPTION 'kickoff_passed'; END IF;
 INSERT INTO lab.agent_runs(role_id,fixture_id,as_of,mode) VALUES(p_role,p_fixture,p_as_of,p_mode) RETURNING id INTO result;
 RETURN result;
END $$;
CREATE FUNCTION lab.post_agent_message(p jsonb) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE mid uuid;run lab.agent_runs%ROWTYPE;eid uuid;sid uuid;prior jsonb;keys text[]:=ARRAY['schema_version','message_id','agent_run_id','fixture_id','agent_role','created_at','input_snapshot_ids','evidence_ids','model_version_id','issue_type','severity','requested_action','status','numeric_override','note'];
BEGIN
 PERFORM lab.assert_agent(p->>'agent_role');
 IF jsonb_typeof(p)<>'object' OR NOT p ?& ARRAY['schema_version','message_id','agent_run_id','fixture_id','agent_role','created_at','input_snapshot_ids','evidence_ids','issue_type','severity','requested_action','status','numeric_override'] OR EXISTS(SELECT 1 FROM jsonb_object_keys(p) k WHERE NOT k=ANY(keys)) THEN RAISE EXCEPTION 'message_schema_invalid'; END IF;
 IF p->>'schema_version'<>'1.0' OR p->'numeric_override'<>'null'::jsonb OR p->>'status'<>'pending_review' OR jsonb_typeof(p->'evidence_ids')<>'array' OR jsonb_typeof(p->'input_snapshot_ids')<>'array' THEN RAISE EXCEPTION 'message_schema_invalid'; END IF;
 IF jsonb_array_length(p->'evidence_ids') NOT BETWEEN 1 AND 100 OR jsonb_array_length(p->'input_snapshot_ids') NOT BETWEEN 1 AND 100 THEN RAISE EXCEPTION 'evidence_required'; END IF;
 mid:=(p->>'message_id')::uuid;
 PERFORM pg_advisory_xact_lock(hashtextextended(mid::text,0));
 SELECT payload INTO prior FROM lab.agent_messages WHERE message_id=mid;
 IF FOUND THEN IF prior<>p THEN RAISE EXCEPTION 'idempotency_conflict'; END IF;RETURN mid;END IF;
 SELECT * INTO STRICT run FROM lab.agent_runs WHERE id=(p->>'agent_run_id')::uuid;
 IF run.role_id<>p->>'agent_role' OR run.fixture_id<>(p->>'fixture_id')::uuid OR (p->>'created_at')::timestamptz<run.as_of THEN RAISE EXCEPTION 'run_identity_mismatch'; END IF;
 FOR eid IN SELECT value::uuid FROM jsonb_array_elements_text(p->'evidence_ids') LOOP
  IF NOT EXISTS(SELECT 1 FROM lab.evidence_references e WHERE e.id=eid AND e.fixture_id=run.fixture_id AND (run.mode='retrospective' OR e.observed_at<=run.as_of) AND p->'input_snapshot_ids' ? e.snapshot_id::text) THEN RAISE EXCEPTION 'missing_or_future_evidence'; END IF;
 END LOOP;
 FOR sid IN SELECT value::uuid FROM jsonb_array_elements_text(p->'input_snapshot_ids') LOOP
  IF NOT EXISTS(SELECT 1 FROM lab.evidence_references e WHERE e.snapshot_id=sid AND p->'evidence_ids' ? e.id::text) THEN RAISE EXCEPTION 'snapshot_evidence_mismatch'; END IF;
 END LOOP;
 INSERT INTO lab.agent_messages(message_id,schema_version,agent_run_id,fixture_id,agent_role,created_at,issue_type,severity,requested_action,status,numeric_override,model_version_id,payload)
 VALUES(mid,p->>'schema_version',run.id,run.fixture_id,run.role_id,(p->>'created_at')::timestamptz,p->>'issue_type',p->>'severity',p->>'requested_action',p->>'status',NULL,(p->>'model_version_id')::uuid,p);
 INSERT INTO lab.message_evidence SELECT mid,value::uuid FROM jsonb_array_elements_text(p->'evidence_ids');
 INSERT INTO lab.message_snapshots SELECT mid,value::uuid FROM jsonb_array_elements_text(p->'input_snapshot_ids');
 IF run.role_id IN ('red_team','data_validator') THEN INSERT INTO lab.review_findings(message_id,fixture_id,severity) VALUES(mid,run.fixture_id,p->>'severity');END IF;
 INSERT INTO lab.audit_events(actor,event_type,entity_id,payload) VALUES(run.role_id,'message',mid::text,jsonb_build_object('run_id',run.id));
 RETURN mid;
END $$;

CREATE FUNCTION lab.decide_review(p_key text,p_finding uuid,p_run uuid,p_resolution uuid DEFAULT NULL) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE f lab.review_findings%ROWTYPE;r lab.agent_runs%ROWTYPE;cycle lab.review_cycles%ROWTYPE;old lab.review_decisions%ROWTYPE;n integer;s text;a text;result uuid;
BEGIN
 PERFORM lab.assert_agent('scientific_referee');
 PERFORM pg_advisory_xact_lock(hashtextextended(p_key,1));
 SELECT * INTO old FROM lab.review_decisions WHERE idempotency_key=p_key;
 IF FOUND THEN
  IF old.finding_id<>p_finding OR old.reviewer_run_id<>p_run OR old.resolution_evidence_id IS DISTINCT FROM p_resolution THEN RAISE EXCEPTION 'idempotency_conflict'; END IF;RETURN old.id;
 END IF;
 SELECT * INTO STRICT f FROM lab.review_findings WHERE id=p_finding;
 SELECT * INTO STRICT r FROM lab.agent_runs WHERE id=p_run;
 IF r.role_id<>'scientific_referee' OR r.fixture_id<>f.fixture_id THEN RAISE EXCEPTION 'referee_identity_mismatch'; END IF;
 INSERT INTO lab.review_cycles(fixture_id) VALUES(f.fixture_id) ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT cycle FROM lab.review_cycles WHERE fixture_id=f.fixture_id FOR UPDATE;
 IF cycle.rounds>=2 OR cycle.risk_action='skip' THEN RAISE EXCEPTION 'review_limit'; END IF;
 IF p_resolution IS NOT NULL AND NOT EXISTS(SELECT 1 FROM lab.evidence_references e WHERE e.id=p_resolution AND e.fixture_id=f.fixture_id AND e.quality='verified' AND e.observed_at<=r.as_of AND NOT EXISTS(SELECT 1 FROM lab.message_evidence me WHERE me.message_id=f.message_id AND me.evidence_id=e.id)) THEN RAISE EXCEPTION 'unverified_resolution'; END IF;
 n:=cycle.rounds+1;s:=CASE WHEN p_resolution IS NOT NULL THEN 'approved' WHEN n=2 THEN 'abstain' ELSE 'needs_reanalysis' END;a:=CASE WHEN s='abstain' THEN 'skip' ELSE 'wait' END;
 INSERT INTO lab.review_decisions(idempotency_key,finding_id,reviewer_run_id,fixture_id,round_no,status,risk_action,reason,resolution_evidence_id)
 VALUES(p_key,p_finding,p_run,f.fixture_id,n,s,a,CASE WHEN p_resolution IS NULL THEN 'unresolved_evidence' ELSE 'new_verified_evidence' END,p_resolution) RETURNING id INTO result;
 UPDATE lab.review_cycles SET rounds=n,status=s,risk_action=a WHERE fixture_id=f.fixture_id;
 IF s='needs_reanalysis' THEN INSERT INTO lab.reanalysis_requests(decision_id,fixture_id,requested_action) VALUES(result,f.fixture_id,'recalculate');END IF;
 INSERT INTO lab.audit_events(actor,event_type,entity_id,payload) VALUES('scientific_referee','review',result::text,jsonb_build_object('status',s,'round',n));
 RETURN result;
END $$;

CREATE FUNCTION lab.enqueue_workflow(p_key text,p_kind text,p_fixture uuid,p_parameters jsonb DEFAULT '{}',p_dependencies uuid[] DEFAULT '{}') RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE role_name text;old lab.workflow_jobs%ROWTYPE;result uuid;dep uuid;
BEGIN
 PERFORM lab.assert_agent('coordinator');PERFORM pg_advisory_xact_lock(hashtextextended(p_key,2));
 role_name:=CASE p_kind WHEN 'collect' THEN 'source_hunter' WHEN 'validate' THEN 'data_validator' WHEN 'model' THEN 'score_engine' WHEN 'red_team' THEN 'red_team' WHEN 'referee' THEN 'scientific_referee' WHEN 'reanalysis' THEN 'score_engine' WHEN 'save_prediction' THEN 'score_engine' WHEN 'settle' THEN 'risk_manager' END;
 IF role_name IS NULL OR length(p_key)<8 THEN RAISE EXCEPTION 'invalid_job'; END IF;
 SELECT * INTO old FROM lab.workflow_jobs WHERE idempotency_key=p_key;
 IF FOUND THEN
  IF old.kind<>p_kind OR old.fixture_id IS DISTINCT FROM p_fixture OR old.parameters<>p_parameters OR (SELECT coalesce(array_agg(depends_on ORDER BY depends_on),'{}'::uuid[]) FROM lab.workflow_dependencies WHERE job_id=old.id)<>(SELECT coalesce(array_agg(x ORDER BY x),'{}'::uuid[]) FROM unnest(p_dependencies) x) THEN RAISE EXCEPTION 'idempotency_conflict'; END IF;RETURN old.id;
 END IF;
 INSERT INTO lab.workflow_jobs(idempotency_key,kind,role_id,fixture_id,parameters) VALUES(p_key,p_kind,role_name,p_fixture,p_parameters) RETURNING id INTO result;
 FOREACH dep IN ARRAY p_dependencies LOOP INSERT INTO lab.workflow_dependencies VALUES(result,dep);END LOOP;
 RETURN result;
END $$;
CREATE FUNCTION lab.claim_workflow(p_role text,p_worker text) RETURNS SETOF lab.workflow_jobs LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE j lab.workflow_jobs%ROWTYPE;
BEGIN
 PERFORM lab.assert_agent(p_role);
 UPDATE lab.workflow_jobs SET status='failed',lease_until=NULL,lease_token=NULL,last_error='lease_expired_max_attempts' WHERE role_id=p_role AND status='running' AND lease_until<=clock_timestamp() AND attempts>=max_attempts;
 UPDATE lab.workflow_jobs queued SET status='blocked',last_error='dependency_failed' WHERE queued.role_id=p_role AND queued.status='pending' AND EXISTS(SELECT 1 FROM lab.workflow_dependencies d JOIN lab.workflow_jobs p ON p.id=d.depends_on WHERE d.job_id=queued.id AND p.status IN ('failed','blocked'));
 SELECT * INTO j FROM lab.workflow_jobs w WHERE w.role_id=p_role AND ((w.status='pending' AND w.not_before<=clock_timestamp()) OR (w.status='running' AND w.lease_until<=clock_timestamp())) AND w.attempts<w.max_attempts AND NOT EXISTS(SELECT 1 FROM lab.workflow_dependencies d JOIN lab.workflow_jobs p ON p.id=d.depends_on WHERE d.job_id=w.id AND p.status<>'done') ORDER BY not_before,id FOR UPDATE SKIP LOCKED LIMIT 1;
 IF NOT FOUND THEN RETURN; END IF;
 UPDATE lab.workflow_jobs SET status='running',attempts=attempts+1,lease_token=gen_random_uuid(),lease_until=clock_timestamp()+make_interval(secs=>timeout_seconds),worker_id=p_worker WHERE id=j.id RETURNING * INTO j;
 INSERT INTO lab.workflow_attempts(job_id,token,worker_id,started_at,lease_until) VALUES(j.id,j.lease_token,p_worker,clock_timestamp(),j.lease_until);
 RETURN NEXT j;
END $$;
CREATE FUNCTION lab.finish_workflow(p_id uuid,p_token uuid,p_worker text,p_error text DEFAULT NULL) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE j lab.workflow_jobs%ROWTYPE;
BEGIN
 SELECT * INTO j FROM lab.workflow_jobs WHERE id=p_id FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM lab.assert_agent(j.role_id);
 IF j.status<>'running' OR j.lease_token<>p_token OR j.worker_id<>p_worker OR j.lease_until<=clock_timestamp() THEN RETURN false; END IF;
 UPDATE lab.workflow_jobs SET status=CASE WHEN p_error IS NULL THEN 'done' WHEN attempts>=max_attempts THEN 'failed' ELSE 'pending' END,lease_until=NULL,lease_token=NULL,last_error=p_error,not_before=clock_timestamp()+make_interval(secs=>30*power(2,attempts)::integer) WHERE id=p_id;
 RETURN true;
END $$;
CREATE FUNCTION lab.reserve_source_request(p_source text) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE p lab.source_access_policies%ROWTYPE;start_at timestamptz;used_count integer;last_at timestamptz;
BEGIN
 PERFORM lab.assert_agent('source_hunter');PERFORM 1 FROM lab.sources WHERE id=p_source FOR UPDATE;
 SELECT * INTO STRICT p FROM lab.source_access_policies WHERE source_id=p_source ORDER BY revision DESC LIMIT 1;
 IF p.status<>'approved' OR p.review_expires<=clock_timestamp() THEN RETURN false; END IF;
 IF NOT EXISTS(SELECT 1 FROM lab.sources WHERE id=p_source AND status='approved') THEN RETURN false; END IF;
 SELECT max(started_at) INTO last_at FROM lab.ingestion_runs WHERE source_id=p_source AND status='request_reserved';
 IF last_at IS NOT NULL AND last_at+make_interval(secs=>p.min_interval_seconds)>clock_timestamp() THEN RETURN false; END IF;
 SELECT count(*) INTO used_count FROM lab.ingestion_runs WHERE source_id=p_source AND status='request_reserved' AND started_at>clock_timestamp()-interval '24 hours';
 IF used_count>=p.max_daily THEN RETURN false; END IF;
 SELECT count(*) INTO used_count FROM lab.ingestion_runs WHERE source_id=p_source AND status='request_reserved' AND started_at>clock_timestamp()-interval '31 days';
 IF used_count>=124 THEN RETURN false; END IF;
 start_at:=date_trunc('day',clock_timestamp());
 INSERT INTO lab.quota_usage(source_id,window_start,window_end,used,ceiling) VALUES(p_source,start_at,start_at+interval '1 day',1,p.max_daily)
 ON CONFLICT(source_id,window_start) DO UPDATE SET used=lab.quota_usage.used+1;
 INSERT INTO lab.ingestion_runs(source_id,status,reason) VALUES(p_source,'request_reserved','Count BEFORE HTTP; failed attempts consume quota');
 RETURN true;
END $$;

CREATE FUNCTION lab.register_evidence(p_id uuid,p_fixture uuid,p_snapshot uuid,p_target text,p_quality text,p_claim text,p_published timestamptz DEFAULT NULL) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE s lab.raw_snapshots%ROWTYPE;p lab.source_access_policies%ROWTYPE;
BEGIN
 PERFORM lab.assert_agent('data_validator');
 SELECT * INTO STRICT s FROM lab.raw_snapshots WHERE id=p_snapshot;
 SELECT * INTO STRICT p FROM lab.source_access_policies WHERE source_id=s.source_id ORDER BY revision DESC LIMIT 1;
 IF p.status<>'approved' OR p.review_expires<=clock_timestamp() THEN RAISE EXCEPTION 'source_not_approved'; END IF;
 INSERT INTO lab.evidence_references(id,fixture_id,source_id,snapshot_id,score_target,observed_at,published_at,quality,claim)
 VALUES(p_id,p_fixture,s.source_id,s.id,p_target,s.received_at,p_published,p_quality,p_claim);
 RETURN p_id;
END $$;
CREATE FUNCTION lab.record_prediction(p_fixture uuid,p_model uuid,p_feature uuid,p_run uuid,p_distribution jsonb) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE previous lab.prediction_runs%ROWTYPE;r lab.agent_runs%ROWTYPE;result uuid;
BEGIN
 PERFORM lab.assert_agent('score_engine');
 PERFORM 1 FROM lab.matches WHERE id=p_fixture FOR UPDATE;
 SELECT * INTO STRICT r FROM lab.agent_runs WHERE id=p_run;
 SELECT * INTO previous FROM lab.prediction_runs WHERE fixture_id=p_fixture AND model_version_id=p_model ORDER BY revision DESC LIMIT 1;
 INSERT INTO lab.prediction_runs(fixture_id,model_version_id,feature_snapshot_id,agent_run_id,revision,previous_id,as_of,mode)
 VALUES(p_fixture,p_model,p_feature,p_run,coalesce(previous.revision,0)+1,previous.id,r.as_of,r.mode) RETURNING id INTO result;
 INSERT INTO lab.score_probability_distributions VALUES(result,(p_distribution->>'home_rate')::float8,(p_distribution->>'away_rate')::float8,(p_distribution->>'rho')::float8,p_distribution->'grid',(p_distribution->>'outside_grid_probability')::float8,(p_distribution->'p_1x2'->>0)::float8,(p_distribution->'p_1x2'->>1)::float8,(p_distribution->'p_1x2'->>2)::float8);
 INSERT INTO lab.audit_events(actor,event_type,entity_id,payload) VALUES('score_engine','prediction',result::text,jsonb_build_object('model_id',p_model,'fixture_id',p_fixture));
 RETURN result;
END $$;

-- Budget trigger also protects the old single-bet path, without rewriting its function.
CREATE FUNCTION lab.check_shared_paper_budget() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lab AS $$
DECLARE day_spent bigint;open_risk bigint;cost integer;
BEGIN
 PERFORM 1 FROM lab.paper_wallet WHERE id=1 FOR UPDATE;
 cost:=CASE WHEN TG_TABLE_NAME='paper_bets' THEN (to_jsonb(NEW)->>'stake_kurus')::integer ELSE (to_jsonb(NEW)->>'total_cost_kurus')::integer END;
 IF NEW.budget_day<>(clock_timestamp() AT TIME ZONE 'Europe/Istanbul')::date THEN RAISE EXCEPTION 'server_budget_day_required'; END IF;
 SELECT (SELECT coalesce(sum(stake_kurus),0) FROM lab.paper_bets WHERE budget_day=NEW.budget_day)+(SELECT coalesce(sum(total_cost_kurus),0) FROM lab.virtual_coupons WHERE budget_day=NEW.budget_day) INTO day_spent;
 SELECT (SELECT coalesce(sum(stake_kurus),0) FROM lab.paper_bets WHERE status='open')+(SELECT coalesce(sum(total_cost_kurus),0) FROM lab.virtual_coupons WHERE status='open') INTO open_risk;
 IF day_spent+cost>10000 THEN RAISE EXCEPTION 'daily_limit'; END IF;
 IF open_risk+cost>10000 THEN RAISE EXCEPTION 'exposure_limit'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER shared_budget BEFORE INSERT ON lab.paper_bets FOR EACH ROW EXECUTE FUNCTION lab.check_shared_paper_budget();
CREATE TRIGGER shared_budget BEFORE INSERT ON lab.virtual_coupons FOR EACH ROW EXECUTE FUNCTION lab.check_shared_paper_budget();

-- Only a disabled-by-default, single-selection foundation path exists.
-- Future combination/system engines must use the same shared budget lock.
CREATE FUNCTION lab.reserve_virtual_coupon(p_key text,p_decision uuid,p_rule text,p_cost integer) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE w lab.paper_wallet%ROWTYPE;c lab.virtual_coupons%ROWTYPE;d lab.betting_decisions%ROWTYPE;r lab.coupon_rule_versions%ROWTYPE;
 pr lab.prediction_runs%ROWTYPE;o lab.odds_snapshots%ROWTYPE;m lab.matches%ROWTYPE;result uuid;
BEGIN
 PERFORM lab.assert_agent('risk_manager');
 SELECT * INTO STRICT w FROM lab.paper_wallet WHERE id=1 FOR UPDATE;
 SELECT * INTO c FROM lab.virtual_coupons WHERE idempotency_key=p_key;
 IF FOUND THEN IF c.decision_id<>p_decision OR c.rule_version<>p_rule OR c.total_cost_kurus<>p_cost THEN RAISE EXCEPTION 'idempotency_conflict';END IF;RETURN c.id;END IF;
 IF length(p_key)<8 OR p_cost IS NULL OR p_cost<=0 THEN RAISE EXCEPTION 'invalid_coupon_request'; END IF;
 IF NOT w.betting_enabled OR w.pilot_start IS NULL OR clock_timestamp()<w.pilot_start OR clock_timestamp()>=w.pilot_end THEN RAISE EXCEPTION 'pilot_disabled'; END IF;
 SELECT * INTO STRICT r FROM lab.coupon_rule_versions WHERE id=p_rule;
 SELECT * INTO STRICT d FROM lab.betting_decisions WHERE id=p_decision;
 IF NOT r.enabled OR r.mbs<>1 OR p_cost<r.minimum_cost_kurus OR p_cost>r.maximum_cost_kurus OR d.action<>'bet' OR p_cost>d.maximum_stake_kurus THEN RAISE EXCEPTION 'coupon_rule_or_risk_limit'; END IF;
 SELECT * INTO STRICT pr FROM lab.prediction_runs WHERE id=d.prediction_run_id;
 SELECT * INTO STRICT o FROM lab.odds_snapshots WHERE id=d.odds_id;
 SELECT * INTO STRICT m FROM lab.matches WHERE id=pr.fixture_id FOR UPDATE;
 IF pr.mode<>'prematch' OR o.match_id<>m.id OR m.status<>'scheduled' OR m.kickoff_at IS NULL OR m.kickoff_at<=clock_timestamp()+interval '5 minutes' OR o.observed_at>clock_timestamp() OR o.observed_at<clock_timestamp()-interval '15 minutes' OR o.source_updated_at<clock_timestamp()-interval '15 minutes' THEN RAISE EXCEPTION 'ineligible_or_stale_inputs'; END IF;
 IF NOT EXISTS(SELECT 1 FROM lab.fixture_contexts WHERE fixture_id=m.id AND score_target='regulation90' AND identity_status='verified') OR NOT EXISTS(SELECT 1 FROM lab.score_probability_distributions WHERE prediction_run_id=pr.id) THEN RAISE EXCEPTION 'unsupported_target_or_missing_distribution'; END IF;
 IF NOT EXISTS(SELECT 1 FROM lab.review_decisions rd JOIN lab.review_cycles rc ON rc.fixture_id=rd.fixture_id WHERE rd.id=d.review_decision_id AND rd.fixture_id=m.id AND rd.status='approved' AND rc.status='approved' AND rc.risk_action<>'skip' AND rd.round_no=rc.rounds) THEN RAISE EXCEPTION 'review_not_approved'; END IF;
 IF NOT EXISTS(SELECT 1 FROM lab.model_versions WHERE id=pr.model_version_id AND role='champion') THEN RAISE EXCEPTION 'no_eligible_champion'; END IF;
 IF NOT EXISTS(SELECT 1 FROM lab.sources WHERE id=o.source_id AND status='approved' AND review_expires>clock_timestamp()) OR NOT EXISTS(SELECT 1 FROM lab.raw_snapshots WHERE id=o.raw_snapshot_id AND source_id=o.source_id AND data_kind='real' AND received_at<=o.observed_at) THEN RAISE EXCEPTION 'invalid_odds_provenance'; END IF;
 IF EXISTS(SELECT 1 FROM lab.coupon_selections cs JOIN lab.virtual_coupons vc ON vc.id=cs.coupon_id WHERE cs.fixture_id=m.id AND vc.status='open') OR EXISTS(SELECT 1 FROM lab.paper_bets WHERE match_id=m.id AND status='open') THEN RAISE EXCEPTION 'duplicate_fixture_exposure'; END IF;
 IF w.balance_kurus<p_cost THEN RAISE EXCEPTION 'insufficient_funds'; END IF;
 INSERT INTO lab.virtual_coupons(idempotency_key,decision_id,rule_version,type,total_cost_kurus,columns,multiplier,budget_day,status)
 VALUES(p_key,d.id,r.id,'single',p_cost,1,1,(clock_timestamp() AT TIME ZONE 'Europe/Istanbul')::date,'open') RETURNING id INTO result;
 INSERT INTO lab.coupon_selections(coupon_id,fixture_id,prediction_run_id,odds_id,market,outcome,locked_odds) VALUES(result,m.id,pr.id,o.id,o.market,o.outcome,o.decimal_odds);
 UPDATE lab.paper_wallet SET balance_kurus=balance_kurus-p_cost WHERE id=1;
 INSERT INTO lab.wallet_ledger(coupon_id,event_key,kind,amount_kurus,balance_after_kurus,evidence) VALUES(result,'coupon-stake:'||p_key,'stake',-p_cost,w.balance_kurus-p_cost,jsonb_build_object('decision_id',d.id));
 RETURN result;
END $$;
-- Void settlement is the only implemented settlement; wins/losses/combinations are future work.
CREATE FUNCTION lab.settle_coupon_void(p_key text,p_coupon uuid,p_event uuid) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE w lab.paper_wallet%ROWTYPE;c lab.virtual_coupons%ROWTYPE;old lab.coupon_settlement_records%ROWTYPE;e lab.fixture_events%ROWTYPE;result uuid;debited bigint;
BEGIN
 PERFORM lab.assert_agent('risk_manager');
 SELECT * INTO STRICT w FROM lab.paper_wallet WHERE id=1 FOR UPDATE;
 SELECT * INTO old FROM lab.coupon_settlement_records WHERE coupon_id=p_coupon OR idempotency_key=p_key;
 IF FOUND THEN IF old.coupon_id<>p_coupon OR old.event_id<>p_event OR old.idempotency_key<>p_key THEN RAISE EXCEPTION 'idempotency_conflict'; END IF;RETURN old.id;END IF;
 SELECT * INTO STRICT c FROM lab.virtual_coupons WHERE id=p_coupon FOR UPDATE;
 SELECT * INTO STRICT e FROM lab.fixture_events WHERE id=p_event;
 SELECT -coalesce(sum(amount_kurus),0) INTO debited FROM lab.wallet_ledger WHERE coupon_id=c.id AND kind='stake';
 IF c.status<>'open' OR c.type<>'single' OR debited<>c.total_cost_kurus OR e.event_type<>'cancelled' OR e.quality<>'verified' OR NOT EXISTS(SELECT 1 FROM lab.coupon_selections WHERE coupon_id=c.id AND fixture_id=e.fixture_id) OR (SELECT count(*) FROM lab.coupon_selections WHERE coupon_id=c.id)<>1 THEN RAISE EXCEPTION 'unsupported_or_unfunded_settlement'; END IF;
 INSERT INTO lab.coupon_settlement_records(coupon_id,event_id,kind,payout_kurus,idempotency_key) VALUES(c.id,e.id,'void',c.total_cost_kurus,p_key) RETURNING id INTO result;
 UPDATE lab.virtual_coupons SET status='settled' WHERE id=c.id;
 UPDATE lab.paper_wallet SET balance_kurus=balance_kurus+c.total_cost_kurus WHERE id=1;
 INSERT INTO lab.wallet_ledger(coupon_id,event_key,kind,amount_kurus,balance_after_kurus,evidence) VALUES(c.id,'coupon-void:'||c.id,'settlement',c.total_cost_kurus,w.balance_kurus+c.total_cost_kurus,jsonb_build_object('event_id',e.id));
 RETURN result;
END $$;

-- Deny-by-default RLS and least privilege. No grants to anon/authenticated/service_role.
DO $$ DECLARE t record;name text;role_row record; BEGIN
 FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='lab' LOOP
  EXECUTE format('ALTER TABLE lab.%I ENABLE ROW LEVEL SECURITY',t.tablename);
  EXECUTE format('REVOKE ALL ON lab.%I FROM PUBLIC',t.tablename);
 END LOOP;
 FOREACH name IN ARRAY ARRAY['agent_roles','source_access_policies','source_dependencies','canonical_mappings','fixture_events','feature_snapshots','feature_snapshot_inputs','model_version_contracts','agent_runs','evidence_references','agent_messages','message_evidence','message_snapshots','review_findings','review_decisions','reanalysis_requests','prediction_runs','score_probability_distributions','champion_promotions','workflow_attempts','calibration_reports','ablation_results','source_performance','model_performance','coupon_rule_versions','betting_decisions','coupon_selections','coupon_settlement_records','integrity_exports','audit_events'] LOOP
  EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON lab.%I FOR EACH ROW EXECUTE FUNCTION lab.reject_mutation()',name);
 END LOOP;
 FOR role_row IN SELECT id FROM lab.agent_roles LOOP
  EXECUTE format('GRANT SELECT ON lab.agent_roles TO %I','lab_'||role_row.id);
  EXECUTE format('GRANT EXECUTE ON FUNCTION lab.start_agent_run(text,uuid,timestamptz,text),lab.post_agent_message(jsonb),lab.claim_workflow(text,text),lab.finish_workflow(uuid,uuid,text,text) TO %I','lab_'||role_row.id);
 END LOOP;
END $$;
CREATE POLICY roles_read ON lab.agent_roles FOR SELECT USING(true);
GRANT SELECT ON lab.prediction_runs,lab.score_probability_distributions,lab.review_decisions TO lab_dashboard;
CREATE POLICY dashboard_predictions ON lab.prediction_runs FOR SELECT TO lab_dashboard USING(true);
CREATE POLICY dashboard_distributions ON lab.score_probability_distributions FOR SELECT TO lab_dashboard USING(true);
CREATE POLICY dashboard_reviews ON lab.review_decisions FOR SELECT TO lab_dashboard USING(true);
GRANT EXECUTE ON FUNCTION lab.enqueue_workflow(text,text,uuid,jsonb,uuid[]) TO lab_coordinator;
GRANT EXECUTE ON FUNCTION lab.decide_review(text,uuid,uuid,uuid) TO lab_scientific_referee;
GRANT EXECUTE ON FUNCTION lab.reserve_source_request(text) TO lab_source_hunter;
GRANT EXECUTE ON FUNCTION lab.settle_coupon_void(text,uuid,uuid) TO lab_risk_manager;
GRANT EXECUTE ON FUNCTION lab.reserve_virtual_coupon(text,uuid,text,integer) TO lab_risk_manager;
GRANT EXECUTE ON FUNCTION lab.register_evidence(uuid,uuid,uuid,text,text,text,timestamptz) TO lab_data_validator;
GRANT EXECUTE ON FUNCTION lab.record_prediction(uuid,uuid,uuid,uuid,jsonb) TO lab_score_engine;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA lab FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA lab FROM PUBLIC;
COMMIT;
