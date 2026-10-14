import numpy as np
from edgelab.research.ym_bt2a_density_corridors import *
def z(i=10,ns=10,direction='long',lo=100,hi=102,**kw):return CausalZone('z',i,ns,lo,hi,direction,kw.get('volume',10),kw.get('rows',2),kw.get('trap_fraction',.2),kw.get('score',12),kw.get('threshold',10))
def test_future_zone_is_excluded():
 a=density_profile([z(i=11,ns=11)],asof_idx=10,asof_ns=10,origin_price_ticks=100,trade_direction='long',offsets=[0,1,2],sigma_ticks=1,scope='total');assert np.all(a==0)
def test_directional_scopes_separate_support_and_opposition():
 zones=[z(direction='long'),z(direction='short')];s=density_profile(zones,asof_idx=10,asof_ns=10,origin_price_ticks=101,trade_direction='long',offsets=[0],sigma_ticks=1,scope='support');o=density_profile(zones,asof_idx=10,asof_ns=10,origin_price_ticks=101,trade_direction='long',offsets=[0],sigma_ticks=1,scope='opposition');assert s[0]>0 and o[0]>0
def test_projection_drops_future_lifecycle_fields():
 raw={'id':'x','sig_idx':1,'dir':'short','lo':99.5,'hi':101.5,'vol':8,'nrows':2,'frac':.3,'a_score':12,'a_thr':10,'touches':999,'state':'INVALIDATED','ended_ms':999999};c=causal_zone_from_bt2(raw,[1,2]);assert not hasattr(c,'touches') and not hasattr(c,'state') and c.available_ns==2
def test_wall_and_policy_match():
 total=np.array([.8,.1,.1,.1,.1,.8,.9]);opp=np.array([0,.1,.1,.1,.1,.7,.8]);back=np.array([.6,.2]);o=observe_corridor(total=total,opposition=opp,support_back=back,wall_min=.5,field_mode='TOTAL',momentum_ticks=3,strength_ratio=1.3);p=CorridorPolicy('p','TOTAL',1,.3,.5,.5,4,7,5,2,1.25);assert o.wall_distance==5 and policy_matches(p,o)
def test_frozen_grid_count_and_ids():
 g=corridor_policy_grid_v1();assert len(g)==2304 and len({p.policy_id for p in g})==2304
