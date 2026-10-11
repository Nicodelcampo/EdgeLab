import unittest,itertools
import numpy as np
from expanded_passage import evaluate,reference
class TestExpanded(unittest.TestCase):
 def test_parity(self):
  rng=np.random.default_rng(42151);ncheck=0
  for rep in range(200):
   p=np.r_[0,np.cumsum(rng.integers(-3,4,119))].astype(np.int64);ts=np.cumsum(rng.integers(0,5,len(p))).astype(np.int64)*100000000;bar=np.arange(len(p))//3
   if rep%4==0:ts[60:]+=20000000000
   for mode,ep,D,q in itertools.product([0,1],[0,1,2],[3,7],[.25,.5,.75]):
    args=(p,ts,bar,0,len(p),-2,2,D,q,ep,mode,13,25)
    a=evaluate(*args);b=reference(*args)
    if a!=b:raise AssertionError((rep,mode,ep,D,q,a,b))
    ncheck+=1
  self.assertEqual(ncheck,7200)
 def test_rearm(self):
  p=np.array([0,2,1,0,3,7,4,0,-1],np.int64);ts=np.arange(len(p),dtype=np.int64);bar=np.arange(len(p),dtype=np.int64)
  a=evaluate(p,ts,bar,0,len(p),0,0,6,.25,0,0);b=evaluate(p,ts,bar,0,len(p),0,0,6,.25,0,1)
  self.assertEqual(a[0],3);self.assertEqual(b[0],4);self.assertEqual(b[-1],1);self.assertEqual(b[3],6)
if __name__=='__main__':unittest.main()
