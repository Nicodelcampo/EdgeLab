#!/usr/bin/env python3
"""CARRIL2-CIERRE (pre-registro docs/research/carril2_20261119/PREREGISTRO_CIERRE.md): las reglas del lote 1 entrando a las 15:56 (cierre RTH)
con señales de la barra RTH. Mismo motor (sqx_catalogo.simular, K28) y mismas señales (carril2._senales); sólo cambian las barras.

  python tools/carril2_cierre.py correr    # → OPS_CIERRE.csv.gz
  python tools/carril2_cierre.py desc      # → DESC_CIERRE.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/carril2_20261119"; PRE = "docs/research/carril2_20261119/PREREGISTRO_CIERRE.md"; FIN = 20250731


def barras(D):
    """Barra de ejecución 15:56 → 15:55 (fecha = día del cierre; viernes 15:56 en adelante va al lunes) y barra RTH 09:30–15:55 del mismo día."""
    clave = (D.index + pd.Timedelta(hours=8, minutes=4)).normalize()
    dow = clave.dayofweek; clave = clave + pd.to_timedelta(np.where(dow == 5, 2, np.where(dow == 6, 1, 0)), unit="D")
    g = D.groupby(clave); E = pd.DataFrame(dict(o=g.o.first(), h=g.h.max(), l=g.l.min(), c=g.c.last(), v=g.v.sum(), t0=g.apply(lambda x: x.index[0])))
    mm = D.index.hour * 60 + D.index.minute; R = D[(mm >= 570) & (mm < 956)]; gr = R.groupby(R.index.normalize())
    Rt = pd.DataFrame(dict(o=gr.o.first(), h=gr.h.max(), l=gr.l.min(), c=gr.c.last()))
    E = E[E.index.isin(Rt.index)]                                                  # sólo días con sesión RTH
    E["fecha"] = np.asarray(E.index.strftime("%Y%m%d"), dtype=np.int64); E["dow"] = E.index.dayofweek
    Rt = Rt.reindex(E.index); Rt["fecha"] = E.fecha.values; Rt["dow"] = E.dow.values
    t = D.index.values; a = np.searchsorted(t, E.t0.values); b = np.r_[a[1:], len(t)]
    m1 = dict(o=D.o.to_numpy(float), h=D.h.to_numpy(float), l=D.l.to_numpy(float), a=a, b=b)
    return E.reset_index(drop=True), Rt.reset_index(drop=True), m1


def correr():
    from registro_global import exigir_contada
    from datos import ruta
    from m1_largo import cargar
    from edgelab.research import sqx_catalogo as Q
    from edgelab.research.embudo_runners import friccion
    from edgelab.holdout import a5_bloque
    import carril2 as C
    exigir_contada(PRE)
    V = pd.read_parquet(Path(ruta("M1NT8")) / "cboe_volatility_daily.parquet"); vc = V.vix_close.copy(); vc.index = pd.to_datetime(vc.index).normalize()
    vix_reg = (vc > vc.rolling(100).mean()).shift(1); partes = []
    for inst in sorted({i for v in C.INST.values() for i in v}):
        D = cargar(inst, ruta("M1NT8")); E, Rt, m1 = barras(D)
        vix_ok = vix_reg.reindex(pd.to_datetime(Rt.fecha.astype(str))).fillna(False).to_numpy(bool)
        S = C._senales(Rt, vix_ok); fr = float(friccion(inst)[0]); f = E.fecha.to_numpy()
        for d, sig in S.items():
            regla = d[:-1] if d.endswith("N") and d[:-1] in C.REGLAS else d
            if inst not in C.INST[regla] or d.endswith("N"): continue
            O = Q.simular(E, sig, viernes=False, m1=m1)
            if not len(O): continue
            rg = (O.entrada - O.stop0).abs(); O["R"] = (O.lado * (O.salida_px - O.entrada) - fr) / rg; O["Rb"] = O.lado * (O.salida_px - O.entrada) / rg
            O["fecha_salida"] = f[np.minimum(O.i0 + O.barras - 1, len(f) - 1)]; O["fecha_senal"] = f[np.maximum(O.i0 - 1, 0)]
            O["definicion"], O["inst"] = d, inst; partes.append(O[O.stop0.notna() & (rg > 0)])
        print(inst, flush=True)
    T = pd.concat(partes, ignore_index=True)
    bl = {int(x): a5_bloque(int(x)) for x in pd.unique(np.r_[T.fecha.to_numpy(), T.fecha_salida.to_numpy()])}
    T["bloque"] = T.fecha.map(bl); T["bloque_salida"] = T.fecha_salida.map(bl)
    T = T[(T.fecha_salida <= FIN) & T.bloque.isin(["DESC", "REP"]) & ~T.bloque_salida.isin(["HOLDOUT", "EMBARGO"])]
    assert not T.bloque_salida.isin(["HOLDOUT", "EMBARGO"]).any()
    T.to_csv(DIR / "OPS_CIERRE.csv.gz", index=False); print(T.groupby(["definicion", "bloque"]).size().unstack().to_string())


def desc():
    from carril2 import _media, REGLAS
    from edgelab.research import a5 as A5
    from edgelab.research.a5 import bh
    from edgelab.research.diagnostico_grilla import episodios
    C = pd.read_csv(DIR / "OPS_CIERRE.csv.gz"); C = C[C.bloque == "DESC"]
    L = pd.read_csv(DIR / "OPS.csv.gz"); L = L[(L.bloque == "DESC") & L.definicion.isin(REGLAS)]
    L["fecha_senal"] = L.fecha                                                   # lote 1: la barra de entrada (18:00) lleva la fecha del día siguiente
    res = {}
    for r in REGLAS:
        c = C[C.definicion == r]; l = L[L.definicion == r]
        m, se, p = _media(c.fecha.to_numpy(), c.R.to_numpy())
        d, se2, p2 = A5.diferencia(c.fecha.to_numpy(), c.R.to_numpy(), l.fecha.to_numpy(), l.R.to_numpy())
        c2 = c.assign(mes=(c.fecha // 100).astype(str))
        res[r] = dict(n=int(len(c)), R=m, se=se, p=p, Rb=float(c.Rb.mean()), R_18=float(l.R.mean()), n_18=int(len(l)), episodios=episodios(c2)["linea"])
        res[f"{r}-18"] = dict(dif=d, se=se2, p=p2)
    k = list(res); rech = bh([res[x]["p"] for x in k], 0.10)
    for x, b in zip(k, rech): res[x]["bh"] = bool(b and (res[x].get("R", res[x].get("dif")) > 0))
    res = dict(preregistro=PRE, resultados=res, nominadas=[x for x in k if res[x]["bh"]])
    (DIR / "DESC_CIERRE.json").write_text(json.dumps(res, indent=1, default=float)); print(json.dumps(res, indent=1, default=float)[:5000])


if __name__ == "__main__":
    {"correr": correr, "desc": desc}[sys.argv[1]]()
