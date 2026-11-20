#!/usr/bin/env python3
"""Mejora de T de FundedSync (docs/research/mejora_estrategias_20261116/CRITERIOS_Y_PLAN.md §10): 6 variantes de una perilla, elección en
años pares por t de los puntos netos por mes, confirmación en impares contra la base.

  python tools/mejora_t.py <carpeta M1>   # -> docs/research/mejora_estrategias_20261116/T_MEJORAS.json
Reusa fundedsyncstack.correr_modulo (con cfg_overrides), fundedsync_tanda2 (lector, _ops, _bh), fundedsync_mecanismos.contexto (noche) y
mejora_som (metricas, _mensual, _p_dif).
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from mejora_som import metricas, _mensual, _p_dif, OUT  # noqa: E402
FR = 1.5455
VARIANTES = {
    "base": ("base", {}, None),
    "sin_objetivo": ("salida", dict(high_orb_target_r=100.0, countertrend_target_r=100.0, baseline_target_r=100.0), None),
    "sin_1530": ("salida", dict(conditional_exit_minute_et=9999), None),
    "salida_libre": ("salida", dict(high_orb_target_r=100.0, countertrend_target_r=100.0, baseline_target_r=100.0, conditional_exit_minute_et=9999), None),
    "stop_x1.0": ("stop", dict(stop_orb_multiplier=1.0), None),
    "stop_x1.5": ("stop", dict(stop_orb_multiplier=1.5), None),
    "noche_no_baja": ("contexto", {}, "noche"),
}


def main(carpeta):
    from edgelab.research import fundedsyncstack as F
    import fundedsync_tanda2 as T2, fundedsync_mecanismos as FM
    from fundedsync_tanda2 import _bh
    D = T2.leer(carpeta, "NQ_M1_dukas"); ms = F.build_multi_series(F.load_m1_data(T2.a_utc(D), end="2026-10-01"), tz_input="UTC")
    noche = FM.contexto(Path(carpeta) / "NQ_M1_dukas.csv").noche
    def correr(cfg, filtro):
        x = F.correr_modulo("T", ms, **cfg); o = T2._ops(x, FR)
        rg = (pd.to_numeric(x.entry_price, errors="coerce") - pd.to_numeric(x.stop_price, errors="coerce")).abs().to_numpy(float)
        g = pd.DataFrame(dict(fecha=o.dia.dt.strftime("%Y%m%d").astype(int).values, mes=o.dia.dt.to_period("M").astype(str).values, anio=o.dia.dt.year.values,
                              R=o.neto.values, fricR=np.where(rg > 0, FR / np.maximum(rg, 1e-9), np.nan), salida=o.salida.values))
        if filtro == "noche": g = g[noche.reindex(o.dia).isin(["medio", "alto"]).values]
        return g
    G = {}
    for n, (_, cfg, fl) in VARIANTES.items():
        G[n] = correr(cfg, fl); print(n, len(G[n]), flush=True)
    todos = sorted(set().union(*[set(g.mes) for g in G.values()])); todos = [m for m in todos if m >= "2012-02"]
    par = [m for m in todos if int(m[:4]) % 2 == 0]; impar = [m for m in todos if int(m[:4]) % 2 == 1]; rec = [m for m in todos if "2025-08" <= m <= "2026-09"]
    res = dict(plan="docs/research/mejora_estrategias_20261116/CRITERIOS_Y_PLAN.md §10", unidad="puntos NQ netos (1 contrato)", variantes={})
    for n, g in G.items():
        res["variantes"][n] = dict(categoria=VARIANTES[n][0], E=metricas(g[g.anio % 2 == 0], par), C=metricas(g[g.anio % 2 == 1], impar),
                                   reciente=metricas(g[g.mes.isin(rec)], rec), total=metricas(g, todos), salidas=g.salida.value_counts().to_dict())
    b = res["variantes"]["base"]["E"]
    eleg = [n for n, v in res["variantes"].items() if n != "base" and v["E"]["anios_pos"] >= b["anios_pos"]]
    top = sorted(eleg, key=lambda n: -res["variantes"][n]["E"]["t_mes"])[:3]; nombres = list(top)
    if len(top) >= 2 and VARIANTES[top[0]][0] != VARIANTES[top[1]][0]:
        c = {}; [c.update(VARIANTES[t][1]) for t in top[:2]]; fl = VARIANTES[top[0]][2] or VARIANTES[top[1]][2]
        n = f"{top[0]}+{top[1]}"; G[n] = correr(c, fl); nombres.append(n)
        res["variantes"][n] = dict(categoria="combinacion", E=metricas(G[n][G[n].anio % 2 == 0], par), C=metricas(G[n][G[n].anio % 2 == 1], impar),
                                   reciente=metricas(G[n][G[n].mes.isin(rec)], rec), total=metricas(G[n], todos))
    base_C = _mensual(G["base"][G["base"].anio % 2 == 1], impar); conf = {}
    for n in nombres:
        d, p = _p_dif(_mensual(G[n][G[n].anio % 2 == 1], impar), base_C); conf[n] = dict(dif_mes=d, p=p, R_mes_C=res["variantes"][n]["C"]["R_mes"])
    for n, bb in zip(nombres, _bh([conf[n]["p"] for n in nombres]) if nombres else []): conf[n].update(bh=bool(bb), confirma=bool(bb and conf[n]["dif_mes"] > 0 and conf[n]["R_mes_C"] > 0))
    gan = max((n for n in nombres if conf[n]["confirma"]), key=lambda n: res["variantes"][n]["E"]["t_mes"], default=None)
    res.update(elegibles=eleg, finalistas=nombres, confirmacion=conf, ganadora=gan)
    (OUT / "T_MEJORAS.json").write_text(json.dumps(res, indent=1, default=float))
    for n, v in res["variantes"].items():
        E, C, R = v["E"], v["C"], v["reciente"]
        print(f"{n:28s} E t {E['t_mes']:5.2f} pts/mes {E['R_mes']:7.1f} a+ {E['anios_pos']}/{E['anios']} | C t {C['t_mes']:5.2f} pts/mes {C['R_mes']:7.1f} a+ {C['anios_pos']}/{C['anios']} | rec {R['R_mes']:7.1f} ops/m {v['total']['ops_mes']:.1f} dd {v['total']['dd_R']:.0f}")
    print(json.dumps(conf, indent=1)); print("ganadora", gan)


if __name__ == "__main__":
    main(sys.argv[1])
