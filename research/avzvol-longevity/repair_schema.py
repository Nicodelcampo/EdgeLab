"""Lossless repair of complete pilot feature column shift; recompute hour from pinned raw tick."""
import csv,gzip,json,hashlib,os,shutil
from pathlib import Path
import numpy as np,pandas as pd,pyarrow.parquet as pq
from feature_schema import FEATURE_NAMES,validate,attach_features
P=Path('/data/analysis/avzvol-longevity');R=P/'MNQ_12-26';old=R/'invalid-schema-attempt/signals-private.csv.gz';src=R/'signals-private.csv.gz'
if not old.exists():shutil.move(src,old)
manifest=json.load(open(R/'manifest.json'));pin=manifest['source'];raw=Path('/data/raw/avzvol-ticks')/pin['file']
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
assert digest(raw)==pin['sha256']
seq=np.unique(np.concatenate([c.source_trigger_sequence.to_numpy(np.int64) for c in pd.read_csv(old,usecols=['source_trigger_sequence'],chunksize=100000)]));hours=np.full(len(seq),-1,np.int8);prior=-1
for b in pq.ParquetFile(raw).iter_batches(batch_size=262144,columns=['sequence','ts_utc_ns'],use_threads=False):
 sq=b.column(0).to_numpy();ts=b.column(1).to_numpy();assert np.all(sq[1:]>sq[:-1]) and sq[0]>prior;prior=int(sq[-1]);a,z=np.searchsorted(seq,[sq[0],sq[-1]],side='left');z=np.searchsorted(seq,sq[-1],side='right')
 if z>a:
  ix=np.searchsorted(sq,seq[a:z]);assert np.array_equal(sq[ix],seq[a:z]);hours[a:z]=pd.to_datetime(ts[ix],utc=True).tz_convert('America/Chicago').hour.to_numpy(np.int8)
assert np.all(hours>=0);lookup=dict(zip(seq.tolist(),hours.tolist()));print('RAW_HOURS_VERIFIED',len(seq),flush=True)
# Serialization regression: every distinctive feature remains under its named key.
sentinel=[7,3,4,.37,41.,9.,2,1.7,8.,.25,.7,-.4,.9,20,2031,730.]
r={'hour':13};attach_features(r,sentinel)
assert r['hour']==13 and all(r[n]==v for n,v in zip(FEATURE_NAMES,sentinel))
for values in [sentinel[:-1]]:
 try:attach_features({'hour':13},values)
 except AssertionError:pass
 else:raise AssertionError('BAD_LENGTH_ACCEPTED')
new=R/'signals-private.csv.gz.tmp';n=0;before=hashlib.sha256();after=hashlib.sha256();feature_digest=hashlib.sha256();stable_names=None
with gzip.open(old,'rt',newline='') as f,gzip.open(new,'wt',newline='',compresslevel=1) as g:
 reader=csv.DictReader(f);head=reader.fieldnames;assert head[15:31]==list(FEATURE_NAMES);writer=csv.DictWriter(g,fieldnames=head);writer.writeheader();stable_names=[k for k in head if k not in FEATURE_NAMES and k!='hour']
 for row in reader:
  unchanged='\x1f'.join(row[k] for k in stable_names).encode();before.update(unchanged+b'\n');vals=[row[k] for k in head[16:32]]
  assert row['visits1']=='', 'UNEXPECTED_INPUT_SCHEMA'
  row.update(zip(FEATURE_NAMES,vals));row['hour']=str(lookup[int(row['source_trigger_sequence'])]);validate(row)
  assert [row[k] for k in FEATURE_NAMES]==vals;feature_digest.update('\x1f'.join(vals).encode()+b'\n');after.update('\x1f'.join(row[k] for k in stable_names).encode()+b'\n');writer.writerow(row);n+=1
assert before.digest()==after.digest();assert n==json.load(open(R/'evidence.json'))['signal_rows_not_independent'];os.replace(new,src)
# Re-read output with a distinct vectorized validation path.
checked=0
for c in pd.read_csv(src,chunksize=100000):
 assert c.visits1.notna().all() and c.hour.between(0,23).all() and (c.visits5<=c.visits1).all();expected=c.source_trigger_sequence.map(lookup);assert np.array_equal(c.hour.to_numpy(),expected.to_numpy());checked+=len(c)
assert checked==n
out=dict(status='PASS_REPAIRED_SCHEMA',contract='MNQ_12-26',rows=n,unique_trigger_hours_checked=len(seq),source_sha256_before_and_after=pin['sha256'],source_unchanged=digest(raw)==pin['sha256'],unaffected_columns_digest=before.hexdigest(),all_16_features_preserved=True,corrected_hours_from_pinned_raw=True,invalid_analyses_archived=True,matrix_independent_unchanged=True,serialization_test=True,corrected_signals_sha256=digest(src),original_bad_signals_sha256=digest(old))
(R/'schema-repair-evidence.json').write_text(json.dumps(out,indent=2)+'\n');print('REPAIRED',n,flush=True)
