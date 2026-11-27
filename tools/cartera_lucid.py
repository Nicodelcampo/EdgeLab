"""Cartera Lucid inverso-volatilidad (plan `docs/research/cartera_lucid_20261125/PLAN.md`).

  python tools/cartera_lucid.py simular     # -> docs/research/cartera_lucid_20261125/PLANES.json
  python tools/cartera_lucid.py contratos --B 200 [--hasta 2026-09-30]
        # contratos fijos por estrategia para el trimestre que empieza después de --hasta (lo que se carga en NT8)

Descriptivo de cuenta: no elige reglas ni toca el holdout terminal (las corridas NT8 cortan en 2026-09-30).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import exp7_estabilizadores as E7  # noqa: E402
from edgelab import costos  # noqa: E402

C, N = E7.CAND, E7.NUEVAS
OUT = ROOT / "docs" / "research" / "cartera_lucid_20261125"
ESTR = {"T_NQ": (C / "T" / "NT8_T_NQ_fijo1.csv", "NQ"), "R_NQ": (C / "R" / "NT8_R_NQ_fijo1.csv", "NQ"),
        "Z_NQ": (C / "Z" / "NT8_Z_NQ_fijo1.csv", "NQ"), "V_NQ": (C / "V" / "NT8_V_NQ_fijo1.csv", "NQ"),
        "RQ5_NQ": (N / "NT8_RQ5_NQ.csv", "NQ"), "RQ5_ES": (N / "NT8_RQ5_ES.csv", "ES"),
        "ES5N_ES": (N / "NT8_ES5N_ES.csv", "ES"), "Franklin_NQ": (N / "NT8_Franklin_NQ.csv", "NQ")}
# Preset Diversificada (2026-11-27, docs/research/preset_diversificada_20261127/PREREGISTRO.md): las 8 + N (arnés, sin corrida NT8
# propia todavía) + SOMEOD (corrida NT8 de Nico).
PD = ROOT / "docs" / "research" / "preset_diversificada_20261127"
ESTR10 = {**ESTR, "N_NQ": (PD / "ARNES_N_NQ.csv.gz", "NQ"), "SOMEOD_NQ": (C / "SOMEOD" / "NT8_SOMEOD_NQ_fijo1.csv", "NQ")}
UNIVERSOS = {"INTRA8": ESTR, "DIVERSIFICADA10": ESTR10}
MICRO = {"NQ": "MNQ", "ES": "MES"}
TOPE = 20


def cargar(estr: dict | None = None) -> dict:
    out = {}
    for k, (p, inst) in (estr or ESTR).items():
        o = E7.ops_nt8(p, inst)                                  # R neto con la fricción del mini (para los pesos)
        mic = MICRO[inst]; pv = costos.tick_value_usd(mic) / costos.tick_size(mic)
        o = o.assign(pv=pv, usd1=(o.pnl_pts - costos.friccion_rt_puntos(mic, "base")) * pv, stop_usd=o.riesgo_pts * pv,
                     dt=pd.to_datetime(o.ses.astype(str)))
        out[k] = o[o.ses <= 20260930]
    return out


def contratos(ops: dict, inicio: pd.Timestamp, B: float, esquema: str, tope: int = TOPE) -> dict:
    """Contratos fijos de cada estrategia para el trimestre que empieza en `inicio`, sólo con datos anteriores."""
    w, stop = {}, {}
    for k, o in ops.items():
        h = o[(o.dt < inicio) & (o.dt >= inicio - pd.DateOffset(months=12))]
        m = h.groupby(h.dt.dt.to_period("M")).R.sum().reindex(pd.period_range(inicio - pd.DateOffset(months=12), inicio - pd.DateOffset(days=1), freq="M"), fill_value=0.0)
        if o.dt.min() > inicio - pd.DateOffset(months=12):       # corrida más corta que la ventana: sin historia suficiente
            m = m[m.index >= o.dt.min().to_period("M")]
        w[k] = 1.0 / m.std(ddof=1) if len(m) >= 6 and m.std(ddof=1) > 0 else np.nan
        s3 = o[(o.dt < inicio) & (o.dt >= inicio - pd.DateOffset(months=3))].stop_usd
        stop[k] = float(s3.median()) if len(s3) else float(o[o.dt < inicio].stop_usd.tail(20).median()) if (o.dt < inicio).any() else np.nan
    if esquema.startswith("UNO"):
        k_ = int(esquema[4:]) if esquema.startswith("UNOx") else 1
        return {k: k_ for k in ops}
    wv = pd.Series(w)
    wv = (wv / wv.mean()).clip(0.25, 2.0).fillna(1.0) if esquema == "INV_VOL" else pd.Series(1.0, index=wv.index)
    n = {k: max(1, int(round(wv[k] * B / stop[k]))) if np.isfinite(stop[k]) else 1 for k in ops}
    tot = sum(n.values())
    if tot > tope:
        f = tope / tot; n = {k: max(1, int(np.floor(v * f))) for k, v in n.items()}
    return n


def serie(ops: dict, B: float, esquema: str, desde="2020-01-01", hasta="2026-09-29", tope: int = TOPE):
    trims = pd.date_range(desde, hasta, freq="QS")
    tabla = {t: contratos(ops, t, B, esquema, tope) for t in trims}
    ses = pd.bdate_range(desde, hasta)
    d = pd.Series(0.0, index=ses)
    for k, o in ops.items():
        o = o[(o.dt >= desde) & (o.dt <= hasta)]
        q = o.dt.dt.to_period("Q").dt.start_time
        nn = q.map(lambda t: tabla[t][k])
        d = d.add((nn * o.usd1).groupby(o.dt).sum(), fill_value=0.0)
    return d.reindex(ses).fillna(0.0), tabla


def simultaneos(ops: dict, tabla: dict) -> int:
    ev = []
    for k, o in ops.items():
        o = o[o.dt >= "2020-01-01"]
        q = o.dt.dt.to_period("Q").dt.start_time
        nn = q.map(lambda t: tabla.get(t, {}).get(k, 0)).to_numpy()
        ev += list(zip(pd.to_datetime(o.en_ny), nn)) + list(zip(pd.to_datetime(o.ex_ny), -nn))
    ev.sort(key=lambda x: (x[0], x[1])); c = m = 0
    for _, s in ev: c += s; m = max(m, c)
    return int(m)


CUENTAS = {  # precio, objetivo, pérdida máx EOD, piso fijo al superar, DLL, retiro máx, día mín, tope micros (PLAN.md, enmienda 1)
    "25K": (45.5, 1250.0, 1000.0, 1100.0, 600.0, 1000.0, 100.0, 20),
    "50K": (95.2, 3000.0, 2000.0, 2100.0, 1200.0, 2000.0, 150.0, 40),
    "150K": (214.25, 9000.0, 4500.0, 4600.0, 2700.0, 3000.0, 250.0, 100)}


def _sim_cuenta(x, mu, N, seed, cuenta, cons=0.4, max_dias=250, xmin=None):
    """xmin (2026-11-27, ADENDA_DLL_INTRADIA): mínimo intradía del día; si toca −DLL el día cierra en −DLL (liquidación de Lucid).
    Sin xmin, el DLL se aplica al cierre (comportamiento anterior)."""
    from numba import njit

    @njit(cache=False)
    def run(y, ym, N, seed, obj, mll, lock, dll, cap, dmin, cons, max_dias):
        np.random.seed(seed); L = len(y)
        cob = np.zeros(N); pasa = np.zeros(N); pagos = np.zeros(N); dias = np.zeros(N)
        for k in range(N):
            pos = np.random.randint(L); paso = 0
            bal = 0.0; piso = -mll; maxc = 0.0; mayor = 0.0; d = 0; ok = False
            while d < max_dias:
                if paso % 5 == 0: pos = np.random.randint(L)
                j = (pos + paso % 5) % L; p = y[j]; paso += 1
                if dll > 0 and (p < -dll or ym[j] <= -dll): p = -dll
                bal += p; d += 1; mayor = max(mayor, p)
                if bal <= piso: break
                maxc = max(maxc, bal); piso = min(max(piso, maxc - mll), 100.0)
                if bal >= obj and mayor / bal <= cons: ok = True; break
            dias[k] = d
            if not ok: continue
            pasa[k] = 1.0; bal = 0.0; piso = -mll; maxc = 0.0; c0 = 0.0; dok = 0; f = 0; npg = 0; tot = 0.0
            while f < max_dias and npg < 5:
                if paso % 5 == 0: pos = np.random.randint(L)
                j = (pos + paso % 5) % L; p = y[j]; paso += 1
                if dll > 0 and (p < -dll or ym[j] <= -dll): p = -dll
                bal += p; f += 1
                if p >= dmin: dok += 1
                if bal <= piso: break
                maxc = max(maxc, bal)
                if piso < 100.0: piso = 100.0 if maxc > lock else max(piso, maxc - mll)
                monto = min(cap, 0.5 * bal)
                if dok >= 5 and bal > c0 and monto >= 500.0:
                    tot += 0.9 * monto; bal -= monto; npg += 1; piso = 100.0; c0 = bal; dok = 0
            cob[k] = tot; pagos[k] = npg; dias[k] += f
        return cob, pasa, pagos, dias

    precio, obj, mll, lock, dll, cap, dmin, _ = CUENTAS[cuenta]
    y = np.asarray(x, np.float64); sh = mu - y.mean(); y = y + sh
    ym = (np.asarray(xmin, np.float64) + sh) if xmin is not None else np.zeros_like(y)   # sin xmin nunca toca (0 > −DLL)
    cob, pas, pg, dias = run(y, ym, N, seed, obj, mll, lock, dll, cap, dmin, cons, max_dias)
    return dict(pasa=float(pas.mean()), cobra=float((pg > 0).mean()), retiros=float(pg.mean()), cobrado=float(cob.mean()),
                ev=float(cob.mean() - precio), p_ganar=float((cob > precio).mean()), dias=float(dias.mean()),
                ev_por_mes=float((cob.mean() - precio) / max(dias.mean(), 1) * 21))


def simular(universo: str = "INTRA8", salida: Path | None = None, intradia: bool = False, precio: str = "extremo",
            cuentas: tuple = ()) -> int:
    if universo != "INTRA8":
        from registro_global import exigir_contada
        exigir_contada(PD / "PREREGISTRO.md")
    if intradia:
        import intradia_min_cartera as IM
        from registro_global import exigir_contada
        exigir_contada(PD / "ADENDA_DLL_INTRADIA.md")
        cam = IM.caminos(UNIVERSOS[universo], precio=precio)
    ops = cargar(UNIVERSOS[universo]); res = {"plan": "docs/research/cartera_lucid_20261125/PLAN.md (enmienda 1)", "universo": universo, "cuentas": {}}
    for cta, spec in CUENTAS.items():
        if cuentas and cta not in cuentas:
            continue
        tope = spec[7]; R = res["cuentas"][cta] = {"planes": {}}
        planes = [(f"UNOx{k}", 0) for k in (1, 2, 3, 4)] + [(e, B) for e in ("RIESGO_IGUAL", "INV_VOL") for B in (100, 200, 300, 400, 600, 800)]
        for e, B in planes:
            x, tabla = serie(ops, B, e, tope=tope)
            xm = IM.minimo_plan(cam, tabla, x.index).to_numpy() if intradia else None
            c = x.cumsum(); dd = float((c - c.cummax()).min()); xr = x[x.index >= "2024-01-01"]
            xmr = xm[(x.index >= "2024-01-01")] if intradia else None
            out = dict(usd_dia=round(float(x.mean()), 1), sd_dia=round(float(x.std()), 1), peor_dia=round(float(x.min()), 0), maxDD_usd=round(dd, 0),
                       max_micros_simultaneos=simultaneos(ops, tabla), contratos_ultimo_trimestre=tabla[max(tabla)],
                       usd_mes_por_anio={str(a): round(float(v), 0) for a, v in (x.groupby(x.index.year).mean() * 21).items()})
            for mu_nom, f in (("dev", 1.0), ("contraida", 0.5), ("cero", 0.0)):
                out[mu_nom] = _sim_cuenta(x.to_numpy(), float(x.mean() * f), 10000, 7, cta, xmin=xm)
            out["contraida_desde_2024"] = _sim_cuenta(xr.to_numpy(), float(xr.mean() * 0.5), 10000, 7, cta, xmin=xmr)
            if intradia:
                out["peor_minimo_intradia"] = round(float(xm.min()), 0); out["dias_que_tocan_dll"] = int((xm <= -CUENTAS[cta][4]).sum())
            nom = f"{e}|B{B}"; R["planes"][nom] = out; v = out["contraida"]; v2 = out["contraida_desde_2024"]
            print(f"{cta:5s} {nom:18s} $/d {x.mean():6.1f} sd {x.std():5.0f} peor {x.min():6.0f} DD {dd:7.0f} sim {out['max_micros_simultaneos']:3d} | "
                  f"p_ganar {v['p_ganar']:.3f} ev {v['ev']:6.0f} ret {v['retiros']:.2f} pasa {v['pasa']:.3f} dias {v['dias']:.0f} | 2024+ p {v2['p_ganar']:.3f} ev {v2['ev']:6.0f} | cero p {out['cero']['p_ganar']:.3f}", flush=True)
        pg = {k: p["contraida"]["p_ganar"] for k, p in R["planes"].items() if p["max_micros_simultaneos"] <= tope}   # auditoría: tope de Lucid
        m = max(pg.values()); cand = [k for k in pg if pg[k] >= m - 0.02]
        R["elegido"] = max(cand, key=lambda k: R["planes"][k]["contraida"]["ev"])
        print(cta, "elegido:", R["elegido"], R["planes"][R["elegido"]]["contratos_ultimo_trimestre"], flush=True)
    res["criterio"] = "por cuenta: max p_ganar con media contraída 0,5 (consistencia 40 %, DLL, retiro máximo); empate a 0,02 -> mayor ev"
    salida = salida or OUT / "PLANES.json"; salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("accion", choices=["simular", "contratos"])
    ap.add_argument("--universo", default="INTRA8", choices=sorted(UNIVERSOS)); ap.add_argument("--salida", type=Path, default=None)
    ap.add_argument("--intradia", action="store_true")                  # DLL sobre el mínimo intradía (ADENDA_DLL_INTRADIA)
    ap.add_argument("--precio", default="extremo", choices=["extremo", "cierre"]); ap.add_argument("--cuentas", default="")
    ap.add_argument("--tope", type=int, default=TOPE)                   # tope de micros de la cuenta (25K 20, 50K 40, 150K 100)
    ap.add_argument("--B", type=float, default=200.0); ap.add_argument("--esquema", default="INV_VOL"); ap.add_argument("--hasta", default="2026-09-30")
    a = ap.parse_args(argv)
    if a.accion == "simular":
        return simular(a.universo, a.salida, a.intradia, a.precio, tuple(x for x in a.cuentas.split(",") if x))
    inicio = (pd.Timestamp(a.hasta) + pd.offsets.QuarterBegin(startingMonth=1)).normalize()
    print(inicio.date(), contratos(cargar(UNIVERSOS[a.universo]), inicio, a.B, a.esquema, a.tope))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
