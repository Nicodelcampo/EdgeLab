#!/usr/bin/env python3
"""Arma el caché (barras + filas de ejecución) y la auditoría de datos de uno o más activos. Una sola lectura de ticks para todas las familias.
  python tools/discovery_cache.py --asset config/discovery/assets/GC.json,... --spec config/discovery/families/f1_momentum.json --cache /data/cache/discovery --audit-out artifacts/discovery/audit
La auditoría es descriptiva: no excluye nada."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.discovery import load_spec,cache as CA

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--asset",required=True);ap.add_argument("--spec",required=True);ap.add_argument("--cache",required=True);ap.add_argument("--audit-out",default=None);ap.add_argument("--force",action="store_true");a=ap.parse_args()
    spec=load_spec(a.spec)
    for ap_ in a.asset.split(","):
        asset=json.loads(Path(ap_).read_text());sp=spec.__class__(**{**spec.__dict__,"commission_ticks":asset["commission_usd_rt"]/asset["tick_value_usd"]})
        if a.force or not CA.cache_ok(asset,sp,a.cache):print(asset["root"],"armando caché…",flush=True);CA.build_cache(asset,sp,a.cache)
        else:print(asset["root"],"caché vigente",flush=True)
        if a.audit_out:
            rep=CA.asset_audit(asset,a.cache);o=Path(a.audit_out);o.mkdir(parents=True,exist_ok=True);(o/f"audit_{asset['root']}.json").write_text(json.dumps(rep,indent=1,default=float));print(asset["root"],"auditoría escrita")
if __name__=="__main__":main()
