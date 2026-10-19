import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest
from edgelab.kaggle.avzvol_design import AVZVOLDesignError, FEATURES, plan_covariate_matches

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('avzvol_smoke', ROOT/'tools/avzvol_design_smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)

class DesignTests(unittest.TestCase):
    def setUp(self):
        self.r, self.c, self.p = smoke.synthetic_fixture()
    def run_plan(self):
        return plan_covariate_matches(self.r, self.c, policy=self.p, holdout_start='2026-10-01')
    def test_weights_and_unsupported_retained(self):
        d=self.run_plan()
        self.assertEqual(d['matched_real_event_count'], 1)
        self.assertEqual(d['unsupported_real_event_count'], 1)
        self.assertAlmostEqual(math.fsum(x['analysis_weight'] for x in d['pairs']), 1.)
        self.assertEqual(d['groups'][1]['controls_used'], 0)
        self.assertFalse(d['balance_accepted'])
    def test_shuffle_invariant(self):
        a=self.run_plan();self.r.reverse();self.c.reverse()
        self.assertEqual(a,self.run_plan())
    def test_tie_uses_stable_id(self):
        self.c[1]['features']=copy.deepcopy(self.c[0]['features']);self.p['max_controls']=1
        self.assertEqual(self.run_plan()['pairs'][0]['control_id'],'SYNTHETIC-C1')
    def test_duplicate_ids_fail(self):
        self.c.append(copy.deepcopy(self.c[0]))
        with self.assertRaises(AVZVOLDesignError):self.run_plan()
    def test_cross_census_id_collision_fails(self):
        self.c[0]['event_id']=self.r[0]['event_id']
        with self.assertRaises(AVZVOLDesignError):self.run_plan()
    def test_real_anchor_not_control(self):
        for key in ('anchor_utc','feature_asof_utc'):self.c[0][key]=self.r[0][key]
        self.assertEqual(len(self.run_plan()['pairs']),1)
    def test_minimum_support_no_relaxation(self):
        self.p['min_controls']=2;self.c[1]['features']['occ']=10.
        d=self.run_plan();self.assertEqual(d['pairs'],[])
        self.assertTrue(all(v is None for v in d['mean_covariate_gap_in_frozen_scale_units'].values()))
    def test_same_strata_required(self):
        for key,value in [('contract','OTHER'),('session','2026-01-06'),('cell','OTHER'),('clock_bucket','OTHER'),('trend_sign',-1)]:
            with self.subTest(key=key):
                c=copy.deepcopy(self.c);c[0][key]=value;c[1][key]=value
                d=plan_covariate_matches(self.r,c,policy=self.p,holdout_start='2026-10-01')
                self.assertEqual(d['pairs'],[])
    def test_no_future_features(self):
        self.c[0]['feature_asof_utc']='2026-01-05T15:11:00Z'
        with self.assertRaises(AVZVOLDesignError):self.run_plan()
    def test_bad_timestamps(self):
        for stamp in ('bad','2026-01-05T15:10:00','2026-01-05T15:10:00-03:00'):
            with self.subTest(stamp=stamp):
                c=copy.deepcopy(self.c);c[0]['anchor_utc']=stamp
                with self.assertRaises(AVZVOLDesignError):plan_covariate_matches(self.r,c,policy=self.p,holdout_start='2026-10-01')
    def test_reserved_trade_date(self):
        self.c[0]['session']='2026-10-01'
        with self.assertRaises(AVZVOLDesignError):self.run_plan()
    def test_reserved_anchor(self):
        self.c[0]['anchor_utc']='2026-10-01T00:00:00Z'
        with self.assertRaises(AVZVOLDesignError):self.run_plan()
    def test_invalid_values_not_imputed(self):
        for v in (None,True,float('nan'),float('inf'),'1'):
            with self.subTest(v=v):
                c=copy.deepcopy(self.c);c[0]['features']['occ']=v
                with self.assertRaises(AVZVOLDesignError):plan_covariate_matches(self.r,c,policy=self.p,holdout_start='2026-10-01')
    def test_outcome_field_rejected(self):
        self.c[0]['O5']=-.1
        with self.assertRaises(AVZVOLDesignError):self.run_plan()
    def test_incomplete_window_stops_not_drops(self):
        self.c[0]['prewindow_complete']=False
        with self.assertRaises(AVZVOLDesignError):self.run_plan()
    def test_missing_or_bad_policy(self):
        for change in ('missing','zero_scale','negative_caliper','bad_count'):
            with self.subTest(change=change):
                p=copy.deepcopy(self.p)
                if change=='missing':del p['calipers']['occ']
                elif change=='zero_scale':p['scales']['occ']=0
                elif change=='negative_caliper':p['calipers']['occ']=-1
                else:p['min_controls']=True
                with self.assertRaises(AVZVOLDesignError):plan_covariate_matches(self.r,self.c,policy=p,holdout_start='2026-10-01')
    def test_reuse_explicit_equal_real_weights(self):
        self.r[1]['features']=copy.deepcopy(self.r[0]['features']);self.p['max_controls']=1
        d=self.run_plan();self.assertEqual(d['control_reuse_counts'],{'SYNTHETIC-C1':2})
        self.assertEqual([p['real_weight'] for p in d['pairs']],[.5,.5])
        self.assertNotEqual(d['pairs'][0]['pair_id'],d['pairs'][1]['pair_id'])
    def test_pair_id_changes_with_policy(self):
        a=self.run_plan()['pairs'][0]['pair_id'];self.p['calipers']['occ']=.4
        self.assertNotEqual(a,self.run_plan()['pairs'][0]['pair_id'])
    def test_pair_and_input_digest_change_with_declared_covariates(self):
        a=self.run_plan();self.c[0]['features']['vol_100']=1.15
        b=self.run_plan()
        self.assertNotEqual(a['declared_input_sha256'],b['declared_input_sha256'])
        self.assertNotEqual(a['pairs'][0]['pair_id'],b['pairs'][0]['pair_id'])
    def test_separation_enforced(self):
        self.p['minimum_separation_seconds']=10000
        self.assertEqual(self.run_plan()['pairs'],[])
    def test_negative_finite_log_covariates_allowed(self):
        for row in self.r+self.c:row['features']={f:-1. for f in FEATURES}
        self.assertEqual(self.run_plan()['matched_real_event_count'],2)
    def test_no_outcomes_or_authority(self):
        d=self.run_plan()
        for k in ('research_authorized','outcomes_read','pnl_computed','bias_adjudicated','inference_implemented','source_quality_certified','census_completeness_verified'):self.assertFalse(d[k])
        self.assertEqual(set(d['candidate_census_ids']),{x['event_id'] for x in self.c})
    def test_research_cli_stops_before_fixture(self):
        from unittest.mock import patch
        with patch.object(smoke,'synthetic_fixture',side_effect=AssertionError('must not load')):
            self.assertEqual(smoke.main(['--purpose','research']),2)
    def test_cli_synthetic(self):
        run=subprocess.run([sys.executable,str(ROOT/'tools/avzvol_design_smoke.py')],capture_output=True,text=True,cwd=ROOT,env={**os.environ, 'PYTHONPATH': str(ROOT)})
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn('SYNTHETIC_ONLY',json.loads(run.stdout)['fixture'])


class DesignDocumentTests(unittest.TestCase):
    def test_proposal_is_blocked_and_preserves_denominator(self):
        p=json.loads((ROOT/'specs/research/avzvol_incremental_design_v1.json').read_text())
        self.assertEqual(p['status'],'BLOCKED_FOR_MARKET_EXECUTION')
        self.assertFalse(p['research_authorized'])
        self.assertIn('before the first zone',p['primary_endpoint']['definition'])
        for key in ('match_policy','support_acceptance_threshold','balance_acceptance_thresholds','minimum_material_effect','clock_horizons_seconds','formal_family_and_budget','reviewed_input_pins','approved_windows_and_holdout','control_census_selection_rule','censoring_and_session_boundary_policy'):
            self.assertIsNone(p[key],key)
        self.assertEqual(p['inference']['implementation'],'NOT IMPLEMENTED')
    def test_episode_not_promoted_or_ingested(self):
        p=json.loads((ROOT/'config/research/avzvol_design_episode_20261010.json').read_text())
        self.assertEqual(p['status'],'PROPOSED');self.assertEqual(p['confidence'],'LOW')
        self.assertFalse(p['ingested_into_hippocampus']);self.assertEqual(p['new_market_trials_executed'],0)
    def test_local_document_links(self):
        import re
        path=ROOT/'docs/research/AVZVOL_SIGUIENTE_ETAPA_20261010.md'
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if '://' not in link and not link.startswith('#'):
                self.assertTrue((path.parent/link.split('#')[0]).exists(),link)

if __name__=='__main__':unittest.main()
