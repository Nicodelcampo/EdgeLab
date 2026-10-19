"""Same closed-bar CSR semantics; bounded chunks of whole bars, disk-backed output."""
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from adapter import csr

def bounded_csr(px,vol,st,en,root,chunk_bars=25000):
 root=Path(root);off=np.empty(len(st)+1,np.int64);off[0]=0;k=0
 tp=root/'footprint-ticks-private.bin';vp=root/'footprint-volume-private.bin'
 with tp.open('wb') as tf,vp.open('wb') as vf:
  for a in range(0,len(st),chunk_bars):
   z=min(a+chunk_bars,len(st));left=int(st[a]);right=int(en[z-1])
   co,ct,cv=csr(px[left:right],vol[left:right],st[a:z]-left,en[a:z]-left)
   off[a+1:z+1]=co[1:]+k;ct.tofile(tf);cv.tofile(vf);k+=len(ct)
 return SimpleNamespace(offsets=off,ticks=np.memmap(tp,dtype=np.int64,mode='r'),vols=np.memmap(vp,dtype=np.float64,mode='r'))

if __name__=='__main__':
 import tempfile,json
 rng=np.random.default_rng(327);checks=0
 with tempfile.TemporaryDirectory() as root:
  for n in [1,24,25,26,249,250,251,1027,12345]:
   p=rng.integers(-20,20,n,dtype=np.int64);v=rng.integers(1,50,n).astype(float);s=np.arange(0,n,25);e=np.minimum(s+25,n);a=csr(p,v,s,e)
   for chunk in [1,2,3,7,25000]:
    b=bounded_csr(p,v,s,e,root,chunk);assert all(np.array_equal(x,y) for x,y in zip(a,[b.offsets,b.ticks,b.vols]));del b;checks+=1
 Path('/data/analysis/avzvol-replication-rest/bounded-csr-check.json').write_text(json.dumps({'status':'PASS','exact_parity_cases':checks,'changes_market_logic':False},indent=2)+'\n');print('BOUNDED_CSR_EXACT_PARITY',checks)
