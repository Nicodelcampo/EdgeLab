"""Private Kaggle GPU smoke/parity kernel; synthetic data only, no holdout."""
import json,time
from pathlib import Path
import numpy as np
import cupy as cp
SRC=r'''extern "C" __global__ void screen(const long long* sig,const signed char* d,const int* h,const int* l,const int* bo,const int* ao,const int* sl,const int* tp,const signed char* mul,int ns,int nc,int n,int hold,float fee,float* out){int z=blockDim.x*blockIdx.x+threadIdx.x;if(z>=ns*nc)return;int k=z/nc,q=z-k*nc,i=(int)sig[k]+1;if(i>=n){out[z]=NAN;return;}int di=d[k]*mul[q],e=di==1?ao[i]:bo[i],st=e-di*sl[q],tg=e+di*tp[q],end=min(n,i+hold+1);float v=-fee;for(int j=i;j<end;j++){if(di==1&&l[j]<=st){v=-sl[q]-fee;break;}if(di==1&&h[j]>=tg+1){v=tp[q]-fee;break;}if(di==-1&&h[j]>=st){v=-sl[q]-fee;break;}if(di==-1&&l[j]<=tg-1){v=tp[q]-fee;break;}}out[z]=v;}'''
def cpu(sig,d,h,l,bo,ao,sl,tp,mul,hold=64):
 out=np.empty((len(sig),len(sl)),np.float32)
 for k,s in enumerate(sig):
  i=int(s)+1
  for q in range(len(sl)):
   di=int(d[k])*int(mul[q]);e=int(ao[i] if di==1 else bo[i]);st=e-di*int(sl[q]);tg=e+di*int(tp[q]);v=-.5
   for j in range(i,min(len(h),i+hold+1)):
    if di==1 and l[j]<=st:v=-sl[q]-.5;break
    if di==1 and h[j]>=tg+1:v=tp[q]-.5;break
    if di==-1 and h[j]>=st:v=-sl[q]-.5;break
    if di==-1 and l[j]<=tg-1:v=tp[q]-.5;break
   out[k,q]=v
 return out
rng=np.random.default_rng(20261002);n=100000;ns=2048;nc=256;base=30000+np.cumsum(rng.integers(-2,3,n,dtype=np.int32));h=base+rng.integers(0,8,n,dtype=np.int32);l=base-rng.integers(0,8,n,dtype=np.int32);bo=base-1;ao=base+1;sig=np.sort(rng.choice(n-66,ns,replace=False)).astype(np.int64);d=rng.choice(np.array([-1,1],np.int8),ns);sl=rng.choice(np.array([20,40,80,120],np.int32),nc);tp=rng.choice(np.array([30,60,100,160],np.int32),nc);mul=rng.choice(np.array([-1,1],np.int8),nc)
args=[cp.asarray(x) for x in (sig,d,h,l,bo,ao,sl,tp,mul)];out=cp.empty(ns*nc,cp.float32);ker=cp.RawKernel(SRC,'screen');threads=256;cp.cuda.Stream.null.synchronize();t=time.time();ker(((ns*nc+threads-1)//threads,),(threads,),(*args,ns,nc,n,64,np.float32(.5),out));cp.cuda.Stream.null.synchronize();elapsed=time.time()-t;got=cp.asnumpy(out.reshape(ns,nc));ref=cpu(sig[:128],d[:128],h,l,bo,ao,sl[:16],tp[:16],mul[:16]);ok=bool(np.array_equal(got[:128,:16],ref));props=cp.cuda.runtime.getDeviceProperties(0);name=props['name'].decode() if isinstance(props['name'],bytes) else str(props['name']);res={'schema_version':'edgelab_gpu_parity_v1','passed':ok,'gpu':name,'tasks':ns*nc,'gpu_seconds':elapsed,'tasks_per_second':ns*nc/elapsed,'checked_cells':2048,'max_abs_diff':float(np.max(np.abs(got[:128,:16]-ref))),'d2_opened':False};Path('/kaggle/working/gpu_parity.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2));assert ok
