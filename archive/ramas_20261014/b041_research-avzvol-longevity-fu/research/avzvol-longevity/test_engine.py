import json
from pathlib import Path
import numpy as np
from engine import first_visit,dedup_masks,features
rng=np.random.default_rng(9931);checks=0
for n in [100,250,500]:
 for _ in range(30):
  p=rng.integers(-8,9,n,dtype=np.int64);t=np.cumsum(rng.integers(0,300000000,n,dtype=np.int64));b=np.arange(n)//25;v=rng.integers(1,20,n).astype(float);f=rng.integers(-1,2,n,dtype=np.int8);st=np.arange(0,n,25);en=np.minimum(st+25,n);m=int(rng.integers(0,n-5));stop=n
  ref=next((i for i in range(m,stop) if -2<=p[i]<=2),-1);got,why=first_visit(p,t,b,m,stop,-2,2);assert got==ref
  tr=n-2;ex=1;pk=10;ff=features(p,t,v,f,b,st,en,0,0,tr,ex,pk,1,20,0,-2,2);total=sum(float(v[i]) for i in range(1,tr+1));inside=sum(float(v[i]) for i in range(1,tr+1) if -2<=p[i]<=2);assert abs(ff[3]-inside/total)<1e-12
  flags=[any(-2<=p[i]<=2 for i in range(st[j],en[j])) for j in range(1,int(b[tr]))];cnt=0;seen=bool(-2<=p[0]<=2);outside=0
  for hit in flags:
   if hit:
    if seen and outside>=1:cnt+=1
    seen=True;outside=0
   else:outside+=1
  assert ff[0]==cnt
  # Appending future prints cannot change any trigger feature or completed first visit.
  p2=np.r_[p,rng.integers(-50,50,25)];t2=np.r_[t,t[-1]+np.arange(1,26)*100];b2=np.arange(n+25)//25;v2=np.r_[v,np.ones(25)];f2=np.r_[f,np.zeros(25,dtype=np.int8)];st2=np.arange(0,n+25,25);en2=np.minimum(st2+25,n+25);ff2=features(p2,t2,v2,f2,b2,st2,en2,0,0,tr,ex,pk,1,20,0,-2,2);assert np.allclose(ff,ff2,equal_nan=True);checks+=3
birth=np.array([[0,0,0,9],[2,2,0,9],[4,4,3,12],[6,6,20,29]],np.int64);ses=np.zeros(10,np.int64);assert dedup_masks(birth,ses,.75).tolist()==[True,False,True,True];assert dedup_masks(birth,ses,.5).tolist()==[True,False,False,True];checks+=2
# Maintenance-like gaps stop new landmark visits, and same-bar repeated prints are not extra visits.
assert first_visit(np.array([20,20,0]),np.array([0,1,20000000000]),np.zeros(3,np.int64),0,3,-1,1)==(-1,3)
assert first_visit(np.array([20,0]),np.array([0,1]),np.array([0,3000]),0,2,-1,1)==(-1,2);checks+=2
Path('/data/analysis/avzvol-longevity/test-evidence.json').write_text(json.dumps({'status':'PASS','checks':checks,'future_prefix_invariance':True,'closed_bar_print_membership':True,'dedup_future_independent':True},indent=2)+'\n');print('ENGINE_TESTS_PASS',checks)
