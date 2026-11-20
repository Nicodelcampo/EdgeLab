#!/usr/bin/env python3
"""Turtles 55/20 en oro con cierre del viernes: réplica en 2004–2010 (no mirado) y mejora con el método de
docs/research/mejora_estrategias_20261116/CRITERIOS_Y_PLAN.md (elegir en años pares, confirmar en impares). Pre-registro:
docs/research/turtles_oro_20261117/PREREGISTRO.md.

  python tools/mejora_turtles_oro.py <carpeta M1>     # -> docs/research/turtles_oro_20261117/RESULTADO.json y ops/
Reusa edgelab.research.sqx_catalogo (motor y reglas), reels_20261116.tramo (bootstrap por sesión) y fundedsync_tanda2._bh.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "docs/research/turtles_oro_20261117"
REPLICA = ("2004-01-01", "2010-12-31"); DEV = ("2011-01-01", "2026-09-29"); NB = 20000
VARIANTES = {          # nombre: (categoría, perillas) — una perilla por vez sobre la base
    "base": ("base", {}),
    "reentrada_lunes": ("frecuencia", dict(reentrada=True)),
    "canal_20": ("frecuencia", dict(n_in=20)),
    "h4": ("frecuencia", dict(tf="H4")),
    "metales": ("frecuencia", dict(insts=("GC", "SI"))),
    "sin_filtro_vol": ("filtro", dict(vol=False)),
    "sin_filtro_tend": ("filtro", dict(tend=False)),
    "solo_largos": ("filtro", dict(cortos=False)),
    "entrada_stop": ("entrada", dict(entrada="stop")),
}


def datos(carpeta):
    from edgelab.research import m1_intradia as M, sqx_catalogo as S
    D = M.leer_m1(Path(carpeta) / "XAUUSD_M1_dukas.csv"); D = D[D.index < "2026-09-30"]
    out = {}
    for tf in ("D1", "H4"):
        B = S.barras_desde_m1(D, tf); B = B[B.fecha < 20260930]; out[("GC", tf)] = (B, S.indices_m1(B, D, tf))
    Bs = S.barras_d1_csv(ROOT / "data/sqx_barras/XAGUSD_D1.csv"); out[("SI", "D1")] = (Bs[Bs.fecha < 20260930], None)
    return out


def medir(perillas, DAT):
    from edgelab.research import sqx_catalogo as S
    from edgelab.research.embudo_runners import friccion
    p = dict(perillas); tf = p.pop("tf", "D1"); insts = p.pop("insts", ("GC",)); reent = p.pop("reentrada", False); partes = []
    for inst in insts:
        B, m1 = DAT[(inst, tf)]; sig = S.turtle_v(**p)(B, {})
        if reent: sig = S.con_reentrada(B, sig, m1)
        T = S.simular(B, sig, viernes=True, m1=m1); fr = friccion(inst)[0]
        g = T.assign(inst=inst, riesgo=(T.entrada - T.stop0).abs(), bruto=T.lado * (T.salida_px - T.entrada)); g = g[g.riesgo > 0].copy()
        g["neto"] = g.bruto - fr; g["R"] = g.neto / g.riesgo; g["Rb"] = g.bruto / g.riesgo; g["fricR"] = fr / g.riesgo
        g["dia"] = pd.to_datetime(g.fecha.astype(str)); partes.append(g)
    return pd.concat(partes, ignore_index=True).sort_values("dia").reset_index(drop=True)


def mensual(g, x0, x1, anios=None):
    meses = pd.period_range(x0[:7], x1[:7], freq="M")
    if anios is not None: meses = meses[np.isin(meses.year, list(anios))]
    m = g.groupby(g.dia.dt.to_period("M")).R.sum(); return m.reindex(meses, fill_value=0.0)


def t_de(x):
    x = np.asarray(x, float); s = x.std(ddof=1); return float(x.mean() / s * np.sqrt(len(x))) if len(x) > 2 and s > 0 else 0.0


def p_boot(x, seed=11):
    x = np.asarray(x, float); i = np.random.default_rng(seed).integers(0, len(x), (NB, len(x))); m = x[i].mean(1)
    return float((1 + (m <= 0).sum()) / (NB + 1))


def resumen(g, x0, x1, anios=None):
    gg = g[(g.dia >= x0) & (g.dia <= x1)]
    if anios is not None: gg = gg[gg.dia.dt.year.isin(list(anios))]
    m = mensual(g, x0, x1, anios); yr = gg.groupby(gg.dia.dt.year).R.sum(); eq = gg.R.cumsum()
    return dict(n=int(len(gg)), ops_anio=float(len(gg) / max(len(m) / 12, 1e-9)), R_op=float(gg.R.mean()) if len(gg) else None,
                R_bruto_op=float(gg.Rb.mean()) if len(gg) else None, R_mes=float(m.mean()), t_mes=t_de(m), fric_med=float(gg.fricR.median()) if len(gg) else None,
                anios_pos=int((yr > 0).sum()), anios=int(len(yr)), dd_R=float((eq - eq.cummax()).min()) if len(gg) else 0.0,
                largos=int((gg.lado == 1).sum()), salidas=gg.motivo.value_counts().to_dict())


def main(carpeta):
    from reels_20261116 import tramo
    from fundedsync_tanda2 import _bh
    (OUT / "ops").mkdir(parents=True, exist_ok=True); DAT = datos(carpeta); res = dict(preregistro="docs/research/turtles_oro_20261117/PREREGISTRO.md")
    pares = range(2012, 2027, 2); impares = range(2011, 2026, 2); G = {}
    for nom, (cat, per) in VARIANTES.items():
        G[nom] = g = medir(per, DAT); g.to_csv(OUT / "ops" / f"{nom}.csv.gz", index=False)
        res[nom] = dict(categoria=cat, perillas=per, pares=resumen(g, *DEV, pares), impares=resumen(g, *DEV, impares), dev=resumen(g, *DEV),
                        replica=dict(resumen(g, *REPLICA), **{k: v for k, v in tramo(g, *REPLICA).items() if k in ("p", "ic90", "mde")}))
        r = res[nom]; print(nom, {k: (r[k]["n"], r[k]["R_op"] and round(r[k]["R_op"], 3), round(r[k]["t_mes"], 2), r[k]["anios_pos"], r[k]["anios"])
                                  for k in ("replica", "pares", "impares")}, "fric", r["dev"]["fric_med"] and round(r["dev"]["fric_med"], 3), flush=True)
    # 1) réplica de la base en 2004–2010 (pre-registrada: R > 0 y p < 0,10, bootstrap por sesión)
    rb = res["base"]["replica"]; res["replica_base"] = dict(R=rb["R_op"], p=rb.get("p"), n=rb["n"], mde=rb.get("mde"),
                                                         replica=bool((rb["R_op"] or -1) > 0 and (rb.get("p") or 1) < 0.10))
    # 2) elección en años pares
    b = res["base"]["pares"]
    eleg = [k for k in VARIANTES if k != "base" and (res[k]["dev"]["fric_med"] or 9) <= 0.08 and res[k]["pares"]["anios_pos"] >= b["anios_pos"]]
    orden = sorted(eleg, key=lambda k: -res[k]["pares"]["t_mes"]); fin = orden[:3]
    cats = [k for k in orden if res[k]["pares"]["t_mes"] > b["t_mes"]]
    dos = [];
    for k in cats:
        if all(VARIANTES[k][0] != VARIANTES[j][0] for j in dos): dos.append(k)
        if len(dos) == 2: break
    if len(dos) == 2:
        comb = "+".join(dos); per = {**VARIANTES[dos[0]][1], **VARIANTES[dos[1]][1]}; G[comb] = g = medir(per, DAT); g.to_csv(OUT / "ops" / f"{comb}.csv.gz", index=False)
        res[comb] = dict(categoria="combinacion", perillas=per, pares=resumen(g, *DEV, pares), impares=resumen(g, *DEV, impares), dev=resumen(g, *DEV),
                         replica=dict(resumen(g, *REPLICA), **{k: v for k, v in tramo(g, *REPLICA).items() if k in ("p", "ic90", "mde")}))
        if (res[comb]["dev"]["fric_med"] or 9) <= 0.08: fin.append(comb)
    res["elegibles"] = eleg; res["finalistas"] = fin
    # 3) confirmación en años impares: diferencia mensual variante − base > 0 (bootstrap por mes), BH q 0,10 sobre las finalistas, R > 0
    mb = mensual(G["base"], *DEV, impares); ps = []
    for k in fin:
        d = mensual(G[k], *DEV, impares) - mb; res[k]["confirmacion"] = dict(dif_mes=float(d.mean()), p=p_boot(d.values)); ps.append(res[k]["confirmacion"]["p"])
    for k, nom_bh in zip(fin, _bh(ps) if ps else []):
        c = res[k]["confirmacion"]; c["bh"] = bool(nom_bh)
        c["confirma"] = bool(nom_bh and c["dif_mes"] > 0 and (res[k]["impares"]["R_op"] or -1) > 0)
        c["replica_2004_2010_R_pos"] = bool((res[k]["replica"]["R_op"] or -1) > 0)
    gan = [k for k in fin if res[k]["confirmacion"]["confirma"] and res[k]["confirmacion"]["replica_2004_2010_R_pos"]]
    res["ganadora"] = max(gan, key=lambda k: res[k]["impares"]["t_mes"]) if gan else None
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, default=float))
    print("réplica base", res["replica_base"]); print("finalistas", fin); print("ganadora", res["ganadora"])


if __name__ == "__main__":
    from edgelab.costos import estimados_permitidos
    with estimados_permitidos("docs/research/turtles_oro_20261117/PREREGISTRO.md (SI con spread estimado)"): main(*sys.argv[1:])
