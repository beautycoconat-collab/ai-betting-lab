import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engine.queue import Queue
from engine.hosted_quota import HostedQuotaGate,HostedQuotaUnavailable


POLICY={'openliga':{'status':'approved','license':'ODbL-1.0',
 'terms_url':'https://www.openligadb.de/lizenz','reviewed_at':'2026-10-01',
 'review_expires':'2026-11-13','requests_per_24h':4,'requests_per_31d':124,
 'min_interval_seconds':21600,'cache_seconds':0}}
NOW='2026-10-20T04:30:00+00:00'


class HostedQuotaTests(unittest.TestCase):
    def queue(self,reserver):
        d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup)
        q=Queue(Path(d.name)/'q.sqlite',POLICY,request_reserver=reserver)
        self.addCleanup(q.close)
        q.enqueue('openliga','collect',{'league':'bl1','season':'2026'},now=NOW,cycle='2026-10-20')
        return q

    def test_remote_denial_happens_before_http(self):
        calls=[]
        q=self.queue(lambda source:calls.append(('reserve',source)) or False)
        result=q.work_one(lambda url:calls.append(('http',url)) or (b'[]',{}),clock=lambda:NOW)
        self.assertEqual(result['status'],'deferred')
        self.assertEqual(result['reason'],'hosted_quota_denied')
        self.assertEqual(calls,[('reserve','openliga')])

    def test_remote_reservation_precedes_http(self):
        calls=[]
        q=self.queue(lambda source:calls.append(('reserve',source)) or True)
        result=q.work_one(lambda url:calls.append(('http',url)) or (b'[]',{}),clock=lambda:NOW)
        self.assertEqual(calls[0],('reserve','openliga'))
        self.assertEqual(calls[1][0],'http')
        self.assertEqual(result['status'],'failed')

    @patch('engine.hosted_quota.HostedQuotaGate._connect')
    @patch('engine.hosted_quota.settings')
    def test_gate_sets_worker_role_and_calls_only_reservation(self,config,connect):
        config.return_value={'host':'example'}
        cursor=connect.return_value.__enter__.return_value
        cursor.transaction.return_value.__enter__.return_value=None
        cursor.execute.side_effect=[None,type('R',(),{'fetchone':lambda self:(True,)})()]
        self.assertTrue(HostedQuotaGate({}).reserve('openliga'))
        self.assertEqual(cursor.execute.call_args_list[0].args[0],
                         'SET LOCAL ROLE lab_source_hunter')
        self.assertEqual(cursor.execute.call_args_list[1].args,
                         ('SELECT lab.reserve_source_request(%s)',('openliga',)))

    @patch('engine.hosted_quota.settings',side_effect=RuntimeError('down'))
    def test_gate_fails_closed_on_database_error(self,_):
        with self.assertRaisesRegex(HostedQuotaUnavailable,'hosted_quota_unavailable'):
            HostedQuotaGate({}).reserve('openliga')


if __name__=='__main__':unittest.main()
