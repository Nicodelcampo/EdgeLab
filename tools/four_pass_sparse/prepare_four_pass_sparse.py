"""Convert bounded canonical raw ticks; invoke the ONE JS detector, never OHLC inference."""
from pathlib import Path
import argparse,hashlib,json,subprocess,tempfile
import pyarrow.parquet as pq

def run(z):
    if z.max_rows<1 or z.tick_size<=0:raise ValueError('POSITIVE_LIMIT_AND_TICK_SIZE_REQUIRED')
    source=Path(z.source);digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if digest!=z.expected_sha256:raise ValueError('SOURCE_SHA256_MISMATCH')
    pf=pq.ParquetFile(source);needed=['ts_utc_ns','sequence','price_ticks','volume','instrument','contract']
    if not set(needed)<=set(pf.schema_arrow.names):raise ValueError('CANONICAL_ACTUAL_TICKS_REQUIRED')
    out=Path(z.out);out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='edgelab_fp4_') as td:
        dump=Path(td)/'ticks.jsonl';count=0
        with open(dump,'w') as f:
            for batch in pf.iter_batches(batch_size=20000,columns=needed):
                for r in batch.to_pylist():
                    if r['ts_utc_ns']<int(z.from_ns):continue
                    if z.before_ns and r['ts_utc_ns']>=int(z.before_ns):break
                    # Producer integers retained; null/missing volume must not be imputed.
                    x={'ts_ns':str(r['ts_utc_ns']),'sequence':r['sequence'],'price_tick':r['price_ticks'],'volume':r['volume'],'instrument':r['instrument'],'contract':r['contract']}
                    f.write(json.dumps(x,separators=(',',':'))+'\n');count+=1
                    if count>=z.max_rows:break
                if count>=z.max_rows or (z.before_ns and batch.column(0)[-1].as_py()>=int(z.before_ns)):break
        args=['node',str(Path(__file__).with_name('four_pass_sparse_cli.cjs')),'--input',str(dump),'--out',str(out),'--tick-size',str(z.tick_size),'--asset',z.asset,'--from-ns',z.from_ns]
        if z.config:args+=['--config',z.config]
        result=subprocess.run(args,check=False,capture_output=True,text=True)
        if not out.exists():raise RuntimeError(result.stderr)
        layer=json.load(open(out));layer.update(source_sha256=digest,source_rows_metadata=pf.metadata.num_rows,input_rows_serialized=count,source='CANONICAL_RAW_TICKS',clock_status='NOT_CERTIFIED',semantic_limit='ordered LAST observations; no fabricated interpolation, future outcomes or fills')
        if layer['detector']['status']=='SEARCHING':layer['search_limit']='INPUT_EOF_OR_EXPLICIT_MAX_ROWS;not no-zone proof'
        out.write_text(json.dumps(layer,indent=2)+'\n');print(result.stdout.strip());return result.returncode
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--expected-sha256',required=True);p.add_argument('--out',required=True);p.add_argument('--asset',required=True);p.add_argument('--tick-size',type=float,required=True);p.add_argument('--max-rows',type=int,default=200000);p.add_argument('--from-ns',default='0');p.add_argument('--before-ns');p.add_argument('--config');raise SystemExit(run(p.parse_args()))
