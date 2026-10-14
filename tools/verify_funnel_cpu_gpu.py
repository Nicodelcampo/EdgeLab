#!/usr/bin/env python3
"""Synthetic CPU/CUDA parity. No market data, split or D2 files required."""
import argparse, hashlib, json, platform, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def oracle(sig, dirs, high, low, bid, ask, sls, tps, mult, hold, fees):
    out=np.full((len(sig),len(sls)),np.nan,np.float64)
    for k,s in enumerate(sig):
        entry=int(s)+1
        if entry>=len(high): continue
        for q,(sl,tp,m) in enumerate(zip(sls,tps,mult)):
            d=int(dirs[k])*int(m);e=int(ask[entry] if d==1 else bid[entry])
            stop=e-d*int(sl);target=e+d*int(tp);v=-fees
            for j in range(entry,min(len(high),entry+hold+1)):
                stop_hit=int(low[j])<=stop if d==1 else int(high[j])>=stop
                target_hit=int(high[j])>=target+1 if d==1 else int(low[j])<=target-1
                if stop_hit: v=-int(sl)-fees;break
                if target_hit: v=int(tp)-fees;break
            out[k,q]=v
    return out


def cases():
    yield 'known_paths',([0,2,5],[1,-1,1],[100,100,112,100,100,100],[100,99,99,88,100,100],[99]*6,[101]*6,[10],[10],[1],2,.5)
    yield 'stop_first_tie',([0],[1],[100,120],[100,80],[99,99],[101,101],[10],[10],[1],0,.5)
    yield 'target_touch_not_fill',([0],[1],[100,111],[100,100],[99,99],[101,101],[10],[10],[1],0,.5)
    rng=np.random.default_rng(20261003)
    for hold in (0,1,17,200):
        n=503;mid=10000+np.cumsum(rng.integers(-4,5,n));width=rng.integers(1,20,n)
        sig=np.r_[np.arange(0,n,7),n-1];dirs=rng.choice([-1,1],len(sig))
        yield 'random_hold_'+str(hold),(sig,dirs,mid+width,mid-width,mid-1,mid+1,[3,7,19,31],[5,13,23,47],[1,-1,1,-1],hold,.37)
    yield 'empty_signals',([],[],[100],[100],[99],[101],[10],[10],[1],2,.5)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--cpu-only',action='store_true');a=p.parse_args()
    report={'schema_version':'funnel_parity_v1','status':'RUNNING','market_data_read':False,'holdout_opened':False,'asserts_edge':False,'gpu_tested':False,'python':platform.python_version(),'numpy':np.__version__,'cases':[]}
    try:
        from edgelab.funnel.screen import cheap_screen
        import numba
        report['numba']=numba.__version__
        if not a.cpu_only:
            import cupy as cp
            report['cupy']=cp.__version__;report['cuda_runtime']=int(cp.cuda.runtime.runtimeGetVersion())
            report['gpu_name']=str(cp.cuda.runtime.getDeviceProperties(0)['name'])
        for name,raw in cases():
            sig,d,h,l,bo,ao,sl,tp,m,hold,fee=raw
            sig=np.asarray(sig,np.int64);d=np.asarray(d,np.int8)
            h,l,bo,ao,sl,tp=[np.asarray(x,np.int32) for x in (h,l,bo,ao,sl,tp)];m=np.asarray(m,np.int8)
            expected=oracle(sig,d,h,l,bo,ao,sl,tp,m,hold,fee)
            cpu,_=cheap_screen(sig,d,h,l,bo,ao,sl,tp,m,hold,fee,'cpu')
            np.testing.assert_allclose(cpu,expected,rtol=0,atol=1e-10,equal_nan=True)
            item={'case':name,'shape':list(cpu.shape),'cpu_oracle':'PASS'}
            if not a.cpu_only and cpu.size:
                gpu,dev=cheap_screen(sig,d,h,l,bo,ao,sl,tp,m,hold,fee,'gpu')
                if dev.backend!='gpu': raise AssertionError('silent GPU fallback')
                np.testing.assert_array_equal(np.isnan(cpu),np.isnan(gpu))
                # GPU output and fee are float32; compare its declared precision.
                np.testing.assert_allclose(gpu,expected.astype(np.float32),rtol=0,atol=8*np.finfo(np.float32).eps*max(1,float(np.nanmax(np.abs(expected)))),equal_nan=True)
                item['gpu_oracle']='PASS';report['gpu_tested']=True
            report['cases'].append(item)
        report['status']='CPU_ONLY_PASS_GPU_PENDING' if a.cpu_only else 'CPU_GPU_PARITY_PASS'
    except Exception as e:
        report['status']='FAIL';report['error']=type(e).__name__+': '+str(e)
    report['sources_sha256']={}
    for rel in ('edgelab/funnel/screen.py','edgelab/funnel/device.py','tools/verify_funnel_cpu_gpu.py'):
        file=Path(__file__).resolve().parents[1]/rel
        if file.exists(): report['sources_sha256'][rel]=hashlib.sha256(file.read_bytes()).hexdigest()
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 1 if report['status']=='FAIL' else 0

if __name__=='__main__':raise SystemExit(main())
