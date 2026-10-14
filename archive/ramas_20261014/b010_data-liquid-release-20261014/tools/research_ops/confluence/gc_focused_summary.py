"""Public descriptive session aggregates; no market rows or IID-anchor inference."""
import numpy as np

class FocusedSummary:
 def __init__(self,plan):self.plan=plan;self.sessions=[];self.date=None;self.times=None
 def begin(self,date,times):
  if len(times)==0 or np.any(np.diff(times)<=0):raise ValueError('strict focused anchor clock')
  self.date=date;self.times=np.array(times,copy=True)
 def add(self,p,z,loss):
  if p!=0 or self.times is None or len(z)!=len(self.times):raise ValueError('one focused aligned pair')
  mask=(z[:,11]==1)&(z[:,29]>0)&(z[:,36]>0)
  thin=np.zeros(len(mask),dtype=bool);last=None
  for i,t in enumerate(self.times):
   if last is None or int(t)-last>=self.plan['thin_spacing_ns']:thin[i]=True;last=int(t)
  groups={}
  for name,m in [('RETURN',mask),('NOT_RETURN',~mask),('RETURN_THIN60S',mask&thin),('NOT_RETURN_THIN60S',(~mask)&thin)]:
   n=int(m.sum());groups[name]={'anchors':n,'mean_brier':{k:float(v[m].mean()) for k,v in loss.items()} if n else None}
  self.sessions.append({'trade_date':self.date,'groups':groups});self.times=None
 def finish(self):
  out={}
  pairs=[('ARRIVAL','CONTINUOUS'),('ARRIVAL','ARRIVAL_CC'),('ARRIVAL','DENSITY'),('INTERACTION','CONTINUOUS'),('INTERACTION','DENSITY'),('INTERACTION','MIRROR_FULL')]
  for group in ('RETURN','NOT_RETURN','RETURN_THIN60S','NOT_RETURN_THIN60S'):
   rows=[s['groups'][group] for s in self.sessions if s['groups'][group]['anchors']];d={}
   for a,b in pairs:
    v=np.array([r['mean_brier'][a]-r['mean_brier'][b] for r in rows]);n=len(v)
    interval=None
    if n>=2:
     rng=np.random.default_rng(self.plan['bootstrap_seed']);sample=v[rng.integers(0,n,(self.plan['bootstrap_replicates'],n))].mean(axis=1);interval=np.quantile(sample,[.025,.975]).tolist()
    d[a+'_MINUS_'+b]={'equal_session_mean':float(v.mean()) if n else None,'pooled_anchor_mean':sum((r['mean_brier'][a]-r['mean_brier'][b])*r['anchors'] for r in rows)/sum(r['anchors'] for r in rows) if n else None,'improved_sessions':int((v<0).sum()),'descriptive_session_bootstrap_95_interval':interval}
   anchors=sum(r['anchors'] for r in rows)
   out[group]={'anchors':anchors,'support_sessions':len(rows),'support_screen_passed_not_edge':anchors>=self.plan['scenario_min_pooled_anchors'] and len(rows)>=self.plan['scenario_min_sessions'],'contrasts':d}
  return {'primary_cut':self.plan['primary_cut'],'sessions':self.sessions,'groups':out,'bootstrap_scope':'RESAMPLE_AVAILABLE_SESSION_MEANS_NOT_IID_ANCHORS_NOT_CONFIRMATORY_CI','thin_scope':'FIRST_COMMON_ANCHOR_THEN_AT_LEAST60S_APART_BEFORE_CUT_NO_ZONE_EPISODE_OR_INDEPENDENCE_CLAIM','prior_selection_outcomes_inspected':True,'new_block_not_confirmation':True}
