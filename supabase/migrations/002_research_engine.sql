-- Additive phase 2 research schema. 001_lab.sql remains unchanged.
BEGIN;
CREATE TABLE lab.source_catalog (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_id text NOT NULL REFERENCES lab.sources,
 competition_key text NOT NULL, season_key text NOT NULL, discovered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 snapshot_id uuid NOT NULL REFERENCES lab.raw_snapshots, metadata jsonb NOT NULL,
 UNIQUE(source_id,competition_key,season_key,snapshot_id)
);
CREATE TABLE lab.collection_jobs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_id text NOT NULL REFERENCES lab.sources,
 kind text NOT NULL CHECK(kind IN ('discover','collect')), parameters jsonb NOT NULL,
 dedupe_key text NOT NULL UNIQUE, status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','running','done','failed','blocked')),
 attempts integer NOT NULL DEFAULT 0 CHECK(attempts>=0), not_before timestamptz NOT NULL DEFAULT clock_timestamp(),
 lease_until timestamptz, lease_token uuid, last_error text, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK((status='running')=(lease_until IS NOT NULL AND lease_token IS NOT NULL))
);
CREATE INDEX pending_jobs ON lab.collection_jobs(status,not_before);
CREATE TABLE lab.source_health (
 source_id text PRIMARY KEY REFERENCES lab.sources, successes integer NOT NULL DEFAULT 0 CHECK(successes>=0),
 failures integer NOT NULL DEFAULT 0 CHECK(failures>=0), consecutive_failures integer NOT NULL DEFAULT 0 CHECK(consecutive_failures>=0),
 last_success_at timestamptz,last_error_at timestamptz,last_error_code text
);
CREATE TABLE lab.normalization_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), snapshot_id uuid NOT NULL REFERENCES lab.raw_snapshots,
 parser_sha256 text NOT NULL CHECK(length(parser_sha256)=64), created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 accepted integer NOT NULL CHECK(accepted>=0),rejected integer NOT NULL CHECK(rejected>=0),
 UNIQUE(snapshot_id,parser_sha256)
);
CREATE TABLE lab.research_results (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), normalization_id uuid NOT NULL REFERENCES lab.normalization_runs,
 source_match_id text NOT NULL, competition text NOT NULL, season text NOT NULL, match_date date NOT NULL,
 home_name text NOT NULL,away_name text NOT NULL, neutral boolean,
 home_goals smallint CHECK(home_goals>=0), away_goals smallint CHECK(away_goals>=0),
 score_definition text NOT NULL CHECK(score_definition IN ('regulation90','final_including_extra_time','provider_final_unknown')),
 CHECK(home_name<>away_name),CHECK((home_goals IS NULL)=(away_goals IS NULL)),
 UNIQUE(normalization_id,source_match_id)
);
CREATE TABLE lab.dataset_manifests (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), dataset_sha256 text NOT NULL CHECK(length(dataset_sha256)=64),
 evaluation_mode text NOT NULL CHECK(evaluation_mode IN ('retrospective','point_in_time')),
 score_definition text NOT NULL, train_start date NOT NULL, train_end_exclusive date NOT NULL,
 validation_end_exclusive date NOT NULL, test_end_exclusive date NOT NULL,
 manifest jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(train_start<train_end_exclusive AND train_end_exclusive<validation_end_exclusive AND validation_end_exclusive<test_end_exclusive)
);
CREATE TABLE lab.research_model_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), dataset_id uuid NOT NULL REFERENCES lab.dataset_manifests,
 model_name text NOT NULL CHECK(model_name IN ('baseline','elo','poisson','dixon_coles')),
 code_sha256 text NOT NULL CHECK(length(code_sha256)=64), artifact_sha256 text NOT NULL CHECK(length(artifact_sha256)=64),
 artifact jsonb NOT NULL, training_end date NOT NULL, validation_metrics jsonb NOT NULL, test_metrics jsonb,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE lab.research_score_predictions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), model_run_id uuid NOT NULL REFERENCES lab.research_model_runs,
 match_ref text NOT NULL, match_date date NOT NULL, training_end date NOT NULL,
 home_name text NOT NULL, away_name text NOT NULL,
 home_rate double precision NOT NULL CHECK(home_rate>=0.02 AND home_rate<=8),
 away_rate double precision NOT NULL CHECK(away_rate>=0.02 AND away_rate<=8),
 rho double precision NOT NULL CHECK(rho>=-0.12 AND rho<=0.015),
 grid jsonb NOT NULL, tail_probability double precision NOT NULL CHECK(tail_probability>=0 AND tail_probability<=1),
 p_home double precision NOT NULL CHECK(p_home>=0 AND p_home<=1),
 p_draw double precision NOT NULL CHECK(p_draw>=0 AND p_draw<=1),
 p_away double precision NOT NULL CHECK(p_away>=0 AND p_away<=1),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(training_end<match_date),CHECK(abs(p_home+p_draw+p_away-1)<0.00000001),
 UNIQUE(model_run_id,match_ref)
);
CREATE FUNCTION lab.check_research_prediction() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,lab AS $$
DECLARE trained date; row_value jsonb; cell jsonb; mass double precision:=0; width integer:=NULL;
BEGIN
 SELECT training_end INTO trained FROM lab.research_model_runs WHERE id=NEW.model_run_id;
 IF trained IS NULL OR NEW.training_end<>trained THEN RAISE EXCEPTION 'model_training_cutoff_mismatch'; END IF;
 IF jsonb_typeof(NEW.grid)<>'array' OR jsonb_array_length(NEW.grid)<2 THEN RAISE EXCEPTION 'invalid_score_grid'; END IF;
 FOR row_value IN SELECT value FROM jsonb_array_elements(NEW.grid) LOOP
  IF jsonb_typeof(row_value)<>'array' THEN RAISE EXCEPTION 'invalid_score_grid'; END IF;
  IF width IS NULL THEN width:=jsonb_array_length(row_value); END IF;
  IF width<2 OR jsonb_array_length(row_value)<>width THEN RAISE EXCEPTION 'invalid_score_grid'; END IF;
  FOR cell IN SELECT value FROM jsonb_array_elements(row_value) LOOP
   IF jsonb_typeof(cell)<>'number' OR (cell::text)::double precision<0 OR (cell::text)::double precision>1 THEN RAISE EXCEPTION 'invalid_score_probability'; END IF;
   mass:=mass+(cell::text)::double precision;
  END LOOP;
 END LOOP;
 IF abs(mass+NEW.tail_probability-1)>0.00000001 THEN RAISE EXCEPTION 'score_grid_mass'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER research_prediction_valid BEFORE INSERT ON lab.research_score_predictions FOR EACH ROW EXECUTE FUNCTION lab.check_research_prediction();
-- This table intentionally has no actual-result columns. Labels stay research_results.
CREATE TABLE lab.external_score_forecasts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_id text NOT NULL REFERENCES lab.sources,
 raw_snapshot_id uuid NOT NULL REFERENCES lab.raw_snapshots, match_ref text NOT NULL,
 observed_at timestamptz NOT NULL DEFAULT clock_timestamp(), published_at timestamptz, kickoff_at timestamptz NOT NULL,
 selection text, probabilities jsonb, other_scores_probability double precision CHECK(other_scores_probability>=0 AND other_scores_probability<=1),
 verified_prematch boolean GENERATED ALWAYS AS (observed_at<kickoff_at AND (published_at IS NULL OR published_at<kickoff_at)) STORED,
 ensemble_weight double precision NOT NULL DEFAULT 0 CHECK(ensemble_weight=0),
 CHECK(selection IS NOT NULL OR probabilities IS NOT NULL),CHECK(published_at IS NULL OR published_at<=observed_at)
);

CREATE FUNCTION lab.claim_collection_job() RETURNS SETOF lab.collection_jobs
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
 WITH candidate AS (
  SELECT id FROM lab.collection_jobs
  WHERE (status='pending' AND not_before<=clock_timestamp()) OR (status='running' AND lease_until<clock_timestamp())
  ORDER BY not_before,id FOR UPDATE SKIP LOCKED LIMIT 1
 ) UPDATE lab.collection_jobs j SET status='running',lease_token=gen_random_uuid(),lease_until=clock_timestamp()+interval '5 minutes'
 FROM candidate c WHERE j.id=c.id RETURNING j.*;
$$;
CREATE FUNCTION lab.complete_collection_job(p_id uuid,p_token uuid,p_status text,p_error text DEFAULT NULL) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,lab AS $$
DECLARE n integer;
BEGIN
 IF p_status NOT IN ('done','failed','blocked','pending') THEN RAISE EXCEPTION 'invalid_terminal_status'; END IF;
 UPDATE lab.collection_jobs SET status=p_status,last_error=p_error,lease_until=NULL,lease_token=NULL
 WHERE id=p_id AND status='running' AND lease_token=p_token AND lease_until>clock_timestamp();
 GET DIAGNOSTICS n=ROW_COUNT;RETURN n=1;
END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['source_catalog','collection_jobs','source_health','normalization_runs','research_results','dataset_manifests','research_model_runs','research_score_predictions','external_score_forecasts'] LOOP
  EXECUTE format('ALTER TABLE lab.%I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('REVOKE ALL ON lab.%I FROM PUBLIC',t);
 END LOOP;
 FOREACH t IN ARRAY ARRAY['source_catalog','normalization_runs','research_results','dataset_manifests','research_model_runs','research_score_predictions','external_score_forecasts'] LOOP
  EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON lab.%I FOR EACH ROW EXECUTE FUNCTION lab.reject_mutation()',t);
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION lab.claim_collection_job() FROM PUBLIC;
REVOKE ALL ON FUNCTION lab.complete_collection_job(uuid,uuid,text,text) FROM PUBLIC;
COMMIT;
