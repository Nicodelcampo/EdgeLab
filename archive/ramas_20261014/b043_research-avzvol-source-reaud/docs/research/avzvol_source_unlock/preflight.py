from pathlib import Path
import json,hashlib
import pyarrow.parquet as pq,pandas as pd
root=Path('/data/raw/avzvol-ticks');dst=Path('/data/analysis/avzvol-source-unlock');prior=json.loads(Path('/data/edgelab-parameter-grid/config/research/avzvol_mnq_raw_quality_review_20261010.json').read_text());cut=pd.Timestamp('2026-09-30T22:00:00Z').value;rows=[]
for source in prior['files']:
 pin=source['structural_audit'];path=root/Path(pin['dataset_file']).name
 with path.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
 assert path.stat().st_size==pin['bytes'] and sha==pin['sha256'];pf=pq.ParquetFile(path);assert pf.metadata.num_rows==pin['rows'];ix=pf.schema_arrow.names.index('ts_utc_ns');maximum=max(pf.metadata.row_group(i).column(ix).statistics.max for i in range(pf.num_row_groups));assert maximum<cut
 rows.append({'contract':source['candidate_contract'],'file':path.name,'dataset':pin['dataset_ref'],'version':pin['dataset_version'],'sha256':sha,'bytes':path.stat().st_size,'rows':pin['rows'],'max_ns':int(maximum),'preholdout':True,'prior_structural_errors':sum(pin['errors'].values()),'prior_evidence_byte_identical':True})
assert len(rows)==6
(dst/'preflight.json').write_text(json.dumps({'global_all_six_passed':True,'files':rows,'raw_price_payload_read':False,'source_quality_certified':False},indent=2));print('GLOBAL PREFLIGHT: six exact pins, all rows strictly preholdout;',sum(r['rows'] for r in rows),'rows')
