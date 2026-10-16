import tempfile
import unittest
from pathlib import Path
from experts.multiseason import snapshot_rows


class SnapshotTests(unittest.TestCase):
    def test_real_preserved_source_hash_and_season(self):
        rows,rejected=snapshot_rows()
        self.assertEqual(len(rows),306)
        self.assertEqual(rejected,{'rejected':0})
        self.assertEqual({r['season'] for r in rows},{'2025-26'})
        self.assertEqual(len({r['id'] for r in rows}),306)

    def test_tampered_raw_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'raw.json'; p.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'snapshot_hash_mismatch'):
                snapshot_rows(p)
