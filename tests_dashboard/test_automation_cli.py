import unittest
from unittest.mock import patch, MagicMock
from dashboard.automation_cli import main

class CliTests(unittest.TestCase):
    def test_main_exits_nonzero_for_partial(self):
        with patch('dashboard.automation_cli.execute',return_value={'status':'partial'}), \
             patch('sys.argv',['cli','--database','/tmp/nonexistent-db']), \
             patch('builtins.print'):
            with self.assertRaises(SystemExit) as caught:
                main()
            self.assertEqual(caught.exception.code,2)

    def test_main_success(self):
        with patch('dashboard.automation_cli.execute',return_value={'status':'done'}), \
             patch('sys.argv',['cli']), patch('builtins.print'):
            main()

if __name__ == '__main__': unittest.main()

class PublicationGateTests(unittest.TestCase):
    def test_partial_never_replaces_public_dashboard(self):
        import importlib.util
        if importlib.util.find_spec("foundation") is None:
            self.skipTest("Full repository required for integration test")
        import tempfile
        from pathlib import Path
        from unittest.mock import patch, MagicMock
        from dashboard.automation_cli import execute
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'dashboard.json'
            output.write_text('PREVIOUS_VERIFIED_PUBLICATION')
            runtime = MagicMock()
            runtime.db.execute.return_value = []
            runtime.queue.registry = {}
            runtime.queue.work_one.return_value = None
            orchestrator = MagicMock()
            orchestrator.run.return_value = {'status':'partial'}
            with patch('foundation.runtime.Runtime',return_value=runtime), \
                 patch('experts.result_scheduler.ResultScheduler'), \
                 patch('dashboard.daily.run',return_value={'fixtures':[], 'connection':'verified_source_worker'}), \
                 patch('dashboard.automation_cli.DailyOrchestrator',return_value=orchestrator):
                result=execute(Path(d)/'db.sqlite',output)
            self.assertEqual(result['status'],'partial')
            self.assertEqual(output.read_text(),'PREVIOUS_VERIFIED_PUBLICATION')
