#!/usr/bin/env python3
"""Invented offline tape demonstration; no input path or market execution mode."""
from __future__ import annotations
import json
from edgelab.kaggle.avzvol_detector_tape import (
    synthetic_fixture, replay_declared_detector, legacy_parameters,
)
from edgelab.kaggle.avzvol_zone_negative import classify_detector_window


def smoke():
    import pandas as pd
    b,f,s=synthetic_fixture(22,3)
    tape=replay_declared_detector(b,f,s,params=legacy_parameters(),
        holdout_start='2026-10-01',utc_cutoff_ns=int(pd.Timestamp('2026-09-30T22:00Z').value))
    counts={k:0 for k in ('DETECTOR_NEGATIVE','DETECTED_ZONE','UNKNOWN')}
    for record in tape['observations']:
        row=record['observation']
        decision=classify_detector_window([row],session=row['session'],
            session_first_bar=record['session_first_bar'],
            window_first_bar=record['block_first_bar'],anchor_bar=row['block_end_bar'],
            holdout_start='2026-10-01',block_bars=10,minimum_calibration_samples=20)
        counts[decision['classification']]+=1
    if counts!={'DETECTOR_NEGATIVE':0,'DETECTED_ZONE':2,'UNKNOWN':20}:
        raise RuntimeError('invented reference classification mismatch')
    if len(tape['zone_creation_snapshots'])!=2 or len(tape['incomplete_session_tails'])!=1:
        raise RuntimeError('invented reference tape mismatch')
    return {'status':'PASS_SYNTHETIC_SOFTWARE_ONLY','fixture_is_invented':True,
        'complete_blocks':len(tape['observations']),'classifications':counts,
        'incomplete_tails_retained':len(tape['incomplete_session_tails']),
        'market_sources_opened':False,'market_census_built':False,
        'outcomes_computed':False,'source_quality_certified':False}

if __name__=='__main__':
    print(json.dumps(smoke(),sort_keys=True))
