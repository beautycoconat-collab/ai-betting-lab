-- Additive hardening. 001, 002 and 003 remain byte-identical.
BEGIN;
-- pg_temp must be LAST, rather than implicitly searched before trusted schemas.
DO $$ DECLARE f record; r text; BEGIN
 FOR f IN SELECT p.oid::regprocedure AS signature FROM pg_proc p
 JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='lab' AND p.prosecdef LOOP
  EXECUTE format('ALTER FUNCTION %s SET search_path=pg_catalog,lab,pg_temp',f.signature);
 END LOOP;
 FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=r) THEN
   EXECUTE format('REVOKE ALL ON SCHEMA lab FROM %I',r);
   EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA lab FROM %I',r);
   EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA lab FROM %I',r);
   EXECUTE format('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA lab FROM %I',r);
   EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA lab REVOKE ALL ON TABLES FROM %I',r);
   EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA lab REVOKE ALL ON FUNCTIONS FROM %I',r);
  END IF;
 END LOOP;
END $$;
REVOKE ALL ON SCHEMA lab FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA lab FROM PUBLIC;
COMMIT;
