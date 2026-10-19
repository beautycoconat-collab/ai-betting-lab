import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from dashboard.scheduled_gate import evaluate, REQUIRED_TABLES

ENV = {'LAB_RESEARCH_ACCEPTED':'true','LAB_DURABLE_QUOTA_VERIFIED':'true',
       'LAB_HOSTED_SECURITY_ACCEPTED':'true'}
NOW = datetime(2026,10,19,12,tzinfo=timezone.utc)

class ScheduledGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root/'acceptance.json'
        self.db = self.root/'state.sqlite'
        self.manifest.write_text('{}')

    def gate(self, env=None):
        return evaluate(manifest_path=self.manifest,db_path=self.db,
                        env=ENV if env is None else env,now=NOW)

    def test_empty_state_blocks(self):
        result=self.gate()
        self.assertEqual(result['status'],'blocked')
        self.assertIn('durable_database_missing',result['reasons'])
        self.assertFalse(result['portfolio_enabled'])

    def test_empty_database_not_sufficient(self):
        sqlite3.connect(self.db).close()
        self.assertIn('durable_database_missing',self.gate()['reasons'])

    def test_missing_quota_tables_blocks(self):
        with sqlite3.connect(self.db) as con:con.execute('CREATE TABLE unrelated (x INTEGER)')
        self.assertIn('missing_table_requests',self.gate()['reasons'])

    def test_env_is_not_enough_even_with_db(self):
        with sqlite3.connect(self.db) as con:
            for table in REQUIRED_TABLES:con.execute(f'CREATE TABLE {table} (x INTEGER)')
        self.assertEqual(self.gate()['status'],'blocked')

    def test_all_checks_and_tables_ready(self):
        with sqlite3.connect(self.db) as con:
            for table in REQUIRED_TABLES:con.execute(f'CREATE TABLE {table} (x INTEGER)')
        with patch('dashboard.scheduled_gate.inspect',return_value={'status':'review_ready','missing':[]}):
            self.assertEqual(self.gate()['status'],'ready')
            self.assertEqual(self.gate({'LAB_RESEARCH_ACCEPTED':'true'})['status'],'blocked')

    def test_no_db_created_by_gate(self):
        self.gate()
        self.assertFalse(self.db.exists())

    def test_manifest_is_not_logged(self):
        self.manifest.write_text('{"token":"SUPER_SECRET"}')
        self.assertNotIn('SUPER_SECRET',json.dumps(self.gate()))

if __name__ == '__main__': unittest.main()
