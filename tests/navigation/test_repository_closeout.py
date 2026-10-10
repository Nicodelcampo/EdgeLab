"""Frozen inventory/navigation consistency, never market-data certification."""
import collections
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]

class RepositoryCloseoutTests(unittest.TestCase):
    def setUp(self):
        self.inventory = json.loads((ROOT / 'config/repository_inventory_20261010.json').read_text())
        self.doc = (ROOT / 'docs/ESTADO_Y_PENDIENTES.md').read_text()

    def test_exhaustive_snapshot_counts_and_unique_refs(self):
        p = self.inventory
        self.assertTrue(p['history_complete'])
        self.assertTrue(p['branch_listing_exhaustive'])
        self.assertTrue(p['open_pr_listing_exhaustive'])
        self.assertEqual(len(p['branches']), p['branch_count'])
        self.assertEqual(len({b['branch'] for b in p['branches']}), p['branch_count'])
        self.assertEqual(len(p['open_pull_requests']), p['open_pr_count'])
        self.assertEqual(len({x['number'] for x in p['open_pull_requests']}), p['open_pr_count'])
        self.assertEqual(sum(x['draft'] for x in p['open_pull_requests']), p['draft_pr_count'])

    def test_no_blanket_readiness_or_pc_inventory(self):
        p = self.inventory
        self.assertFalse(p['semantic_review_complete'])
        self.assertTrue(p['observation_excludes_closeout_pr'])
        self.assertEqual(p['ready_to_merge_to_main_verified'], [])
        self.assertTrue(all(not b['scientific_readiness_verified'] for b in p['branches']))
        self.assertIn('no pusheada', self.doc)

    def test_every_pr_has_documented_destination(self):
        for x in self.inventory['open_pull_requests']:
            self.assertIn(f"[#{x['number']}]({x['html_url']})", self.doc)
            self.assertIn(f"`{x['base']['ref']}`", self.doc)
            self.assertRegex(x['head']['sha'], r'^[a-f0-9]{40}$')
            self.assertRegex(x['observed_live_target_sha'], r'^[a-f0-9]{40}$')

    def test_snapshot_base_and_branch_categories(self):
        for key in ('main_sha', 'foundation_sha'):
            self.assertIn(self.inventory[key], self.doc)
        for kind, amount in collections.Counter(b['disposition'] for b in self.inventory['branches']).items():
            self.assertIn(f'`{kind}`: **{amount}**', self.doc)

    def test_all_pinned_datasets_are_named(self):
        discovery = json.loads((ROOT / 'edgelab/kaggle/discovery.json').read_text())
        for dataset in discovery['datasets']:
            self.assertIn(dataset['version_ref'], self.doc)
        self.assertIn('NO hay release ES/NQ certificado', self.doc)
        self.assertIn('sin fallback silencioso', self.doc)

    def test_local_links_resolve(self):
        for label, link in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', self.doc):
            if '://' in link or link.startswith('#'):
                continue
            self.assertTrue((ROOT / 'docs' / link.split('#')[0]).exists(), (label, link))

    def test_front_doors_link_to_current_status(self):
        for filename in ('README.md', 'AGENTS.md', 'docs/START_HERE.md', 'docs/INTEGRATION_PLAN.md', 'docs/KAGGLE_START_HERE.md'):
            self.assertIn('ESTADO_Y_PENDIENTES.md', (ROOT / filename).read_text())

if __name__ == '__main__':
    unittest.main()
