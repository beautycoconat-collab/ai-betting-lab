import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import Mock,patch
from cloudcheck.capacity import decision,guarded_call,collect
from cloudcheck.config import settings,ConfigError

NOW=datetime(2026,10,15,tzinfo=timezone.utc)
def sample():
    return dict(observed_at=NOW.isoformat(),plan='free',billing_scope='organization',database_bytes=100,storage_bytes=100,egress_bytes=100,connection_ratio=.1)

class Capacity(unittest.TestCase):
    def test_good(self):self.assertTrue(decision(sample(),NOW)['allowed'])
    def test_missing(self):self.assertFalse(decision({},NOW)['allowed'])
    def test_stale(self):self.assertFalse(decision(sample(),NOW+timedelta(minutes=16))['allowed'])
    def test_future(self):self.assertFalse(decision(sample(),NOW-timedelta(seconds=1))['allowed'])
    def test_naive(self):
        x=sample();x['observed_at']='2026-10-15T00:00:00';self.assertFalse(decision(x,NOW)['allowed'])
    def test_paid(self):
        x=sample();x['plan']='pro';self.assertFalse(decision(x,NOW)['allowed'])
    def test_project_not_org(self):
        x=sample();x['billing_scope']='project';self.assertFalse(decision(x,NOW)['allowed'])
    def test_exact_limit(self):
        x=sample();x['database_bytes']=400_000_000;self.assertFalse(decision(x,NOW)['allowed'])
    def test_invalid_metric(self):
        for value in [None,True,float('nan'),float('inf'),-1,'100']:
            x=sample();x['egress_bytes']=value;self.assertFalse(decision(x,NOW)['allowed'])
    def test_gate_stops_operation(self):
        operation=Mock();guarded_call({},operation,NOW);operation.assert_not_called()
    def test_gate_calls_once(self):
        operation=Mock(return_value=5);self.assertEqual(guarded_call(sample(),operation,NOW),5);operation.assert_called_once()
    def test_live_query_unknown_org(self):
        db=Mock();db.execute.side_effect=[Mock(fetchone=Mock(return_value=(1234,2,100))),Mock(fetchone=Mock(return_value=(None,)))]
        result=collect(db);self.assertEqual(result['database_bytes'],1234);self.assertFalse(decision(result)['allowed'])

class Configuration(unittest.TestCase):
    def test_missing_environment(self):
        with self.assertRaises(ConfigError):settings('hosted',{})
    def test_native_binding(self):
        env={'LAB_DISPOSABLE_TEST_PROJECT':'1','LAB_TEST_DSN':'host=localhost dbname=ai_betting_lab_test_ci','LAB_EXPECTED_DB_HOST':'localhost'}
        self.assertEqual(settings('native',env)['connect_timeout'],10)
    def test_native_reject_remote(self):
        env={'LAB_DISPOSABLE_TEST_PROJECT':'1','LAB_TEST_DSN':'host=example.com dbname=ai_betting_lab_test_ci','LAB_EXPECTED_DB_HOST':'example.com'}
        with self.assertRaises(ConfigError):settings('native',env)
    def test_native_reject_production_name(self):
        env={'LAB_DISPOSABLE_TEST_PROJECT':'1','LAB_TEST_DSN':'host=localhost dbname=production','LAB_EXPECTED_DB_HOST':'localhost'}
        with self.assertRaises(ConfigError):settings('native',env)
    def test_host_mismatch(self):
        env={'LAB_DISPOSABLE_TEST_PROJECT':'1','LAB_TEST_DSN':'host=localhost dbname=ai_betting_lab_test_ci','LAB_EXPECTED_DB_HOST':'127.0.0.1'}
        with self.assertRaises(ConfigError):settings('native',env)
    def test_invalid_dsn_redacted(self):
        env={'LAB_DISPOSABLE_TEST_PROJECT':'1','LAB_TEST_DSN':'SECRET_BAD_DSN','LAB_EXPECTED_DB_HOST':'localhost'}
        with self.assertRaisesRegex(ConfigError,'^invalid_dsn$'):settings('native',env)
    def test_hostaddr_bypass(self):
        env={'LAB_DISPOSABLE_TEST_PROJECT':'1','LAB_TEST_DSN':'host=localhost hostaddr=8.8.8.8 dbname=ai_betting_lab_test_ci','LAB_EXPECTED_DB_HOST':'localhost'}
        with self.assertRaises(ConfigError):settings('native',env)

class HostedProtocol(unittest.TestCase):
    # Mocked unit tests; NEVER evidence of a hosted run.
    def run_auth(self,replies):
        from cloudcheck.runner import hosted_auth
        with patch.dict('os.environ',{'LAB_TEST_PROJECT_REF':'a'*20,'LAB_SUPABASE_ANON_KEY':'SYNTHETIC','LAB_AUTH_JWT':'SYNTHETIC'}),patch('cloudcheck.runner.http',side_effect=replies):
            return hosted_auth()
    def test_valid_auth_then_denials(self):
        self.assertEqual(self.run_auth([(200,{'id':'test'}),(200,{})]+[(406,{'code':'PGRST106'})]*6),6)
    def test_invalid_jwt_is_failure(self):
        with self.assertRaises(AssertionError):self.run_auth([(401,{})])
    def test_invalid_anon_key_is_failure(self):
        with self.assertRaises(AssertionError):self.run_auth([(200,{'id':'test'}),(401,{})])
    def test_successful_write_is_failure(self):
        with self.assertRaises(AssertionError):self.run_auth([(200,{'id':'test'}),(200,{}),(200,{})])
    def test_unrelated_api_error_not_pass(self):
        with self.assertRaises(AssertionError):self.run_auth([(200,{'id':'test'}),(200,{}),(404,{'code':'PGRST205'})])

if __name__=='__main__':unittest.main()
