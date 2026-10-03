"""EF3/EF4: plateau, global trial counter and max-statistic null with randomized direction.

Everything here is screening-level (bar OHLC, independent signals) and never evidentiary on its own.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np


def candidate_statistic(d0_mean,d1_mean):
    """Same criterion the runner uses to pick a family headline: min(D0,D1) minus their gap."""
    return min(d0_mean,d1_mean)-abs(d0_mean-d1_mean)


def plateau_report(nets,grid,key,min_positive_fraction=2/3,min_median_ratio=.5):
    """Is the headline cell inside a stable region of the (sl,tp) grid, or an isolated spike?

    nets: {(sl,tp): value}. grid: (sorted sl values, sorted tp values). key: headline (sl,tp).
    Neighbours are the 8 adjacent grid cells that exist. Rule fixed in advance:
    PLATEAU iff >= min_positive_fraction of neighbours are > 0 AND median(neighbours) >= min_median_ratio*headline.
    """
    sls,tps=sorted(grid[0]),sorted(grid[1])
    if key not in nets or key[0] not in sls or key[1] not in tps:raise ValueError('headline not in grid')
    i,j=sls.index(key[0]),tps.index(key[1]);nb=[]
    for a in(-1,0,1):
        for b in(-1,0,1):
            if (a,b)==(0,0):continue
            ii,jj=i+a,j+b
            if 0<=ii<len(sls) and 0<=jj<len(tps) and (sls[ii],tps[jj]) in nets:nb.append(float(nets[(sls[ii],tps[jj])]))
    head=float(nets[key])
    if not nb:return {'status':'NO_NEIGHBOURS','neighbours':0}
    pos=sum(v>0 for v in nb)/len(nb);med=float(np.median(nb))
    ok=head>0 and pos>=min_positive_fraction and med>=min_median_ratio*head
    return {'status':'PLATEAU' if ok else 'ISOLATED_SPIKE_OR_NEGATIVE','neighbours':len(nb),'positive_fraction':pos,'median_neighbour':med,'headline':head,'rule':{'min_positive_fraction':min_positive_fraction,'min_median_ratio':min_median_ratio}}


class TrialRegistry:
    """Append-only, hash-chained count of every candidate ever evaluated (global multiplicity).

    A campaign is a (campaign_id, family_id) with n_trials. Re-registering the same campaign
    is rejected so a rerun cannot silently reset the count.
    """
    def __init__(self,path):self.path=Path(path)
    def _rows(self):
        if not self.path.exists():return []
        return [json.loads(x) for x in self.path.read_text().splitlines() if x.strip()]
    def register(self,campaign_id,family_id,n_trials,note=''):
        if n_trials<1:raise ValueError('n_trials must be positive')
        rows=self._rows()
        if any(r['campaign_id']==campaign_id and r['family_id']==family_id for r in rows):raise ValueError(f'campaign already registered: {campaign_id}/{family_id}')
        prev=rows[-1]['hash'] if rows else '0'*64
        body={'campaign_id':campaign_id,'family_id':family_id,'n_trials':int(n_trials),'note':note,'prev':prev}
        h=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('a') as f:f.write(json.dumps({**body,'hash':h})+'\n')
        return h
    def total(self):return sum(r['n_trials'] for r in self._rows())
    def verify(self):
        prev='0'*64
        for k,r in enumerate(self._rows()):
            body={x:r[x] for x in('campaign_id','family_id','n_trials','note','prev')}
            if r['prev']!=prev or hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=r['hash']:return {'valid':False,'broken_at':k}
            prev=r['hash']
        return {'valid':True,'rows':len(self._rows())}


def sidak_bonferroni(p,n_trials):
    """Conservative family-wise adjustment of a single-cell p-value across n_trials."""
    if not 0<=p<=1 or n_trials<1:raise ValueError('bad p or n_trials')
    return {'bonferroni':min(1.,p*n_trials),'sidak':1-(1-p)**n_trials}


def max_null_direction(stat_fn,signal_days,n_sims,seed,flip='session'):
    """Null of the max statistic over ALL candidates under randomized direction.

    stat_fn(signal_sign) -> 1-D array of per-candidate statistics where signal_sign is an int8 +/-1
    vector multiplied into the real signal directions. flip='session' flips whole sessions together
    (preserves intra-session structure); 'signal' flips each signal independently.
    Returns observed max, null maxima and p = (1+#{null>=obs})/(1+n_sims).
    """
    obs=np.asarray(stat_fn(np.ones(len(signal_days),np.int8)),float)
    if not np.isfinite(obs).any():raise ValueError('no finite observed statistic')
    days,inv=np.unique(np.asarray(signal_days),return_inverse=True);rng=np.random.default_rng(seed);null=np.empty(n_sims)
    for s in range(n_sims):
        sign=rng.choice(np.array([-1,1],np.int8),len(days))[inv] if flip=='session' else rng.choice(np.array([-1,1],np.int8),len(signal_days))
        v=np.asarray(stat_fn(sign),float);null[s]=np.nanmax(v)
    om=float(np.nanmax(obs))
    return {'observed_max':om,'n_sims':int(n_sims),'seed':int(seed),'flip':flip,'null_mean':float(null.mean()),'null_q95':float(np.quantile(null,.95)),'p_max':float((np.sum(null>=om)+1)/(n_sims+1)),'mc_se':float(np.sqrt(.25/n_sims))}
