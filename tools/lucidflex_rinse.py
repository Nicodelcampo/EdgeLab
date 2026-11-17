#!/usr/bin/env python3
"""LucidFlex 25K «rinse» (reel @la.tradez, 2026-11-17, pedido de Nico: «hacé tu propia investigación y cálculos»).

Cálculo propio, sin edge por construcción (dirección al azar cada día): recorridos REALES del Nasdaq (M1 USATECH, RTH 09:30–15:59 NY,
2020-01 → 2026-09-29, nada del holdout) con brackets en dólares, fricción canónica (spread + slippage base de edgelab.costos + comisión
de Lucid) y TODAS las reglas oficiales de LucidFlex 25K (support.lucidtrading.com, leídas el 2026-11-17):
  evaluación: objetivo $1.250, pérdida máxima $1.000 al cierre (EOD, sube con el mejor cierre hasta el piso $25.100), consistencia 40 %
  (50 % con el adicional), 2 minis o 20 micros;
  fondeada: mismo drawdown EOD; el piso se bloquea en $25.100 al superar $26.100 o al pedir el primer payout; payout = 50 % del
  beneficio hasta $1.000, mínimo $500, 5 días con al menos $100 de ganancia en el ciclo y neto del ciclo > 0, 90 % para el trader,
  máximo 5 payouts (después pasa a live: no se valora).
«50 % del beneficio» se modela de las dos formas posibles: A = beneficio total de la cuenta (saldo − 25.000), B = beneficio del ciclo.
No es una búsqueda de edge (no hay selección ni hipótesis de retorno): no cuenta pruebas. Uso:
  python tools/lucidflex_rinse.py <carpeta M1>      # -> docs/research/propfirm_lucidflex_20261117/RESULTADO.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs/research/propfirm_lucidflex_20261117"
START, MLL, TRAIL, LOCK, TARGET = 25_000.0, 1_000.0, 26_100.0, 25_100.0, 1_250.0
PAY_MAX, PAY_MIN, PAY_DAY, SPLIT, N_PAY = 1_000.0, 500.0, 100.0, 0.9, 5


def friccion_usd(inst: str) -> float:
    """Ida y vuelta por contrato con la comisión de Lucid (canónica) + spread medido + slippage del escenario base."""
    from edgelab import costos as C
    d = C.tabla()["instrumentos"][inst]
    return (C.spread_ticks(inst) + C.slippage_rt_ticks("base")) * d["tick_value_usd"] + d["comision_rt_usd"]["Lucid"]


def dias_rth(carpeta):
    from edgelab.research import m1_intradia as M
    D = M.leer_m1(Path(carpeta) / "NQ_M1_dukas.csv"); D = D[(D.index >= "2020-01-01") & (D.index < "2026-09-30")]
    D = D[(D.index.hour * 60 + D.index.minute >= 570) & (D.index.hour * 60 + D.index.minute < 960) & (D.index.dayofweek < 5)]
    out = []
    for _, g in D.groupby(D.index.normalize()):
        if len(g) < 300: continue
        o = g.o.iloc[0]
        out.append((np.maximum.accumulate(g.h.values - o), np.maximum.accumulate(o - g.l.values), g.c.values[-1] - o))
    return out


def dia(rng, dias, objetivo, stop, edge_usd=0.0):
    """P&L neto de un día con bracket NETO +objetivo / −stop en USD (la fricción se suma al objetivo bruto y se descuenta del stop),
    dirección al azar, contratos MNQ para que el bracket sea ≈ 25 puntos (máx. 20 micros = el tope de 2 minis). Stop antes que objetivo
    si los dos caen en el mismo minuto; sin toque, sale al cierre de las 15:59. `edge_usd`: ventaja agregada por operación."""
    up, dn, cierre = dias[rng.integers(len(dias))]; lado = 1 if rng.random() < 0.5 else -1
    n = int(np.clip(round(max(objetivo, stop) / 50.0), 1, 20)); q = 2.0 * n; f = n * FRIC_MNQ   # MNQ: 2 USD por punto
    U, S = (objetivo + f) / q, max(stop - f, 0.25 * q) / q
    fav, con = (up, dn) if lado == 1 else (dn, up)
    i_obj = np.searchsorted(fav, U); i_stop = np.searchsorted(con, S)
    if i_stop <= i_obj and i_stop < len(fav): bruto = -S * q
    elif i_obj < len(fav): bruto = U * q
    else: bruto = lado * cierre * q
    return bruto - f + edge_usd


def cuenta(rng, dias, consistencia=0.4, lectura="A", politica="max", edge_usd=0.0, max_dias=400, dll=None):
    """Una cuenta de punta a punta. Devuelve (USD cobrados por el trader, días usados, pasó la evaluación, payouts)."""
    # --- evaluación: días iguales de objetivo/3 (40 %) o /2 (50 %), stop = colchón hasta el piso
    bal, piso, maxc, mayor, d = START, START - MLL, START, 0.0, 0
    k = 3 if consistencia == 0.4 else 2
    while d < max_dias:
        falta = START + TARGET - bal; obj = min(TARGET / k, falta) if falta > 1 else TARGET / k
        if mayor > 0 and (bal - START) > 0 and mayor / (bal - START) > consistencia: obj = TARGET / k   # sigue sumando días chicos
        pnl = dia(rng, dias, obj, min(bal - piso - 1, dll or 1e9), edge_usd); d += 1   # DLL: corte blando, el día termina
        bal += pnl; mayor = max(mayor, pnl)
        if bal <= piso: return 0.0, d, False, 0
        maxc = max(maxc, bal); piso = max(piso, min(maxc - MLL, LOCK))
        prof = bal - START
        if prof >= TARGET and mayor / prof <= consistencia: break
    else: return 0.0, d, False, 0
    # --- fondeada
    bal, piso, maxc, cobrado, pagos = START, START - MLL, START, 0.0, 0
    ciclo0, dias_ok = bal, 0
    while d < max_dias and pagos < N_PAY:
        meta = START + 2 * PAY_MAX if lectura == "A" else ciclo0 + 2 * PAY_MAX     # saldo que da el payout máximo
        if politica == "min" and lectura == "A": meta = max(START + 2 * PAY_MIN, piso + 1)
        if bal < meta: obj, stop = meta - bal, bal - piso - 1                       # tramo grande: ir al nivel o al piso
        else: obj, stop = PAY_DAY + 1, min(PAY_DAY, bal - piso - 1)                # días chicos de +$100 neto (Ari: arriesgar 100 por 100)
        pnl = dia(rng, dias, obj, max(min(stop, dll or 1e9), 1.0), edge_usd); d += 1; bal += pnl
        if pnl >= PAY_DAY: dias_ok += 1
        if bal <= piso: return cobrado, d, True, pagos
        maxc = max(maxc, bal)
        if piso < LOCK: piso = LOCK if maxc > TRAIL else max(piso, maxc - MLL)
        base = (bal - START) if lectura == "A" else (bal - ciclo0)
        monto = min(PAY_MAX, 0.5 * base)
        if dias_ok >= 5 and bal > ciclo0 and monto >= PAY_MIN and bal >= meta:
            cobrado += SPLIT * monto; bal -= monto; pagos += 1; piso = LOCK; ciclo0, dias_ok = bal, 0
    return cobrado, d, True, pagos


def main(carpeta, n=20000):
    global FRIC_MNQ
    FRIC_MNQ = friccion_usd("MNQ"); dias = dias_rth(carpeta); res = dict(fuente_reglas="support.lucidtrading.com (2026-11-17)",
                                                                       friccion_mnq_usd=FRIC_MNQ, dias=len(dias), escenarios={})
    # 4 configuraciones oficiales (LucidFlex Customization) con el precio con cupón de la página (2026-11-17): DLL ON baja el precio
    PRECIOS = {"DLL600|40%": 45.50, "DLL600|50%": 55.30, "sinDLL|40%": 60.20, "sinDLL|50%": 70.00}
    for nom, kw in {"DLL600|40%|A": dict(dll=600.0), "DLL600|50%|A": dict(dll=600.0, consistencia=0.5), "sinDLL|40%|A": dict(),
                    "sinDLL|50%|A": dict(consistencia=0.5), "DLL600|40%|B": dict(dll=600.0, lectura="B"), "sinDLL|50%|B": dict(consistencia=0.5, lectura="B"),
                    "DLL600|40%|A|min": dict(dll=600.0, politica="min"), "sinDLL|40%|A|sin_costos": dict()}.items():
        precio = PRECIOS["|".join(nom.split("|")[:2])]
        fr0 = FRIC_MNQ
        if "sin_costos" in nom: FRIC_MNQ = 0.0
        rng = np.random.default_rng(7); r = [cuenta(rng, dias, **kw) for _ in range(int(n))]; FRIC_MNQ = fr0
        cob = np.array([x[0] for x in r]); dd = np.array([x[1] for x in r]); pas = np.array([x[2] for x in r]); pg = np.array([x[3] for x in r])
        res["escenarios"][nom] = dict(pasa_eval=float(pas.mean()), llega_a_payout=float((pg > 0).mean()), payouts_medios=float(pg.mean()),
                                      cobrado_medio=float(cob.mean()), ee_cobrado=float(cob.std(ddof=1) / np.sqrt(len(cob))),
                                      cobrado_si_payout=float(cob[pg > 0].mean()) if (pg > 0).any() else 0.0, dias_medios=float(dd.mean()),
                                      dias_si_payout=float(dd[pg > 0].mean()) if (pg > 0).any() else 0.0,
                                      precio=precio, ev=float(cob.mean() - precio), ev_por_dia=float((cob.mean() - precio) / dd.mean()),
                                      p_ganar_dinero=float((cob > precio).mean()), compradas_por_fondeada=float(1 / max(pas.mean(), 1e-9)),
                                      cobrado_por_fondeada=float(cob[pas].mean()) if pas.any() else 0.0,
                                      dias_fondeada=float(dd[pas].mean()) if pas.any() else 0.0)
        print(nom, {k: round(v, 3) for k, v in res["escenarios"][nom].items()}, flush=True)
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
