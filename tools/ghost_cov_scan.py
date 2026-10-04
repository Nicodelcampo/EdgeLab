import sys,os,subprocess,json,numpy as np,pandas as pd,pyarrow.parquet as pq,pyarrow.compute as pc
DS='edgelab-ticks-nt8-canonical'
out={}
for A in sys.argv[1:]:
    for c in (f'{A}_09-26',f'{A}_12-26'):
        fn=f'ho_raw/{c}_ticks.parquet'
        if not os.path.exists(fn):
            r=subprocess.run(['curl','-sS','-L','-o',fn,'-w','%{http_code}',f'https://www.kaggle.com/api/v1/datasets/download/nicolasbuttaro/{DS}?fileName={A}/{c}_ticks_ext.parquet'],capture_output=True,text=True)
            if r.stdout.strip()!='200':
                print(A,c,'download',r.stdout);os.path.exists(fn) and os.remove(fn);continue
        f=pq.ParquetFile(fn);ts=[];v=[]
        for g in range(f.metadata.num_row_groups):
            t=f.read_row_group(g,columns=['ts_utc_ns','volume','tick_type']);m=pc.equal(t.column('tick_type'),'trade').to_numpy(zero_copy_only=False)
            ts.append(t.column('ts_utc_ns').to_numpy()[m]);v.append(t.column('volume').to_numpy()[m])
        ts=np.concatenate(ts);v=np.concatenate(v)
        ix=pd.to_datetime(ts,unit='ns',utc=True).tz_convert('America/Chicago')+pd.Timedelta(hours=7)
        s=pd.Series(v,index=pd.to_datetime(ix.date)).groupby(level=0).sum()
        n=pd.Series(1,index=pd.to_datetime(ix.date)).groupby(level=0).sum()
        out[c]={'vol':{str(k.date()):int(x) for k,x in s.items()},'ticks':{str(k.date()):int(x) for k,x in n.items()}}
        print(A,c,'rows',len(ts),s.index.min().date(),s.index.max().date(),len(s),flush=True)
    json.dump(out,open(f'cov/cov_{"_".join(sys.argv[1:])}.json','w'))
