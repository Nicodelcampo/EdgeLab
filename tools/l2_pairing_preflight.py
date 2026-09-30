"""Instrument-neutral custody and exact ordered-tape preflight. Never outcomes."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq

class Abstain(ValueError):
    pass

def require(test, reason):
    if not test:
        raise Abstain(reason)

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def ordered_tape(left, right):
    """Arrays: timestamp_ns, integer price tick, volume; no nearest/rounding."""
    require(left.ndim==right.ndim==2 and left.shape[1]==right.shape[1]==3,
            "TAPE_SCHEMA_FAIL")
    require(np.issubdtype(left.dtype,np.integer) and np.issubdtype(right.dtype,np.integer),
            "INTEGER_TAPE_REQUIRED")
    if left.shape!=right.shape:
        return {"gate":"ABSTAIN_TAPE_LENGTH","l1_trades":len(left),"ticks":len(right)}
    columns=np.sum(left!=right,axis=0)
    rows=np.any(left!=right,axis=1)
    return {"gate":"PASS" if not rows.any() else "ABSTAIN_ORDERED_TAPE_IDENTITY",
            "l1_trades":len(left),"ticks":len(right),"mismatch_rows":int(rows.sum()),
            "timestamp_mismatches":int(columns[0]),"price_mismatches":int(columns[1]),
            "volume_mismatches":int(columns[2])}

def numeric_table(path, columns):
    pf=pq.ParquetFile(path)
    require(set(columns)<=set(pf.schema.names),"MISSING_NUMERIC_COLUMNS")
    t=pf.read(columns=columns)
    require(all(t.column(k).null_count==0 for k in columns),"NULL_INPUT")
    return {k:t.column(k).to_numpy(zero_copy_only=False) for k in columns}

def raw_checks(a, b, tick_size):
    for kind,d in (("l1",a),("l2",b)):
        require(len(d["source_row"])>0,"EMPTY_"+kind)
        require(np.all(np.diff(d["source_row"])>0),"SOURCE_ROW_ORDER_"+kind)
        require(np.all(np.diff(d["ts_us"])>=0),"CLOCK_ORDER_"+kind)
        for key in ("ts_us","source_row","price_tick","side"):
            require(np.issubdtype(d[key].dtype,np.integer),"INTEGER_"+kind+"_"+key)
        require(np.all(np.isfinite(d["size"])) and np.all(d["size"]>=0),"SIZE_"+kind)
        require(np.all(np.isfinite(d["price"])) and
                np.all(abs(d["price"]/tick_size-d["price_tick"])<=1e-6),"GRID_"+kind)
    # v2 L1 also contains DAILY_VOLUME and other non-trade market-data rows.
    # Keep them for mixed clock/order checks; only schema-declared LAST is tape.
    require(np.all(a["side"]>=0),"NEGATIVE_L1_SIDE_CODE")
    require(np.all(np.isin(b["side"],[0,1])),"L2_SIDE_CODE")
    require(np.all(np.isin(b["operation"],[0,1,2])),"L2_OPERATION_CODE")
    require(np.issubdtype(b["level"].dtype,np.integer) and
            np.issubdtype(b["operation"].dtype,np.integer),"INTEGER_L2_LEVEL_OPERATION")
    # MBP-10 visible depth is not an input level ceiling: canonical NT8 P-75
    # permits displaced-tail level10 and accounts EDGE_RESYNC in book replay.
    require(np.all(b["level"]>=0),"NEGATIVE_L2_LEVEL")
    require(not np.intersect1d(a["source_row"],b["source_row"]).size,"INTERLEAVED_ROW_COLLISION")
    # Check mixed-feed clock order without manufacturing missing publication.
    row=np.r_[a["source_row"],b["source_row"]]
    ts=np.r_[a["ts_us"],b["ts_us"]][np.argsort(row)]
    require(np.all(np.diff(ts)>=0),"MIXED_CLOCK_ORDER")

def tick_slice(path, start_ns, end_ns, instrument, contract, boundary):
    pf=pq.ParquetFile(path)
    cols=["ts_utc_ns","price_ticks","volume","instrument","contract","tick_type"]
    require(set(cols)<=set(pf.schema.names),"MISSING_TICK_COLUMNS")
    selected=[]
    for i in range(pf.num_row_groups):
        st=pf.metadata.row_group(i).column(pf.schema.names.index("ts_utc_ns")).statistics
        if st is not None and (st.max<start_ns or st.min>end_ns): continue
        for batch in pf.iter_batches(batch_size=250000,row_groups=[i],columns=cols):
            ts=batch.column(0).to_numpy(zero_copy_only=False)
            require(batch.column(0).null_count==0,"NULL_TICK_CLOCK")
            mask=(ts>=start_ns)&(ts<=end_ns)
            if not mask.any(): continue
            require(all(batch.column(k).null_count==0 for k in range(6)),"NULL_TICK_INPUT")
            for k,label in ((3,instrument),(4,contract),(5,"trade")):
                require(all(v==label for v,m in zip(batch.column(k).to_pylist(),mask) if m),
                        "TICK_INSTRUMENT_CONTRACT_OR_TYPE")
            price=batch.column(1).to_numpy(zero_copy_only=False)[mask]
            volume=batch.column(2).to_numpy(zero_copy_only=False)[mask]
            require(np.issubdtype(ts.dtype,np.integer) and np.issubdtype(price.dtype,np.integer)
                    and np.issubdtype(volume.dtype,np.integer),"INTEGER_TICK_TAPE")
            require(np.all(volume>0),"NONPOSITIVE_TRADE_VOLUME")
            require(np.all(ts[mask]<boundary),"HOLDOUT_ROW")
            selected.append(np.column_stack([ts[mask],price,volume]))
    out=np.concatenate(selected) if selected else np.empty((0,3),dtype=np.int64)
    require(np.all(np.diff(out[:,0])>=0),"TICK_CLOCK_ORDER")
    return out

def audit(config):
    e={"schema":"edgelab.l2_pairing_preflight/1","scope":"CUSTODY_TAPE_PREFLIGHT_NOT_BOOK_VALIDATION",
       "instrument":config.get("instrument"),"session":config.get("session"),
       "outcomes_computed":False,"models_fitted":0,
       "book_replay_gate":"NOT_RUN","predictive_run_gate":"STOP_MANIFEST_AND_APPROVAL_REQUIRED"}
    try:
        require(config.get("instrument") in ("GC","ES"),"EXPLICIT_INSTRUMENT_REQUIRED")
        require(type(config.get("clock_offset_ns")) is int,"EXPLICIT_INTEGER_CLOCK_OFFSET_REQUIRED")
        require(bool(config.get("clock_resolution_source")),"CLOCK_PROVENANCE_REQUIRED")
        require(type(config.get("holdout_boundary_ns")) is int,"EXPLICIT_BOUNDARY_REQUIRED")
        require(type(config.get("tick_size")) in (float,int) and config["tick_size"]>0,
                "TICK_SIZE_REQUIRED")
        files=config.get("files",{})
        require(set(files)=={"ticks","l1","l2","session_manifest"},"INPUT_SET_REQUIRED")
        checks={}
        for label,item in files.items():
            require(Path(item["path"]).is_file(),"MISSING_FILE_"+label)
            actual=sha256(item["path"]);require(actual==item.get("sha256"),"HASH_FAIL_"+label)
            checks[label]=actual
        e["input_sha256"]=checks
        m=json.loads(Path(files["session_manifest"]["path"]).read_text())
        require(m["instrument"]==config["contract"],"MANIFEST_CONTRACT_FAIL")
        require(m.get("session_name")==config.get("session"),"MANIFEST_SESSION_FAIL")
        require(m["conversion"]["tick_size"]==config["tick_size"],"MANIFEST_TICK_SIZE_FAIL")
        for kind,label in (("l1_quotes","l1"),("l2_depth","l2")):
            require(m["outputs"][kind]["sha256"]==checks[label],"MANIFEST_RAW_HASH_"+label)
        metadata=pq.ParquetFile(files["l1"]["path"]).schema_arrow.metadata or {}
        require(metadata.get(b"edgelab_schema")==b"nt8_l1_quotes_trades_v2" and
                b"2=LAST" in metadata.get(b"side_codes",b""),"EXPLICIT_LAST_SCHEMA_REQUIRED")
        l2meta=pq.ParquetFile(files["l2"]["path"]).schema_arrow.metadata or {}
        require(l2meta.get(b"edgelab_schema")==b"nt8_l2_depth_v2","EXPLICIT_L2_SCHEMA_REQUIRED")
        a=numeric_table(files["l1"]["path"],["source_row","ts_us","price_tick","price","size","side"])
        b=numeric_table(files["l2"]["path"],["source_row","ts_us","price_tick","price","size","side","level","operation"])
        raw_checks(a,b,config["tick_size"])
        for kind,d in (("l1_quotes",a),("l2_depth",b)):
            require(len(d["ts_us"])==m["outputs"][kind]["rows"],"MANIFEST_ROW_COUNT")
        require(np.all((np.r_[a["ts_us"],b["ts_us"]]*1000+config["clock_offset_ns"])
                       <config["holdout_boundary_ns"]),"HOLDOUT_RAW_ROW")
        tr=a["side"]==2
        require(tr.any(),"NO_TRADE_PRINTS")
        require(np.all(a["size"][tr]>0) and np.all(a["size"][tr]==np.floor(a["size"][tr])),
                "INTEGER_TRADE_SIZE_REQUIRED")
        left=np.column_stack([a["ts_us"][tr]*1000+config["clock_offset_ns"],
                              a["price_tick"][tr],a["size"][tr].astype(np.int64)])
        right=tick_slice(files["ticks"]["path"],int(left[0,0]),int(left[-1,0]),
                         config["instrument"],config["contract"],config["holdout_boundary_ns"])
        e["tape"]=ordered_tape(left,right);e["gate"]=e["tape"]["gate"]
        e["clock_scope"]="EXPLICIT_OFFSET_EXACT_ORDERED_TAPE_ONLY_NOT_ABSOLUTE_CLOCK_CERTIFICATE"
        e["nearest_or_rounding_used"]=False
    except (Abstain,KeyError,TypeError,ValueError,OSError) as exc:
        e["gate"]="ABSTAIN";e["reason"]=str(exc)
    return e

def main():
    p=argparse.ArgumentParser();p.add_argument("--config",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();out=Path(a.out);require(not out.exists(),"NEW_OUTPUT_REQUIRED")
    e=audit(json.loads(Path(a.config).read_text()))
    e["config_sha256"]=sha256(a.config);e["runner_sha256"]=sha256(__file__)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(e,indent=2))
    print(json.dumps(e))
    # Completed audit with ABSTAIN is a valid result, not permission for replay.

if __name__=="__main__": main()