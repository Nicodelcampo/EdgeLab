#!/usr/bin/env python3
"""Análisis CONGELADO de la apertura exploratoria del holdout de HFT_RUPTURA
(docs/research/hft_clusters_u1_20261110/PREREGISTRO_HOLDOUT_HFT_RUPTURA.md). Una sola vez, sobre las tablas del kernel `op2_holdout`.
  python tools/op2_holdout.py curva     # curva de capital de la regla de YM: IS (DESC) y OOS (réplica); el holdout se agrega si ya está
  python tools/op2_holdout.py analizar  # H-YM y H1 en el holdout, Fisher con las p de desarrollo declaradas, BH q 0,10 sobre las dos
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab.research import banco_eventos as BE  # noqa: E402

D = ROOT / "docs/research/hft_clusters_u1_20261110"
FIN_DESC, FIN_REP = 20260331, 20260930
P_DESARROLLO = {"H_YM": (0.286, 0.381), "H1": (0.088, 0.052)}      # declaradas en el pre-registro ANTES de lanzar
H1_INST = ("NQ", "YM")                                               # H1 de CONFIRMACION_NO_DEFIENDE (NQ+RTY+YM) sin RTY: no está sellado
GEOM = "g1"                                                          # regla congelada: stop X, objetivo X, 900 s


def neto_ym(T: pd.DataFrame) -> pd.DataFrame:
    R = T[(T.inst == "YM") & (T.placebo == 0)].reset_index(drop=True)      # orden del kernel: cronológico dentro de cada sesión
    R = R.assign(neto=R[f"op_{GEOM}"] - R.op_costo_r, orden=np.arange(len(R))).sort_values(["fecha", "orden"], kind="stable")
    return R.assign(periodo=np.select([R.fecha <= FIN_DESC, R.fecha <= FIN_REP], ["IS", "OOS"], "HOLDOUT"))


def fisher(ps) -> float:
    from scipy.stats import chi2
    ps = [min(max(float(p), 1e-12), 1.0) for p in ps]
    return float(chi2.sf(-2 * np.sum(np.log(ps)), 2 * len(ps)))


def analizar(T_op: pd.DataFrame, T_rup: pd.DataFrame) -> dict:
    R = neto_ym(T_op); out = dict(regla="YM, D0 del cluster K4_A025, a mercado a favor de la llegada, stop X, objetivo X, 900 s, R neto")
    e = BE.estabilidad(R.neto.to_numpy(float), R.fecha.to_numpy(), BE._sesiones(R)) if len(R) >= 10 else {}
    out["H_YM"] = dict(n=int(len(R)), sesiones=int(R.fecha.nunique()), r_neto=float(R.neto.mean()) if len(R) else None,
                       r_bruto=float(R[f"op_{GEOM}"].mean()) if len(R) else None, bloques_pos=e.get("bloques_pos"), p=e.get("p_media"))
    h1 = BE.real_menos_control(T_rup[T_rup.inst.isin(H1_INST)], "rompe") if len(T_rup) else {}
    out["H1"] = {k: v for k, v in h1.items() if k in ("media", "bloques_pos", "p_media", "sesiones", "por_activo")}
    ps = {}
    for h, p in (("H_YM", out["H_YM"].get("p")), ("H1", out["H1"].get("p_media"))):
        out[h]["p_fisher"] = ps[h] = fisher([*P_DESARROLLO[h], p]) if p is not None else None
    v = sorted((p, h) for h, p in ps.items() if p is not None); m = len(v); nom = set()
    for k in range(m, 0, -1):                                                       # BH q 0,10 sobre las dos combinadas
        if v[k - 1][0] <= 0.10 * k / m: nom = {h for _, h in v[:k]}; break
    for h in ps:
        efecto = out[h].get("r_neto") if h == "H_YM" else out[h].get("media")
        out[h]["veredicto"] = ("SIN_DATOS" if ps[h] is None else "A_FAVOR_COMBINADO" if h in nom and (efecto or 0) > 0
                               else "EN_CONTRA" if (efecto or 0) <= 0 else "NO_CONCLUYENTE")
    return out


def curva(R: pd.DataFrame, salida: Path) -> dict:
    """SVG a mano (sin matplotlib en el entorno: regla de no sumar dependencias pesadas)."""
    colores = {"IS": "#3b6ea8", "OOS": "#d08a2c", "HOLDOUT": "#2f9e6b"}; res = {}; tramos = []; x0, acum = 0, 0.0
    for per in ("IS", "OOS", "HOLDOUT"):
        S = R[R.periodo == per]
        if not len(S): continue
        c = S.neto.cumsum().to_numpy(); y = acum + c
        res[per] = dict(n=int(len(S)), sesiones=int(S.fecha.nunique()), r_neto_medio=float(S.neto.mean()), r_total=float(S.neto.sum()),
                        r_bruto_medio=float(S[f"op_{GEOM}"].mean()), desde=int(S.fecha.min()), hasta=int(S.fecha.max()),
                        max_drawdown_r=float((np.maximum.accumulate(np.r_[0, c]) - np.r_[0, c]).max()))
        tramos.append((per, np.r_[x0, np.arange(x0 + 1, x0 + len(S) + 1)], np.r_[acum, y])); x0, acum = x0 + len(S), float(y[-1])
    W, Hh, ml, mr, mt, mb = 980, 500, 70, 20, 112, 50
    ys = np.concatenate([t[2] for t in tramos]); lo, hi = min(0.0, ys.min()), max(0.0, ys.max()); pad = (hi - lo) * 0.08 or 1
    lo, hi = lo - pad, hi + pad; X = lambda v: ml + (W - ml - mr) * v / max(x0, 1); Y = lambda v: mt + (Hh - mt - mb) * (hi - v) / (hi - lo)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" viewBox="0 0 {W} {Hh}" font-family="Helvetica,Arial,sans-serif">',
         f'<rect width="{W}" height="{Hh}" fill="#fff"/>',
         f'<text x="{ml}" y="24" font-size="15" font-weight="bold" fill="#222">OP-2 en YM — continuación en el primer regreso a un cluster HFT grande</text>',
         f'<text x="{ml}" y="42" font-size="11.5" fill="#555">stop X, objetivo X, salida a 900 s; R neto acumulado con costos de edgelab/costos.py; una operación por punto</text>']
    for k in range(6):                                                               # grilla horizontal
        v = lo + (hi - lo) * k / 5
        o.append(f'<line x1="{ml}" x2="{W - mr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#eee"/><text x="{ml - 8}" y="{Y(v) + 4:.1f}" font-size="10.5" fill="#666" text-anchor="end">{v:+.1f} R</text>')
    o.append(f'<line x1="{ml}" x2="{W - mr}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="#888" stroke-width="0.8"/>')
    ly = 58
    for i, (per, xs, yv) in enumerate(tramos):
        o.append(f'<rect x="{X(xs[0]):.1f}" y="{mt}" width="{X(xs[-1]) - X(xs[0]):.1f}" height="{Hh - mt - mb}" fill="{colores[per]}" opacity="0.05"/>')
        o.append('<polyline fill="none" stroke="%s" stroke-width="1.8" points="%s"/>' % (colores[per], " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in zip(xs, yv))))
        r = res[per]; yy = 64 + 16 * i
        o.append(f'<rect x="{ml}" y="{yy - 9}" width="14" height="3" fill="{colores[per]}"/><text x="{ml + 20}" y="{yy}" font-size="11.5" font-weight="bold" fill="{colores[per]}">{per}</text>')
        o.append(f'<text x="{ml + 92}" y="{yy}" font-size="11" fill="#444">{r["desde"]}–{r["hasta"]} · n {r["n"]} · {r["r_neto_medio"]:+.3f} R/op · total {r["r_total"]:+.1f} R · DD máx {r["max_drawdown_r"]:.1f} R</text>')
    o.append(f'<text x="{(W + ml) / 2:.0f}" y="{Hh - 14}" font-size="11" fill="#666" text-anchor="middle">operación (orden cronológico, {x0} en total)</text></svg>')
    salida.write_text("\n".join(o), encoding="utf-8")
    return res


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "curva"
    T = pd.read_csv(D / "HFTC_op2.csv"); H = D / "HFTC_op2_holdout.csv"
    if modo == "analizar":
        if not H.exists(): raise SystemExit("falta HFTC_op2_holdout.csv (python tools/hft_clusters_info.py traer op2_holdout)")
        Th, Tr = pd.read_csv(H), pd.read_csv(D / "HFTC_ruptura_holdout.csv")
        out = analizar(Th, Tr)
        (D / "RESULTADO_HOLDOUT_HFT_RUPTURA.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
        print(json.dumps(out, ensure_ascii=False, default=float)); T = pd.concat([T, Th], ignore_index=True)
    res = curva(neto_ym(T), D / "OP2_YM_CURVA.svg")
    (D / "OP2_YM_CURVA.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); print(json.dumps(res, default=float))


if __name__ == "__main__":
    main()
