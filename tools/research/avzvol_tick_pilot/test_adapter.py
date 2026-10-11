import importlib.util,random,unittest
import numpy as np
from adapter import build_bars,passage,STATUS,fail_closed_events
s=importlib.util.spec_from_file_location('ref','/data/analysis/avzvol-pilot/reference_partial_return.py');ref=importlib.util.module_from_spec(s);s.loader.exec_module(ref)
class Tests(unittest.TestCase):
 def test_footprint_and_partial(self):
  rng=np.random.default_rng(282);px=rng.integers(50,65,128);v=rng.integers(1,10,128);ts=np.arange(128,dtype=np.int64);sid=np.r_[np.zeros(53,int),np.ones(75,int)]
  bars,fps,st,en,ss,ee=build_bars(ts,px,v,sid)
  self.assertEqual((en-st).tolist(),[25,25,3,25,25,25])
  for b,(a,z) in enumerate(zip(st,en)):
   d={}
   for p,q in zip(px[a:z],v[a:z]):d[int(p)]=d.get(int(p),0)+int(q)
   self.assertEqual(dict(zip(fps.ticks[fps.offsets[b]:fps.offsets[b+1]],fps.vols[fps.offsets[b]:fps.offsets[b+1]])),d)
 def test_future_cannot_change_closed_footprints(self):
  px=np.arange(75,dtype=np.int64);v=np.ones(75,dtype=np.int64);ts=np.arange(75,dtype=np.int64);sid=np.zeros(75,dtype=np.int64)
  a,fa,st,en,ss,ee=build_bars(ts[:50],px[:50],v[:50],sid[:50]);b,fb,st,en,ss,ee=build_bars(ts,px,v,sid)
  self.assertTrue(np.array_equal(fa.ticks,fb.ticks[:fb.offsets[2]]));self.assertTrue(np.array_equal(fa.vols,fb.vols[:fb.offsets[2]]));self.assertTrue(np.array_equal(a.close_t,b.close_t[:2]))
 def test_partial_reference_random(self):
  r=random.Random(8721)
  for trial in range(400):
   prices=[100]
   for _ in range(120):prices.append(prices[-1]+r.randint(-3,3))
   for sign in [1,-1]:
    px=np.array([sign*p for p in prices],np.int64);ts=np.arange(len(px),dtype=np.int64)*100000000;bar=np.arange(len(px),dtype=np.int64)//25;lo,hi=(99,101) if sign==1 else (-101,-99)
    for endpoint in range(3):
     q=[.25,.5,.75][trial%3];d=[5,10,20][trial%3];arr=passage(px,ts,bar,0,len(px),lo,hi,d,q,endpoint,3,-1)
     tape=[ref.Trade(i,int(ts[i]),int(bar[i]),int(px[i]),'s') for i in range(len(px))];tape.append(ref.Trade(len(px),int(ts[-1])+1,0,int(px[-1]),'next_session'));expected=ref.evaluate(tape,ref.Zone('z',lo,hi,0),ref.Rule(d,q,['touch','enter_one_tick','cross_one_tick'][endpoint],3));self.assertEqual(STATUS[arr[0]],expected['status']);self.assertEqual(arr[3]>=0,expected['signal'])
     if arr[3]>=0:self.assertEqual((arr[3],arr[7],arr[8]),(expected['trigger_seq'],expected['frozen_target'],expected['frozen_opposite']))
 def test_scope(self):
  self.assertTrue(fail_closed_events([{'contract':'a','session':'s'}],{('a','s')}))
  with self.assertRaisesRegex(ValueError,'EVENT_OUTSIDE'):fail_closed_events([{'contract':'b','session':'s'}],{('a','s')})
 def test_gap(self):
  px=np.array([100,103,110,105,100],np.int64);t=np.array([0,1,2,3,20000000000],np.int64);b=np.zeros(5,np.int64)
  self.assertEqual(STATUS[passage(px,t,b,0,5,99,101,5,.5,0,100,10000000000)[0]],'UNRESOLVED_GAP')
if __name__=='__main__':unittest.main()
