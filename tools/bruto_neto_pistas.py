#!/usr/bin/env python3
"""¿Señal bruta o fricción? Bruto contra neto de las pistas en la réplica (protocolo: docs/research/bruto_neto_pistas_20261108/).

Reutiliza `equity_pistas` (lanzar / traer: ANALIZAR_REGLA con operaciones sobre las pistas congeladas, DESC + réplica) apuntado a otra
carpeta, y la fricción canónica de `embudo_runners.friccion`. EXPLORATORIO: nada se promueve desde acá.

  python tools/bruto_neto_pistas.py lanzar [CID ...]     # sin CID: todas las campañas en R con pistas en réplica
  python tools/bruto_neto_pistas.py traer
  python tools/bruto_neto_pistas.py analizar
"""
import argparse, glob, json, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import equity_pistas as EP  # noqa: E402

EP.SALIDA = ROOT / "docs/research/bruto_neto_pistas_20261108"


def campanas() -> list:
    out = []
    for f in sorted(glob.glob(str(ROOT / "docs/research/*/embudo/*/estado.json"))):
        st = json.loads(Path(f).read_text(encoding="utf-8")); pr = st.get("pistas_replica") or {}; sp = st.get("spec") or {}
        if pr.get("celdas") and pr.get("canasta") and sp.get("estadistico") == "R": out.append(sp["cid"])
    return out


def _canasta(ses, x, k, B=2000, seed=0):
    """Media por sesión (suma / k), media de sesiones e IC90 por bootstrap de sesiones."""
    u, inv = np.unique(ses, return_inverse=True); s = np.bincount(inv, weights=x) / k
    if len(s) < 2: return float(s.mean()) if len(s) else float("nan"), [float("nan")] * 2, len(s)
    rng = np.random.default_rng(seed); bs = s[rng.integers(0, len(s), (B, len(s)))].mean(1)
    return float(s.mean()), [float(np.quantile(bs, 0.05)), float(np.quantile(bs, 0.95))], len(s)


def clasificar(b_m, b_ic, n_m, n_ic, costo):
    if np.isfinite(n_ic[0]) and n_ic[0] > 0: return "SEÑAL_NETA"
    if np.isfinite(b_ic[0]) and b_ic[0] > 0 and n_m <= 0: return "FRICCION"
    if b_m <= 0 or (np.isfinite(b_ic[1]) and b_ic[1] <= costo): return "SIN_SEÑAL"
    return "INDETERMINADO"


def analizar():
    from edgelab.research.embudo_runners import friccion
    hs = json.loads((EP.SALIDA / "handles.json").read_text()); filas = []
    for cid, h in sorted(hs.items()):
        f = EP.SALIDA / f"{cid}.json"
        if not f.exists(): continue
        r = json.loads(f.read_text()); o = r.get("operaciones") or {}
        if not o: continue
        st = EP._estado(cid); sp = st["spec"]; fr = friccion(sp.get("ejecucion") or sp["sensor"])[0]
        ses = np.asarray(o["ses"], np.int64); net = np.asarray(o["neto"], float); rg = np.asarray(o["riesgo"], float)
        ok = np.isfinite(net) & np.isfinite(rg) & (rg > 0); ses, net, rg = ses[ok], net[ok], rg[ok]
        costo = fr / rg; bru = net + costo; k = len(r["reportes"]); oos = int(sp["oos"][0]); fila = dict(cid=cid, k=k, friccion_pts=fr)
        for nom, m in (("desc", ses < oos), ("rep", ses >= oos)):
            bm, bic, ns = _canasta(ses[m], bru[m], k); nm, nic, _ = _canasta(ses[m], net[m], k)
            fila[nom] = dict(sesiones=ns, ops=int(m.sum()), bruto=bm, bruto_ic90=bic, neto=nm, neto_ic90=nic,
                             costo_r_medio=float(costo[m].mean()) if m.any() else float("nan"))
        rp = fila["rep"]; fila["clase"] = clasificar(rp["bruto"], rp["bruto_ic90"], rp["neto"], rp["neto_ic90"], rp["costo_r_medio"])
        filas.append(fila)
    (EP.SALIDA / "RESULTADOS.json").write_text(json.dumps(filas, indent=1, ensure_ascii=False, default=float))
    from collections import Counter
    print(Counter(f["clase"] for f in filas), len(filas))
    for f in filas:
        d, r = f["desc"], f["rep"]
        print(f"{f['cid']:28s} {f['clase']:13s} rep bruto {r['bruto']:+.3f} [{r['bruto_ic90'][0]:+.3f},{r['bruto_ic90'][1]:+.3f}] "
              f"neto {r['neto']:+.3f} costo {r['costo_r_medio']:.3f} ses {r['sesiones']:4d} | desc bruto {d['bruto']:+.3f} neto {d['neto']:+.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["lanzar", "traer", "analizar"]); ap.add_argument("cids", nargs="*")
    a = ap.parse_args()
    if a.cmd == "lanzar": EP.lanzar(a.cids or campanas())
    elif a.cmd == "traer": EP.traer()
    else: analizar()
