"""EF3/EF4: plateau, global trial counter and max-statistic null with randomized direction.

Everything here is screening-level (bar OHLC, independent signals) and never evidentiary on its own.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np


def candidate_statistic(d0_mean,d1_mean):
    """The ONE criterion for picking/testing a headline: min(D0,D1) minus their gap (scalar or array)."""
    a,b=np.asarray(d0_mean,float),np.asarray(d1_mean,float)
    out=np.minimum(a,b)-np.abs(a-b)
    return float(out) if out.ndim==0 else out


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

    One row per (campaign_id, family_id). `ensure` is idempotent for the same count and rejects a changed
    count, so a rerun cannot silently shrink or reset the tally. Writes take an exclusive file lock.
    Truncation of trailing rows is detectable by passing the remembered `head()` to `verify`.
    """
    FIELDS=('campaign_id','family_id','n_trials','note','prev')
    def __init__(self,path):self.path=Path(path)
    def _rows(self):
        if not self.path.exists():return []
        return [json.loads(x) for x in self.path.read_text().splitlines() if x.strip()]
    @staticmethod
    def _digest(body):return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    def head(self):
        rows=self._rows();return rows[-1]['hash'] if rows else '0'*64
    def ensure(self,campaign_id,family_id,n_trials,note=''):
        """Register if new; return False if already present with the same count; raise if the count differs."""
        import fcntl
        if n_trials<1:raise ValueError('n_trials must be positive')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('a+') as f:
            fcntl.flock(f,fcntl.LOCK_EX);f.seek(0)
            rows=[json.loads(x) for x in f.read().splitlines() if x.strip()]
            for r in rows:
                if r['campaign_id']==campaign_id and r['family_id']==family_id:
                    if r['n_trials']!=int(n_trials):raise ValueError(f'campaign {campaign_id}/{family_id} already registered with {r["n_trials"]} trials, not {n_trials}')
                    return False
            body={'campaign_id':campaign_id,'family_id':family_id,'n_trials':int(n_trials),'note':note,'prev':rows[-1]['hash'] if rows else '0'*64}
            f.seek(0,2);f.write(json.dumps({**body,'hash':self._digest(body)})+'\n');f.flush()
        return True
    def register(self,campaign_id,family_id,n_trials,note=''):
        if not self.ensure(campaign_id,family_id,n_trials,note):raise ValueError(f'campaign already registered: {campaign_id}/{family_id}')
        return self.head()
    def total(self):return sum(r['n_trials'] for r in self._rows())
    def n_campaigns(self):return len({r['campaign_id'] for r in self._rows()})
    def verify(self,expected_head=None):
        prev='0'*64;rows=[]
        try:
            rows=self._rows()
            for k,r in enumerate(rows):
                body={x:r[x] for x in self.FIELDS}
                if r['prev']!=prev or self._digest(body)!=r['hash']:return {'valid':False,'broken_at':k}
                prev=r['hash']
        except (KeyError,TypeError,ValueError):return {'valid':False,'broken_at':'malformed'}
        if expected_head is not None and prev!=expected_head:return {'valid':False,'broken_at':'head_mismatch'}
        return {'valid':True,'rows':len(rows),'head':prev}


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


def max_null_batched(batches,sizes,signal_days,n_sims,seed,flip='session',min_trades=30):
    """Max-statistic null under randomized direction, one kernel pass per partition (not per simulation).

    batches yields (start,end,[(M_plus,M_minus),...]) per config batch and partition (D0,D1): M_plus are outcomes
    with the signal's own direction, M_minus with the opposite one (each signals x configs, NaN = no outcome).
    A simulation picks, per signal, the row from M_plus or M_minus, so means/counts are sign-matrix products.
    sizes: signals per partition, in the order of `signal_days` (concatenated). Row 0 of the sign matrix is the
    real (all +1) signal, so the observed statistic comes from the same pass. Returns (result, observed_vector).
    """
    N=int(sum(sizes));days,inv=np.unique(np.asarray(signal_days),return_inverse=True)
    if len(signal_days)!=N:raise ValueError('signal_days length != sum(sizes)')
    rng=np.random.default_rng(seed)
    sg=np.ones((n_sims+1,N),np.int8)
    sg[1:]=rng.choice(np.array([-1,1],np.int8),(n_sims,len(days)))[:,inv] if flip=='session' else rng.choice(np.array([-1,1],np.int8),(n_sims,N))
    null=np.full(n_sims+1,-np.inf);obs_parts=[];off=[0,*np.cumsum(sizes)]
    for start,end,parts in batches:
        if start!=sum(len(x) for x in obs_parts):raise ValueError('config batches must be contiguous and ordered')
        means=[];cnts=[]
        for k,(Mp,Mm) in enumerate(parts):
            pos=(sg[:,off[k]:off[k+1]]==1).astype(np.float64);neg=1.-pos
            fp,fm=np.isfinite(Mp),np.isfinite(Mm)
            c=pos@fp.astype(np.float64)+neg@fm.astype(np.float64)
            sm=pos@np.where(fp,Mp,0.)+neg@np.where(fm,Mm,0.)
            means.append(np.where(c>0,sm/np.maximum(c,1),np.nan));cnts.append(c)
        ok=(cnts[0]>=min_trades)&(cnts[1]>=min_trades)&np.isfinite(means[0])&np.isfinite(means[1])
        st=np.where(ok,candidate_statistic(means[0],means[1]),-np.inf)
        null=np.maximum(null,st.max(axis=1))
        obs_parts.append(st[0])
    obs=np.concatenate(obs_parts) if obs_parts else np.array([])
    if not np.isfinite(obs).any():raise ValueError('no finite observed statistic')
    nl=null[1:];om=float(obs.max())
    return {'observed_max':om,'n_sims':int(n_sims),'seed':int(seed),'flip':flip,'min_trades':int(min_trades),'null_mean':float(nl.mean()),'null_q95':float(np.quantile(nl,.95)),'p_max':float((np.sum(nl>=om)+1)/(n_sims+1)),'mc_se':float(np.sqrt(.25/n_sims))},obs
