"""Del escaneo crudo (/data/catalog/{datasets.json,scan,text}) al catálogo por instrumento: contratos, fuentes, serie líder y rolls,
elegibilidad por liquidez, días faltantes, sesiones cortas, solapes entre datasets y custodia del holdout."""
from __future__ import annotations
import datetime as dt,glob,json,re
from collections import defaultdict
from pathlib import Path
import numpy as np
from ..discovery import data as D

CONTRACT_RE=re.compile(r"(?P<root>[A-Z0-9]+)[ _-](?P<mm>\d{2})-(?P<yy>\d{2})")
SPECS={ # tamaño de tick y valor por tick en USD (por contrato); verificar antes de usar un instrumento nuevo
 "GC":(0.1,10.0),"MGC":(0.1,1.0),"ES":(0.25,12.5),"MES":(0.25,1.25),"NQ":(0.25,5.0),"MNQ":(0.25,0.5),"YM":(1.0,5.0),"MYM":(1.0,0.5),"RTY":(0.1,5.0),
 "ZB":(1/32,31.25),"6E":(0.00005,6.25),"6J":(0.0000005,6.25),"6B":(0.0001,6.25)}
CYCLES={"GC":(2,4,6,8,10,12),"MGC":(2,4,6,8,10,12),"ES":(3,6,9,12),"MES":(3,6,9,12),"NQ":(3,6,9,12),"MNQ":(3,6,9,12),"YM":(3,6,9,12),"MYM":(3,6,9,12),"RTY":(3,6,9,12),
        "ZB":(3,6,9,12),"6E":(3,6,9,12),"6J":(3,6,9,12),"6B":(3,6,9,12)}      # meses de vencimiento de la serie estándar
HOLDOUT_FIRST=dt.date(2026,10,1).toordinal()          # HOLDOUT-A1: holdout formal = sesiones de trading desde 2026-10-01
CUT_PRE=dt.date(2026,6,30).toordinal()

def iso(o:int)->str:return dt.date.fromordinal(int(o)).isoformat()
def ranges(ords:list[int])->list[str]:
    ords=sorted(ords);out=[];i=0
    while i<len(ords):
        j=i
        while j+1<len(ords) and ords[j+1]-ords[j]==1:j+=1
        out.append(iso(ords[i]) if i==j else f"{iso(ords[i])}..{iso(ords[j])}");i=j+1
    return out

def parse_contract(file:str,scan:dict)->tuple[str,str]:
    m=CONTRACT_RE.search(Path(file).name)
    c=None
    if scan.get("contracts_in_file"):
        m2=CONTRACT_RE.search(scan["contracts_in_file"][0])
        if m2:c=(m2["root"],f"{m2['mm']}-{m2['yy']}")
    if m:f=(m["root"],f"{m['mm']}-{m['yy']}");return f if (c is None or c==f) else f
    return c if c else ("?","?")

def _holidays(lo:int,hi:int)->set[int]:
    from pandas.tseries.holiday import USFederalHolidayCalendar
    from dateutil.easter import easter
    h={d.date().toordinal() for d in USFederalHolidayCalendar().holidays(iso(lo),iso(hi))}
    for y in range(dt.date.fromordinal(lo).year,dt.date.fromordinal(hi).year+1):h.add((easter(y)-dt.timedelta(days=2)).toordinal())
    return h

def load_scans(root:Path)->list[dict]:
    out=[]
    for f in sorted(glob.glob(str(root/"scan"/"*"/"*.json"))):out.append(json.loads(Path(f).read_text()))
    return out

def build(root:Path)->dict:
    listing=json.loads((root/"datasets.json").read_text());scans=load_scans(root);by_ds=defaultdict(list)
    for s in scans:by_ds[s["dataset"]].append(s)
    datasets=[]
    for d in listing:
        files=d["files"];tick=[s for s in by_ds.get(d["slug"],[]) if s.get("recognized")];other=[s for s in by_ds.get(d["slug"],[]) if not s.get("recognized")]
        kind="ticks" if tick else ("tabular/otro" if other else ("codigo" if "code" in d["slug"] else "artefactos/evidencia"))
        rd=root/"text"/d["slug"]/"README.md";readme=rd.read_text()[:1500] if rd.exists() else None
        datasets.append({"slug":d["slug"],"private":d["private"],"bytes":d["bytes"],"last_updated":d["last_updated"],"kind":kind,"n_files":len(files),"readme_excerpt":readme,
                         "tick_files":[s["file"] for s in tick],"unrecognized_parquet":[{"file":s["file"],"columns":s["columns"]} for s in other],"top_level_files":[f["name"] for f in files if "/" not in f["name"]][:40]})
    # --- fuentes por contrato
    files=[];spot=defaultdict(lambda:{"ticks":{},"m1":{}})
    SPOT_RE=re.compile(r"(?P<sym>[A-Z]{6})_(?:m1_)?(?P<ym>\d{4}-\d{2})")
    for s in scans:
        if s.get("recognized") and s.get("quote_only") and s.get("days"):
            m=SPOT_RE.search(Path(s["file"]).name)
            if m:
                kind="m1" if s.get("kind")=="m1_bars" else "ticks";d=s["days"]
                spot[m["sym"]][kind][m["ym"]]={"dataset":s["dataset"],"file":s["file"],"rows":s["rows"],"first_date":iso(d[0]["td"]),"last_date":iso(d[-1]["td"]),"sessions":len(d),"events_or_nonzero_bars":int(sum(x["trades"] for x in d)),
                    "unsorted":s["unsorted_events"],"price_min":s.get("price_ticks_min"),"price_max":s.get("price_ticks_max"),"post_holdout_sessions":sum(1 for x in d if x["td"]>=HOLDOUT_FIRST)}
            continue
        if not s.get("recognized") or not s.get("days"):continue
        root_sym,exp=parse_contract(s["file"],s);days=s["days"]
        files.append({"dataset":s["dataset"],"file":s["file"],"instrument":root_sym,"contract":f"{root_sym}_{exp}","bytes":s["bytes"],"rows":s["rows"],"trades":s["trades"],
            "first_trade_date":iso(days[0]["td"]),"last_trade_date":iso(days[-1]["td"]),"sessions":len(days),"first_ts_utc":s["ts_utc_first"],"last_ts_utc":s["ts_utc_last"],
            "tick_types":s["tick_types"],"has_book":s["has_book"],"has_aggressor":s["has_aggressor"],"aggressor":s["aggressor"],"unsorted_events":s["unsorted_events"],"crossed_book":s["crossed_book"],
            "no_book_le_0":s["no_book_le_0"],"contracts_in_file":s["contracts_in_file"],"price_ticks_range":[s["price_ticks_min"],s["price_ticks_max"]],"source":s.get("source"),
            "post_holdout_sessions":sum(1 for x in days if x["td"]>=HOLDOUT_FIRST),"days":days})
    inst=defaultdict(lambda:defaultdict(list))
    for f in files:inst[f["instrument"]][f["contract"]].append(f)
    instruments={}
    for sym,cons in sorted(inst.items()):
        def key(c):mm,yy=c.split("_")[1].split("-");return (int(yy),int(mm))
        order=sorted(cons,key=key);daily={};cinfo={};conflicts=[]
        for c in order:
            srcs=cons[c];dd={}
            for f in srcs:
                for x in f["days"]:
                    cur=dd.get(x["td"])
                    if cur is None or x["volume"]>cur["volume"]:dd[x["td"]]=x
            daily[c]={t:v["volume"] for t,v in dd.items()}
            if len(srcs)>1:
                a=srcs[0];both=0;eq=0;diffs=[]
                for b in srcs[1:]:
                    da={x["td"]:x for x in a["days"]};db={x["td"]:x for x in b["days"]};common=sorted(set(da)&set(db))
                    both=len(common);eq=sum(1 for t in common if da[t]["trades"]==db[t]["trades"]);diffs=[abs(da[t]["trades"]-db[t]["trades"])/max(1,max(da[t]["trades"],db[t]["trades"])) for t in common if da[t]["trades"]!=db[t]["trades"]]
                    conflicts.append({"contract":c,"a":f"{a['dataset']}:{a['file']}","b":f"{b['dataset']}:{b['file']}","days_a":len(da),"days_b":len(db),"days_common":both,"days_identical_trades":eq,"days_different":both-eq,
                                      "max_rel_diff":round(max(diffs),4) if diffs else 0.0,"days_rel_diff_gt_1pct":sum(1 for x in diffs if x>0.01),"days_a_more_trades":sum(1 for t in common if da[t]["trades"]>db[t]["trades"]),"days_b_more_trades":sum(1 for t in common if db[t]["trades"]>da[t]["trades"]),
                                      "median_ratio_a_over_b_on_differing_days":round(float(np.median([da[t]["trades"]/max(1,db[t]["trades"]) for t in common if da[t]["trades"]!=db[t]["trades"]])),3) if both-eq else None,"only_in_a":ranges(list(set(da)-set(db)))[:12],"only_in_b":ranges(list(set(db)-set(da)))[:12]})
            allt=sorted(daily[c]);cinfo[c]={"first":iso(allt[0]),"last":iso(allt[-1]),"sessions":len(allt),"trades":int(sum(x["trades"] for x in dd.values())),"sources":[{"dataset":f["dataset"],"file":f["file"],"sessions":f["sessions"],"trades":f["trades"],"first":f["first_trade_date"],"last":f["last_trade_date"],"has_book":f["has_book"],"has_aggressor":f["has_aggressor"]} for f in srcs]}
        segs,elig=D.continuous_segments(daily,order,0.5)
        allt=sorted({t for c in order for t in daily[c]});lo,hi=allt[0],allt[-1];hol=_holidays(lo,hi)
        missing=[t for t in range(lo,hi+1) if dt.date.fromordinal(t).weekday()<5 and t not in set(allt)]
        miss_unexpl=[t for t in missing if t not in hol];miss_hol=[t for t in missing if t in hol]
        minutes={t:max((x["minutes"] for f in cons[c] for x in f["days"] if x["td"]==t) or [0]) if False else None for c in order for t in []}
        leader_minutes={}
        for c in order:
            for f in cons[c]:
                for x in f["days"]:
                    if elig.get(x["td"])==order.index(c):leader_minutes[x["td"]]=max(leader_minutes.get(x["td"],0),x["minutes"])
        med_m=float(np.median(list(leader_minutes.values()))) if leader_minutes else 0.
        thin=[t for t,m in leader_minutes.items() if m<0.5*med_m]
        rolls=[]
        for k in range(1,len(segs)):
            r,d0,_=segs[k];old=order[segs[k-1][0]];new=order[r];prev=[t for t in range(d0-1,d0-8,-1) if t in daily[old] and t in daily[new]]
            rec={"from":old,"to":new,"first_session_as_leader":iso(d0)}
            if prev:p=prev[0];rec.update({"previous_session":iso(p),"volume_old":daily[old][p],"volume_new":daily[new][p],"ratio_new_over_old":round(daily[new][p]/max(1.,daily[old][p]),2)})
            rolls.append(rec)
        inelig=[t for r,d0,d1 in segs for t in range(d0,d1+1) if t in daily[order[r]] and t not in elig]
        gaps_in_life=[]
        for c in order:
            ts=sorted(daily[c]);gaps=[(a,b) for a,b in zip(ts[:-1],ts[1:]) if b-a>5]
            if gaps:gaps_in_life.append({"contract":c,"gaps":[f"{iso(a)}->{iso(b)}" for a,b in gaps]})
        # contratos del ciclo estándar que deberían ser líder en algún momento del rango y no están en los datos
        exp_missing=[]
        if sym in CYCLES:
            y0,y1=dt.date.fromordinal(lo).year,dt.date.fromordinal(hi).year+1
            for y in range(y0,y1+1):
                for mth in CYCLES[sym]:
                    lab=f"{sym}_{mth:02d}-{y%100:02d}";life_end=dt.date(y,mth,28).toordinal();life_start=life_end-100
                    if lab not in cons and life_start<=hi and life_end>=lo and life_end-30<=hi:exp_missing.append(lab)
        lv=[daily[order[r]][t] for r,d0,d1 in segs for t in range(d0,d1+1) if t in elig and elig[t]==r and t in daily[order[r]]];med_lv=float(np.median(lv)) if lv else 0.
        thin_vs=[t for t in elig if daily[order[elig[t]]].get(t,0)<0.25*med_lv]
        tk,tv=SPECS.get(sym,(None,None))
        instruments[sym]={"tick_size":tk,"tick_value_usd":tv,"first_date":iso(lo),"last_date":iso(hi),"sessions_with_data":len(allt),"contracts":cinfo,
            "leader_segments":[{"contract":order[r],"first":iso(a),"last":iso(b)} for r,a,b in segs],"rolls":rolls,"eligible_sessions":len(elig),
            "ineligible_low_volume":{"n":len(inelig),"ranges":ranges(inelig)[:40]},"missing_weekdays":{"holidays":[iso(t) for t in miss_hol],"unexplained":ranges(miss_unexpl)},
            "thin_leader_sessions(<50%_of_median_minutes)":[iso(t) for t in sorted(thin)],"gaps_inside_contract_life(>5_days)":gaps_in_life,"source_conflicts":conflicts,
            "expected_contracts_missing":exp_missing,"leader_median_daily_volume":med_lv,"leader_sessions_below_25pct_of_instrument_median":{"n":len(thin_vs),"ranges":ranges(thin_vs)[:40]},"post_holdout_sessions":sum(1 for t in allt if t>=HOLDOUT_FIRST),"data_after_2026-06-30_present":any(t>CUT_PRE for t in allt)}
    spot_out={}
    for sym,v in spot.items():
        months=sorted(set(v["ticks"])|set(v["m1"]));y0,m0=map(int,months[0].split("-"));y1,m1_=map(int,months[-1].split("-"));allm=[]
        y,m=y0,m0
        while (y,m)<=(y1,m1_):allm.append(f"{y:04d}-{m:02d}");m+=1;y,m=(y+1,1) if m==13 else (y,m)
        qa=root/"text"/"edgelab-dukascopy-xauusd-ticks-m1"/"calidad.json";qual=json.loads(qa.read_text()) if qa.exists() else None
        spot_out[sym]={"ticks_months":sorted(v["ticks"]),"m1_months":sorted(v["m1"]),"missing_months_in_range":[x for x in allm if x not in v["ticks"]],"files":v,"timezone":"UTC",
                       "price_fields":"bid/ask (spot cotizado, sin operaciones ni volumen real)","quality_file_days":len(qual["dias"]) if qual and "dias" in qual else None,
                       "post_holdout_sessions":sum(x["post_holdout_sessions"] for x in v["ticks"].values())}
    return {"generated_utc":dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),"holdout_first_trade_date":iso(HOLDOUT_FIRST),"datasets":datasets,
            "tick_files":[{k:v for k,v in f.items() if k!="days"} for f in files],"instruments":instruments,"spot_series":spot_out}
