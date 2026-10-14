from pathlib import Path
import hashlib,json
import pyarrow as pa,pyarrow.parquet as pq

def write_survivors(rows,path,metadata):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);t=pa.Table.from_pylist(rows);md={str(k):str(v) for k,v in metadata.items()};t=t.replace_schema_metadata({k.encode():v.encode() for k,v in md.items()});pq.write_table(t,p,compression="zstd");return {"path":str(p),"rows":len(rows),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"metadata":md}
