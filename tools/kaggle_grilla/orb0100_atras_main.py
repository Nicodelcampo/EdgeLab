# Principal del kernel ORB0100-ATRAS (docs/research/orb0100_20261021/PREREGISTRO_ORB0100_ATRAS_20261025.md): la celda congelada de la
# réplica (rango 01:00–01:15 ET, ruptura por cierre de 5 min, a favor del VWAP, TP 1,5R, SL otro lado, cierre 16:00) sobre USATECH de
# Dukascopy 2023-01-03 → 2025-08-04, que ORB0100 nunca usó. Reutiliza tools/orb0100/orb0100_v2.py (senales, operar) sin cambios,
# fuentes_ticks, grilla_generica.contexto_m1, oro_0530.trimestres y funnel/escalera. Entorno: FRICCION / FRICCION_ADV (puntos de NQ).
# Salida: ORB0100_ATRAS.json y ORB0100_ATRAS_operaciones.csv.
import json
import os
import time

import numpy as np
import pandas as pd

FUENTE, D0, D1 = "DK:USATECHIDXUSD", 20230101, 20250804


def velas(ctx):
    """M1 del contexto en el formato de orb0100_v2.cargar (time = inicio de la vela, et, hm, fecha, sesión, vwap, b5, ema5)."""
    d = pd.DataFrame(dict(time=ctx["t"] - 60, open=ctx["o"], high=ctx["h"], low=ctx["l"], close=ctx["c"], volume=ctx["v"]))
    d["et"] = pd.to_datetime(d.time, unit="s", utc=True).dt.tz_convert("America/New_York")
    d["hm"] = d.et.dt.hour * 100 + d.et.dt.minute; d["fecha"] = d.et.dt.date; d["sesion"] = (d.et + pd.Timedelta(hours=6)).dt.date
    tp = (d.high + d.low + d.close) / 3; vol = d.volume.clip(lower=1e-9)
    d["vwap"] = (tp * vol).groupby(d.sesion).cumsum() / vol.groupby(d.sesion).cumsum()
    d["b5"] = d.time // 300; c5 = d.groupby("b5").close.last(); d["ema5"] = d.b5.map(c5.ewm(span=50, adjust=False).mean())
    return d


def main():
    from edgelab.funnel import escalera as ES
    from edgelab.research import fuentes_ticks as F, grilla_generica as GG, oro_0530 as O
    from tools.orb0100 import orb0100_v2 as V
    ent = os.environ.get("ENTRADA", "/kaggle/input"); fr, fra = float(os.environ["FRICCION"]), float(os.environ["FRICCION_ADV"])
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    lector, tick = F.resolver(FUENTE); filas = []
    for lo, hi in O.trimestres(D0, D1):
        try: d = velas(GG.contexto_m1(lector(lo, hi, ent), tick))
        except (ValueError, IndexError): log(f"{lo}-{hi}: sin datos"); continue
        for s in V.senales(d, 100, 115, 1600):                                 # celda congelada: rango 01:00–01:15, cierre 16:00
            if not ((s["c"] > s["vwap"]) if s["dir"] > 0 else (s["c"] < s["vwap"])): continue
            r = V.operar(d, s, 1.5, 0.0, 0.0)                                  # sin tick ni comisión: la fricción canónica va aparte
            if r: filas.append(dict(fecha=int(pd.Timestamp(s["fecha"]).strftime("%Y%m%d")), lado=int(s["dir"]), bruto=float(r[0]), R=float(r[1]), salida=r[2]))
        log(f"{lo}-{hi}: {len(filas)} operaciones acumuladas")
    X = pd.DataFrame(filas); x = X.bruto.to_numpy() - fr; ses = X.fecha.to_numpy()
    rs = ES.resumen_sesiones(x, ses, n_boot=20000)
    res = dict(experimento="ORB0100-ATRAS", codigo=CODIGO_SHA, modulos=MODULOS_SHA, fuente=FUENTE, desde=D0, hasta=D1, friccion_pts=fr,
               friccion_adversa_pts=fra, n=int(len(x)), sesiones=int(len(np.unique(ses))), media=rs["media"], ic90=rs["ic"], p=rs["p_unilateral"],
               mde=float(ES.mde(rs["se"])), media_adversa=float((X.bruto - fra).mean()), bruto=float(X.bruto.mean()), acierto=float((X.salida == "TP").mean()), R_bruto=float(X.R.mean()),
               por_anio={str(a): dict(n=int(len(g)), media=float(g.mean())) for a, g in pd.Series(x).groupby(ses // 10000)},
               largos=float(x[X.lado.to_numpy() == 1].mean()), cortos=float(x[X.lado.to_numpy() == -1].mean()))
    json.dump(res, open("ORB0100_ATRAS.json", "w"), indent=1, default=float); X.to_csv("ORB0100_ATRAS_operaciones.csv", index=False)
    log(json.dumps({k: res[k] for k in ("n", "media", "ic90", "p", "mde", "media_adversa")}, default=float))


if __name__ == "__main__":
    main()
