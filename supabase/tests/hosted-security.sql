-- Actual hosted PostgreSQL probes. All temporary privilege grants roll back.
BEGIN;
DO $$
DECLARE r text; t text; cmd text; n bigint;
BEGIN
 IF EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace s ON s.oid=c.relnamespace WHERE s.nspname='lab' AND c.relkind='r' AND NOT c.relrowsecurity) THEN RAISE EXCEPTION 'RLS_missing'; END IF;
 IF EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace s ON s.oid=p.pronamespace WHERE s.nspname='lab' AND p.prosecdef AND NOT ('search_path=pg_catalog, lab, pg_temp'=ANY(coalesce(p.proconfig,'{}')))) THEN RAISE EXCEPTION 'unsafe_definer'; END IF;
 FOR r IN SELECT 'lab_'||id FROM lab.agent_roles LOOP
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=r AND (rolcanlogin OR rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb)) THEN RAISE EXCEPTION 'unsafe_worker'; END IF;
  FOREACH t IN ARRAY ARRAY['predictions','prediction_runs','review_decisions','paper_wallet','wallet_ledger'] LOOP
   IF has_table_privilege(r,'lab.'||t,'INSERT,UPDATE,DELETE') THEN RAISE EXCEPTION 'worker_direct_write'; END IF;
  END LOOP;
 END LOOP;
 FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
  IF has_schema_privilege(r,'lab','USAGE') OR has_function_privilege(r,'lab.post_agent_message(jsonb)','EXECUTE') THEN RAISE EXCEPTION 'browser_access'; END IF;
 END LOOP;
 FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
  EXECUTE format('SET LOCAL ROLE %I',r);
  FOREACH cmd IN ARRAY ARRAY['UPDATE lab.paper_wallet SET balance_kurus=1','DELETE FROM lab.predictions','DELETE FROM lab.review_decisions','UPDATE lab.wallet_ledger SET amount_kurus=1','SELECT lab.post_agent_message(''{}'')'] LOOP
   BEGIN
    EXECUTE cmd;
    RAISE EXCEPTION 'unauthorized_operation_allowed';
   EXCEPTION WHEN insufficient_privilege THEN NULL;
   END;
  END LOOP;
  RESET ROLE;
 END LOOP;
 -- Separate RLS from ACL: temporary grants disappear at ROLLBACK.
 GRANT USAGE ON SCHEMA lab TO authenticated;
 GRANT SELECT,UPDATE ON lab.paper_wallet TO authenticated;
 SET LOCAL ROLE authenticated;
 SELECT count(*) INTO n FROM lab.paper_wallet;
 IF n<>0 THEN RAISE EXCEPTION 'rls_wallet_leak'; END IF;
 UPDATE lab.paper_wallet SET balance_kurus=1;
 GET DIAGNOSTICS n=ROW_COUNT;
 IF n<>0 THEN RAISE EXCEPTION 'rls_wallet_write'; END IF;
 RESET ROLE;
 SET LOCAL ROLE lab_red_team;
 BEGIN
  PERFORM lab.record_prediction(gen_random_uuid(),gen_random_uuid(),gen_random_uuid(),gen_random_uuid(),'{}');
  RAISE EXCEPTION 'numeric_override_allowed';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
 BEGIN
  PERFORM lab.start_agent_run('score_engine',gen_random_uuid(),now(),'prematch');
  RAISE EXCEPTION 'role_spoof_allowed';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'agent_permission_denied' THEN RAISE; END IF;
 END;
 RESET ROLE;
 BEGIN
  UPDATE lab.wallet_ledger SET amount_kurus=1;
  RAISE EXCEPTION 'ledger_mutation_allowed';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM NOT LIKE '%append_only%' THEN RAISE; END IF;
 END;
 IF NOT EXISTS(SELECT 1 FROM lab.paper_wallet WHERE balance_kurus=100000 AND NOT betting_enabled AND pilot_start IS NULL) THEN RAISE EXCEPTION 'wallet_or_pilot_changed'; END IF;
END $$;
ROLLBACK;
SELECT 'passed' AS hosted_security, 'temporary_grants_rolled_back' AS isolation,
 (SELECT count(*) FROM lab.agent_roles) AS roles,
 (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='lab' AND c.relkind='r' AND c.relrowsecurity) AS rls_tables;
