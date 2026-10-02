import numpy as np
from edgelab.funnel.signals import session_vwap_reclaim,absorption_break,failed_auction_reentry

def test_vwap_prefix_and_mirror():
 c=np.array([100,100,80,80,101,120,120,99],np.int32);v=np.ones(8,np.int64);td=np.ones(8,np.int32)
 i,d=session_vwap_reclaim(c,v,td,1,5);mi,md=session_vwap_reclaim(-c,v,td,1,5)
 assert np.array_equal(i,mi) and np.array_equal(d,-md)
 pi,pd=session_vwap_reclaim(c[:6],v[:6],td[:6],1,5);assert np.array_equal(pi,i[i<6]) and np.array_equal(pd,d[i<6])
def test_absorption_break_causal():
 o=np.array([100,100,100,100,100],np.int32);h=np.array([102,102,101,110,111],np.int32);l=np.array([98,98,99,100,100],np.int32);c=np.array([100,100,100,109,110],np.int32);v=np.array([10,10,30,10,10],np.int64);td=np.ones(5,np.int32)
 i,d=absorption_break(o,h,l,c,v,td,2,2.0,3);assert i.tolist()==[3] and d.tolist()==[1]
def test_failed_auction_reentry():
 h=np.array([10,11,12,15,11],np.int32);l=np.array([8,8,9,11,9],np.int32);c=np.array([9,10,10,14,10],np.int32);td=np.ones(5,np.int32)
 i,d=failed_auction_reentry(h,l,c,td,3,20);assert i.tolist()==[4] and d.tolist()==[-1]
