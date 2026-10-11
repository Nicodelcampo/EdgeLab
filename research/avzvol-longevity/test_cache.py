from pathlib import Path
import json,numpy as np
from engine import features,build_cache,cached_features
rng=np.random.default_rng(9943);checks=0
for n in [100,250,501,1000]:
 for _ in range(25):
  p=rng.integers(-10,11,n,dtype=np.int64);t=np.cumsum(rng.integers(0,300000000,n,dtype=np.int64));t[n//2:]+=15000000000;v=rng.integers(1,20,n).astype(float);f=rng.integers(-1,2,n,dtype=np.int8);b=np.arange(n)//25;st=np.arange(0,n,25);en=np.minimum(st+25,n);i0=24;b0=0;c=build_cache(p,t,v,f,b,st,en,b0,i0,n,-2,2)
  for tr in [50,n-2]:
   ex=25;pk=40;expected=features(p,t,v,f,b,st,en,b0,i0,tr,ex,pk,1,20,0,-2,2);got=cached_features(p,t,b,b0,i0,tr,ex,pk,1,20,0,-2,2,c);assert np.allclose(expected,got,equal_nan=True)
   c2=build_cache(p,t,v,f,b,st,en,b0,i0,tr+1,-2,2);g2=cached_features(p,t,b,b0,i0,tr,ex,pk,1,20,0,-2,2,c2);assert np.allclose(got,g2,equal_nan=True);checks+=2
Path('/data/analysis/avzvol-longevity/cache-test-evidence.json').write_text(json.dumps({'status':'PASS','exact_reference_feature_comparisons':checks,'future_prefix_invariance':True},indent=2)+'\n');print('CACHE_PARITY_PASS',checks)
