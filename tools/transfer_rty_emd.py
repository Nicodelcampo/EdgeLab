#!/usr/bin/env python3
"""TRANSFER-RTY-EMD (pre-registro docs/research/transfer_rty_emd_20261119/PREREGISTRO.md): Z (FundedSync, stop 0,25 × ATR20) y VZ (compresión de
VIX+VIX9D, regla de CARRIL2-LOTE2) en RTY y EMD, sólo meses DESC de A5. Sin motor propio: neto_pistas (_ms, _ops, _cfg, FABRICA) para Z;
carril2._senales2 + sqx_catalogo.simular (K28) para VZ, con RVX como IV en RTY.

  python tools/transfer_rty_emd.py z     # → Z_OPS.csv.gz, Z.json
  python tools/transfer_rty_emd.py vz    # → VZ_OPS.csv.gz, VZ.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/transfer_rty_emd_20261119"; PRE = "docs/research/transfer_rty_emd_20261119/PREREGISTRO.md"; INST = ("RTY", "EMD")


def _fr(inst):
    from edgelab import costos
    from edgelab.research.embudo_runners import friccion
    with costos.estimados_permitidos(PRE): return float(friccion(inst)[0])


def _prueba(ses, r):
    from carril2 import _media
    m, se, p = _media(np.asarray(ses), np.asarray(r, float)); return dict(n=int(len(r)), R=m, se=se, p=p, mde80=2.49 * se)


def z():
    from registro_global import exigir_contada
    from edgelab.holdout import a5_bloque
    import neto_pistas as NP
    exigir_contada(PRE); partes = []
    for inst in INST:
        F, D, ms = NP._ms(inst); o = NP._ops(F, "Z", ms, D, NP._cfg("Z", NP.FABRICA["Z"])); fr = _fr(inst); s = 0.25 * o.atr20
        o = o[np.isfinite(s) & (s > 0)].copy(); s = 0.25 * o.atr20
        o["R"] = (np.where(o.mae_pts >= s, -s, o.pnl_pts) - fr) / s; o["Rb"] = np.where(o.mae_pts >= s, -s, o.pnl_pts) / s
        o["fecha"] = pd.to_datetime(o.ses).dt.strftime("%Y%m%d").astype(int); o["bloque"] = [a5_bloque(int(x)) for x in o.fecha]; o["inst"] = inst
        partes.append(o); print(inst, len(o), flush=True)
    T = pd.concat(partes, ignore_index=True); T = T[(T.bloque == "DESC") & (T.fecha <= 20250731)]
    T.to_csv(DIR / "Z_OPS.csv.gz", index=False)
    v = T[T.fecha >= 20180101]; res = dict(prueba=_prueba(v.fecha, v.R), por_inst={i: _prueba(g.fecha, g.R) for i, g in v.groupby("inst")},
                                          bruto=float(v.Rb.mean()), antes_2018=_prueba(T[T.fecha < 20180101].fecha, T[T.fecha < 20180101].R))
    res["veredicto"] = "TRANSFIERE_DESC" if res["prueba"]["R"] > 0 and res["prueba"]["p"] < 0.05 else "SIN_TRANSFERENCIA"
    (DIR / "Z.json").write_text(json.dumps(res, indent=1, default=float)); print(json.dumps(res, indent=1, default=float))


def vz():
    from registro_global import exigir_contada
    from datos import ruta
    from m1_largo import cargar
    from edgelab.research import sqx_catalogo as Q
    from edgelab.holdout import a5_bloque
    import carril2 as C
    exigir_contada(PRE); C._lote2()
    V = pd.read_parquet(Path(ruta("M1NT8")) / "cboe_volatility_daily.parquet"); partes = []
    for inst in INST:
        Vi = V.assign(vix_close=V.rvx_close) if inst == "RTY" else V                  # IV = RVX en RTY, VIX en EMD (VIX9D igual en los dos)
        D = cargar(inst, ruta("M1NT8")); B = Q.barras_desde_m1(D, "D1"); m1 = Q.indices_m1(B, D, "D1"); f = B.fecha.to_numpy()
        mens = pd.Series(dtype=float); mens.attrs["sma"] = pd.Series(dtype=float)          # la rotación no se usa acá
        S = C._senales2(B, "X", Vi, mens)
        fr = _fr(inst)
        for d in ("C2_VZ", "C2_VZN"):
            O = Q.simular(B, S[d], viernes=False, m1=m1); rg = (O.entrada - O.stop0).abs()
            O["R"] = (O.lado * (O.salida_px - O.entrada) - fr) / rg; O["Rb"] = O.lado * (O.salida_px - O.entrada) / rg
            O["fecha_salida"] = f[np.minimum(O.i0 + O.barras - 1, len(f) - 1)]; O["definicion"], O["inst"] = d, inst
            partes.append(O[O.stop0.notna() & (rg > 0)])
        print(inst, flush=True)
    T = pd.concat(partes, ignore_index=True)
    T["bloque"] = [a5_bloque(int(x)) for x in T.fecha]; T["bloque_salida"] = [a5_bloque(int(x)) for x in T.fecha_salida]
    T = T[(T.bloque == "DESC") & (T.bloque_salida == "DESC") & (T.fecha_salida <= 20250731)]
    assert (T.bloque_salida == "DESC").all()
    T.to_csv(DIR / "VZ_OPS.csv.gz", index=False); g = T[T.definicion == "C2_VZ"]
    res = dict(prueba=_prueba(g.fecha, g.R), por_inst={i: _prueba(x.fecha, x.R) for i, x in g.groupby("inst")}, bruto=float(g.Rb.mean()),
               desde_2018=_prueba(g[g.fecha >= 20180101].fecha, g[g.fecha >= 20180101].R),
               control_VZN=_prueba(T[T.definicion == "C2_VZN"].fecha, T[T.definicion == "C2_VZN"].R))
    res["veredicto"] = "TRANSFIERE_DESC" if res["prueba"]["R"] > 0 and res["prueba"]["p"] < 0.05 else "SIN_TRANSFERENCIA"
    (DIR / "VZ.json").write_text(json.dumps(res, indent=1, default=float)); print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    {"z": z, "vz": vz}[sys.argv[1]]()
