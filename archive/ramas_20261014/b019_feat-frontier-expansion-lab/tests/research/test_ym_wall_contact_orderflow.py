import numpy as np
from edgelab.research.ym_wall_contact_orderflow import *
def test_aggressor_sign_quotes():
 p=np.array([101,99,100]);b=np.array([99,99,99]);a=np.array([101,101,101]);assert aggressor_sign(p,b,a).tolist()==[1,-1,0]
def test_long_confirmation_and_strict_later_fill():
 p=np.array([100,100,101,102,103]);b=p-1;a=p;v=np.ones(5);s=np.zeros(5);c=confirm_rejection(trigger_idx=0,lo=99,hi=100,direction='long',price=p,bid=b,ask=a,volume=v,sessions=s,observation_ticks=5,rejection_min=2,imbalance_min=.5,wall_prints_min=2);assert c.confirmation_idx==3 and c.fill_idx==4 and c.fill_idx>c.confirmation_idx
def test_short_symmetry():
 p=np.array([100,100,99,98,97]);b=p;a=p+1;v=np.ones(5);s=np.zeros(5);c=confirm_rejection(trigger_idx=0,lo=100,hi=101,direction='short',price=p,bid=b,ask=a,volume=v,sessions=s,observation_ticks=5,rejection_min=2,imbalance_min=.5,wall_prints_min=2);assert c.confirmation_idx==3 and c.aligned_imbalance==1
def test_no_cross_session_fill():
 p=np.array([100,102,103]);b=p-1;a=p;v=np.ones(3);s=np.array([0,0,1]);assert confirm_rejection(trigger_idx=0,lo=99,hi=100,direction='long',price=p,bid=b,ask=a,volume=v,sessions=s,observation_ticks=3,rejection_min=2,imbalance_min=0,wall_prints_min=1)is None
def test_grid_cardinality():
 g=wall_contact_policy_grid_v1();assert len(g)==3456 and len({x[0] for x in g})==3456
def test_support_breach_short_and_later_fill():
 p=np.array([100,100,99,98,97]);b=p;a=p+1;v=np.ones(5);s=np.zeros(5);c=confirm_breach(trigger_idx=0,lo=100,hi=101,zone_direction='long',price=p,bid=b,ask=a,volume=v,sessions=s,observation_ticks=5,penetration_min=2,imbalance_min=.5,wall_prints_max=3);assert c.breakout_direction=='short'and c.confirmation_idx==3 and c.fill_idx==4
def test_resistance_breach_long_symmetry():
 p=np.array([100,101,102,103,104]);b=p-1;a=p;v=np.ones(5);s=np.zeros(5);c=confirm_breach(trigger_idx=0,lo=99,hi=100,zone_direction='short',price=p,bid=b,ask=a,volume=v,sessions=s,observation_ticks=5,penetration_min=2,imbalance_min=.5,wall_prints_max=3);assert c.breakout_direction=='long'and c.confirmation_idx==2 and c.aligned_imbalance==1
def test_breach_grid_cardinality():
 g=wall_breach_policy_grid_v1();assert len(g)==2304 and len({x[0]for x in g})==2304
