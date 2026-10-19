#!/usr/bin/env python3
"""Responde «¿qué datos hay de X entre estas fechas y de dónde los saco?» usando docs/data_catalog/catalog.json.
  python tools/data_find.py --instrument GC --from 2026-01-01 --to 2026-03-31
  python tools/data_find.py --list"""
import argparse,json
from pathlib import Path
CAT=Path(__file__).resolve().parents[1]/"docs/data_catalog/catalog.json"

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--instrument");ap.add_argument("--from",dest="d0");ap.add_argument("--to",dest="d1");ap.add_argument("--list",action="store_true");a=ap.parse_args();c=json.loads(CAT.read_text());I=c["instruments"]
    if a.list or not a.instrument:
        for s,v in I.items():print(f"{s:5} {v['first_date']}..{v['last_date']}  sesiones {v['sessions_with_data']:4}  elegibles {v['eligible_sessions']:4}  contratos {len(v['contracts'])}")
        return
    v=I.get(a.instrument.upper())
    if v is None:raise SystemExit(f"instrumento desconocido; hay: {', '.join(I)}")
    d0=a.d0 or "0000-00-00";d1=a.d1 or "9999-99-99";print(f"{a.instrument.upper()}: tick {v['tick_size']} = USD {v['tick_value_usd']}. Holdout formal desde {c['holdout_first_trade_date']} (no leer).")
    print("\nContratos que tocan el rango:")
    for k,x in v["contracts"].items():
        if x["last"]>=d0 and x["first"]<=d1:
            print(f"  {k}: {x['first']}..{x['last']} ({x['sessions']} sesiones)")
            for s in x["sources"]:print(f"     python tools/kaggle_data.py get nicolasbuttaro/{s['dataset']} {s['file']} --out /data/raw/{a.instrument.upper()}   # {s['first']}..{s['last']}, libro={'sí' if s['has_book'] else 'no'}")
    print("\nLíder por tramo:")
    for s in v["leader_segments"]:
        if s["last"]>=d0 and s["first"]<=d1:print(f"  {s['contract']}: {s['first']}..{s['last']}")
    print("\nDías hábiles sin datos y sin explicación:",", ".join(v["missing_weekdays"]["unexplained"]) or "ninguno")
    print("Sesiones no elegibles por liquidez en el rango:",", ".join(r for r in v["ineligible_low_volume"]["ranges"] if r[:10]<=d1 and r[-10:]>=d0) or "ninguna")
    for k in v["source_conflicts"]:
        if k["days_different"]:print(f"AVISO fuentes que difieren en {k['contract']}: {k['a']} vs {k['b']} ({k['days_different']} días)")
if __name__=="__main__":main()
