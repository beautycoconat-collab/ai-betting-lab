"""Environment-only secrets, explicit target binding, TLS required for cloud."""
import os
import re
from pathlib import Path

class ConfigError(ValueError):
    pass

def settings(mode, env=None, require_auth=True):
    env = os.environ if env is None else env
    required = ['LAB_TEST_DSN', 'LAB_EXPECTED_DB_HOST']
    if mode == 'hosted':
        required += ['LAB_TEST_PROJECT_REF', 'LAB_SSLROOTCERT']
        if require_auth:required += ['LAB_SUPABASE_ANON_KEY', 'LAB_AUTH_JWT']
    if env.get('LAB_DISPOSABLE_TEST_PROJECT') != '1' or any(not env.get(k) for k in required):
        raise ConfigError('missing_test_configuration')
    import psycopg.conninfo
    try:
        params = psycopg.conninfo.conninfo_to_dict(env['LAB_TEST_DSN'])
    except Exception:
        raise ConfigError('invalid_dsn') from None
    if params.get('host') != env['LAB_EXPECTED_DB_HOST'] or ',' in params.get('host', ''):
        raise ConfigError('database_host_mismatch')
    if any(params.get(key) for key in ('hostaddr','service')) or env.get('PGHOSTADDR') or env.get('PGSERVICE'):
        raise ConfigError('alternate_connection_target_forbidden')
    if mode == 'hosted':
        ref = env['LAB_TEST_PROJECT_REF']
        if not re.fullmatch('[a-z0-9]{20}', ref):
            raise ConfigError('invalid_test_project_ref')
        direct = params['host'] == 'db.' + ref + '.supabase.co'
        pooler = params['host'].endswith('.pooler.supabase.com') and params.get('user') == 'postgres.' + ref
        if not (direct or pooler) or params.get('port', '5432') != '5432':
            raise ConfigError('requires_bound_direct_or_session_connection')
        if params.get('dbname') != 'postgres' or not Path(env['LAB_SSLROOTCERT']).is_file():
            raise ConfigError('requires_database_and_ca')
        params.update(sslmode='verify-full', sslrootcert=env['LAB_SSLROOTCERT'])
    else:
        if params['host'] not in ('localhost', '127.0.0.1') or not params.get('dbname', '').startswith('ai_betting_lab_test'):
            raise ConfigError('native_requires_local_disposable_database')
    params.update(connect_timeout=10, application_name='ai_lab_validation', options='-c statement_timeout=15000 -c lock_timeout=5000')
    return params
