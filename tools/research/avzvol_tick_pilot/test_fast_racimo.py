import random,types,unittest
from collections import defaultdict
from pathlib import Path
import numpy as np,pandas as pd
from fast_racimo import replay
m=types.ModuleType('legacy');m.__dict__.update(np=np,pd=pd,defaultdict=defaultdict);exec(Path('/data/analysis/avzvol-pilot/legacy_detector.py').read_text(),m.__dict__)
class Tests(unittest.TestCase):
 def test_random_exact_births_and_prefixes(self):
  r=random.Random(29853)
  for trial in range(120):
   n=100;b=np.cumsum([r.randint(0,5) for _ in range(n)]).astype(np.int64);lo=np.array([r.randint(80,120) for _ in range(n)],np.int64);hi=lo+np.array([r.randint(0,12) for _ in range(n)],np.int64);params=dict(racimo_min=[4,5,8,18][trial%4],racimo_bars=[10,20,50,100][(trial//4)%4],racimo_altura_ticks=[10,20,30,45][(trial//16)%4]);zs=[];cl=[]
   for i in range(n):
    z=dict(bar=int(b[i]),low_tick=int(lo[i]),high_tick=int(hi[i]),racimo_bar=-1,rac=None);m._racimo(z,zs,cl,int(b[i]),params);zs.append(z)
    if i in [24,49,99]:
     fast=replay(b[:i+1],lo[:i+1],hi[:i+1],params['racimo_min'],params['racimo_bars'],params['racimo_altura_ticks']);ref=np.array([(c['bar'],c['start0'],c['low0'],c['high0']) for c in cl],np.int64).reshape(-1,4);self.assertTrue(np.array_equal(fast,ref),(trial,i,fast,ref))
if __name__=='__main__':unittest.main()
