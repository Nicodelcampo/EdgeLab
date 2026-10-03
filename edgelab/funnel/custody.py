"""Data custody: holdout guard and a ledger of date ranges whose OUTCOMES were already examined.

A funnel D2 that overlaps examined dates is not a clean confirmation set.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np


def forbid_holdout(trade_dates,first_holdout_date):
    """Raise if any trade date is at or after the holdout start. Call at every script entry."""
    td=np.asarray(trade_dates)
    if td.size and int(td.max())>=int(first_holdout_date):
        raise PermissionError(f'holdout touched: max trade_date {int(td.max())} >= {int(first_holdout_date)}')


class SeenLedger:
    """Which trade dates had outcomes looked at, and by which analysis."""
    def __init__(self,path):self.path=Path(path)
    def _rows(self):
        return [json.loads(x) for x in self.path.read_text().splitlines() if x.strip()] if self.path.exists() else []
    def mark(self,analysis_id,first_date,last_date,note=''):
        if int(first_date)>int(last_date):raise ValueError('first_date > last_date')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('a') as f:f.write(json.dumps({'analysis_id':analysis_id,'first_date':int(first_date),'last_date':int(last_date),'note':note})+'\n')
    def seen_mask(self,dates):
        d=np.asarray(dates);m=np.zeros(d.shape,bool)
        for r in self._rows():m|=(d>=r['first_date'])&(d<=r['last_date'])
        return m
    def contamination(self,split):
        """Fraction of each partition's dates already examined. D2 must be 0 for a clean confirmation."""
        out={}
        for part in('d0','d1','d2'):
            ds=np.asarray(getattr(split,part+'_dates'));out[part]=float(self.seen_mask(ds).mean()) if ds.size else 0.
        out['d2_clean']=out['d2']==0.
        return out
