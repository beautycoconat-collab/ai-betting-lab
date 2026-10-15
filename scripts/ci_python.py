"""Run all available tests; explicitly skip absent large release artifacts."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
suite=unittest.TestSuite()
for folder in ('tests','tests_phase2','tests_foundation','tests_cloud'):
    discovered=unittest.TestLoader().discover(str(ROOT/folder),top_level_dir=str(ROOT/folder))
    def add(node):
        if isinstance(node,unittest.TestSuite):
            for child in node:add(child)
        else:
            if node.__class__.__name__=='RealEvidence' and not (ROOT/'evidence/phase2/raw/international.zip').exists():
                node.__class__.__unittest_skip__=True
                node.__class__.__unittest_skip_why__='Full historical release artifacts are in the delivered ZIP; not uploaded to source repository.'
            suite.addTest(node)
    add(discovered)
if __name__=='__main__':raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
