-- Supabase postgres is managed, not a PostgreSQL superuser.
-- Creating NOLOGIN roles does not necessarily give the migration runner SET ROLE.
-- Only the trusted migration owner receives worker membership; no browser role.
BEGIN;
DO $$ DECLARE r record; BEGIN
 IF current_user<>'postgres' THEN RAISE EXCEPTION 'requires_migration_owner'; END IF;
 FOR r IN SELECT 'lab_'||id AS role_name FROM lab.agent_roles
 UNION ALL SELECT 'lab_dashboard' LOOP
  EXECUTE format('GRANT %I TO postgres',r.role_name);
 END LOOP;
END $$;
COMMIT;
