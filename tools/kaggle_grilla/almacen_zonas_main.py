# Principal del kernel ALMACÉN DE ZONAS (target-free; docs/research/u1_zonas_20261025/SPEC_U1_ZONAS.md): corre un indicador de
# zonas PASS sobre los ticks de operaciones de un futuro del release y guarda cada zona con su hora de creación (cierre de la barra
# que la crea) y su banda de precio, para que la gramática de U1 (edgelab/research/u1_zonas.py) la use como fuente de zonas.
# Indicadores: aVolZonePOI2 (edgelab/bridge/indicators/avolzonepoi2.py, PASS en MNQ 25t). Reutiliza fuentes_ticks.bloques_futuro,
# edgelab/bridge/bars (barras de N ticks, footprint total NT8, sesiones) y oro_0530.trimestres. Sin desenlaces ni retornos.
# Entorno: INDICADOR (AVZP2 | AVCL | BT2 | AVZRG), INSTS (p. ej. "ES,NQ"), SPEC (ticks por barra; 25 y 50 por defecto).
# Salida: ZONAS_<IND>_<INST>.parquet y ALMACEN_ZONAS_<IND>.json.
import json
import os
import time

import numpy as np
import pandas as pd

D0, D1 = 20250701, 20260930
CALENTAR = 45                      # días previos por trimestre: el umbral del indicador pide 20 sesiones de historia
PARAMS = dict(ob_away_heights=6.0, ob_max_inside_pct=4.0, racimo_min=0, racimo_bars=500, racimo_altura_ticks=30)   # = réplica AVZP2


def zonas_avzp2(bloques, tick, spec):
    from edgelab.bridge import bars as B
    from edgelab.bridge.indicators.avolzonepoi2 import run
    from edgelab.bridge.ticks import TickSeries
    bl = list(bloques)
    if not bl: return pd.DataFrame()
    ts = np.concatenate([b.ts_ns.to_numpy() for b in bl]); px = np.concatenate([b.px.to_numpy() for b in bl])
    vol = np.concatenate([b.vol.to_numpy() for b in bl]); del bl
    tk = TickSeries(ts_ns=ts, price_ticks=np.round(px / tick).astype(np.int64), volume=vol.astype(np.int64), bid_ticks=None, ask_ticks=None,
                    sequence=np.arange(len(ts), dtype=np.int64), tick_size=tick)
    bars = B.build_tick_bars(tk, spec); fps = B.build_total_footprint_csr_nt8(tk, bars); del tk
    end = np.asarray(bars.end_ns, np.int64)
    r = run(bars, fps, B.session_ids(end), PARAMS)
    Z = pd.DataFrame([dict(t_ns=z["end_ns"], lo=z["low_tick"] * tick, hi=z["high_tick"] * tick, niveles=z["levels"], score=z["score"],
                           estado=z["state"], t_decidida_ns=int(end[z["decided_bar"]]) if z["decided_bar"] is not None else -1)
                      for z in r["zones"]])
    return Z


def zonas_avcl(bloques, tick, spec):
    """aVolClusterPOI (PASS en MNQ 50t y 200t; footprint NT8 de subserie de 1 tick)."""
    from edgelab.bridge import bars as B
    from edgelab.bridge.indicators.avolclusterpoi import run
    from edgelab.bridge.ticks import TickSeries
    bl = list(bloques)
    if not bl: return pd.DataFrame()
    ts = np.concatenate([b.ts_ns.to_numpy() for b in bl]); px = np.concatenate([b.px.to_numpy() for b in bl])
    vol = np.concatenate([b.vol.to_numpy() for b in bl]); del bl
    tk = TickSeries(ts_ns=ts, price_ticks=np.round(px / tick).astype(np.int64), volume=vol.astype(np.int64), bid_ticks=None, ask_ticks=None,
                    sequence=np.arange(len(ts), dtype=np.int64), tick_size=tick)
    bars = B.build_tick_bars(tk, spec); fps = B.build_footprints(tk, bars, nt8_subseries=True)
    r = run(tk, bars, fps); del tk
    return pd.DataFrame([dict(t_ns=int(z["created_ms"]) * 10**6, lo=float(z["bottom"]), hi=float(z["top"])) for z in r["zones"]])


def zonas_bt2(bloques, tick, spec):
    """BigTrap2 (PASS_CON_CAVEAT; oráculo O1 Diagonal sobre barras de `spec` minutos): la zona RECTANGULAR (bottom/top) que el
    indicador extiende hasta su invalidación (CloseThrough) o su expiración (max_age_bars); `t_fin_ns` = fin conocido al cerrarse
    (−1 si sigue activa al final del tramo). No son los círculos (TRAPs exportados): sólo las zonas dibujadas."""
    from edgelab.bridge import bars as B
    from edgelab.bridge.indicators.bigtrap2 import run
    from edgelab.bridge.ticks import TickSeries
    bl = list(bloques)
    if not bl: return pd.DataFrame()
    cat = lambda c: np.concatenate([b[c].to_numpy() for b in bl])
    ts, px, vol, bid, ask = cat("ts_ns"), cat("px"), cat("vol"), cat("bid"), cat("ask"); del bl
    q = lambda x: np.where(np.isfinite(x), np.round(np.nan_to_num(x) / tick), -1).astype(np.int64)
    tk = TickSeries(ts_ns=ts, price_ticks=np.round(px / tick).astype(np.int64), volume=vol.astype(np.int64), bid_ticks=q(bid), ask_ticks=q(ask),
                    sequence=np.arange(len(ts), dtype=np.int64), tick_size=tick)
    bars = B.build_time_bars(tk, spec); fps = B.build_footprints(tk, bars)
    r = run(tk, bars, fps); del tk
    return pd.DataFrame([dict(t_ns=int(z["created_ms"]) * 10**6, lo=float(z["bottom"]), hi=float(z["top"]),
                              t_fin_ns=int(z["ended_ms"]) * 10**6 if z.get("ended_ms") else -1,
                              lado=1 if z["kind"] == "trapped_buyers" else -1) for z in r["zones"]])


def racimos_de(zonas, p):
    """Racimos de una lista de zonas de AVZP2 (bar, low_tick, high_tick, en orden de creación) con la regla `_racimo` del indicador
    (se importa, no se copia): un registro por racimo AL FORMARSE (banda de ese momento, barra de formación)."""
    from edgelab.bridge.indicators.avolzonepoi2 import _racimo
    hechas, clusters = [], []
    for z in zonas:
        nz = dict(bar=z["bar"], low_tick=z["low_tick"], high_tick=z["high_tick"], racimo_bar=-1, rac=None)
        _racimo(nz, hechas, clusters, nz["bar"], p); hechas.append(nz)
    return [dict(bar=c["bar"], low=c["low0"], high=c["high0"]) for c in clusters]


# Grilla de racimos de AVZP2 (2026-10-26, Nico: «muchas perillas, de la zona individual y del racimo; optimizalo y usá las variantes que
# valen la pena»). Zona: percentil {90, 95, 98} × multiplicador de la mediana {1,5; 2; 3} × velas por bloque {10, 20} × ancho mínimo
# del cluster {2, 3} ticks = 36 (el resto queda en la réplica AVZP2: bucket 15 min, 20 sesiones, Suma). Racimo: mínimo {4, 6, 8} ×
# ventana {500, 1000} velas × altura {30, 45} ticks = 12 (las ventanas largas y alturas medias/anchas son donde AVZP2-RACIMO-GRILLA
# vio compresión 23/23 y O1). Tipo = zona·12 + racimo (432). Pre-registro: PREREGISTRO_U1_ZONAS_BT2_AVZR.md.
GRILLA_ZONA = [dict(detection_percentile=pc, median_multiplier=mm, window_bars=wb, min_cluster_ticks=mc)
               for pc in (90.0, 95.0, 98.0) for mm in (1.5, 2.0, 3.0) for wb in (10, 20) for mc in (2, 3)]
GRILLA_RACIMO = [dict(racimo_min=m, racimo_bars=w, racimo_altura_ticks=a) for m in (4, 6, 8) for w in (500, 1000) for a in (30, 45)]


def zonas_avzrg(bloques, tick, spec):
    """Racimos de AVZP2 de toda la grilla: un DataFrame (t_ns de formación, lo, hi, zona, racimo). Las barras y el footprint se
    arman una vez; el indicador corre una vez por definición de zona; los racimos se arman de cada lista de zonas (`racimos_de`)."""
    from edgelab.bridge import bars as B
    from edgelab.bridge.indicators.avolzonepoi2 import run
    from edgelab.bridge.ticks import TickSeries
    bl = list(bloques)
    if not bl: return pd.DataFrame()
    ts = np.concatenate([b.ts_ns.to_numpy() for b in bl]); px = np.concatenate([b.px.to_numpy() for b in bl])
    vol = np.concatenate([b.vol.to_numpy() for b in bl]); del bl
    tk = TickSeries(ts_ns=ts, price_ticks=np.round(px / tick).astype(np.int64), volume=vol.astype(np.int64), bid_ticks=None, ask_ticks=None,
                    sequence=np.arange(len(ts), dtype=np.int64), tick_size=tick)
    bars = B.build_tick_bars(tk, spec); fps = B.build_total_footprint_csr_nt8(tk, bars); del tk
    end = np.asarray(bars.end_ns, np.int64); ses = B.session_ids(end); filas = []
    for iz, pz in enumerate(GRILLA_ZONA):
        zs = sorted(run(bars, fps, ses, dict(PARAMS, **pz, racimo_min=0))["zones"], key=lambda z: z["bar"])
        for ir, pr in enumerate(GRILLA_RACIMO):
            filas += [(int(end[c["bar"]]), c["low"] * tick, c["high"] * tick, iz, ir) for c in racimos_de(zs, pr)]
    return pd.DataFrame(filas, columns=["t_ns", "lo", "hi", "zona", "racimo"])


INDICADORES = {"AVZP2": (zonas_avzp2, 25), "AVCL": (zonas_avcl, 50), "BT2": (zonas_bt2, 1),
               "AVZRG": (zonas_avzrg, 25)}
LIBRO = {"BT2"}                    # indicadores que clasifican el agresor con bid/ask


def main():
    from edgelab.research import fuentes_ticks as F, oro_0530 as O
    ent = os.environ.get("ENTRADA", "/kaggle/input"); ind = os.environ.get("INDICADOR", "AVZP2"); fn, spec = INDICADORES[ind]
    spec = int(os.environ.get("SPEC", spec))
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    res = dict(experimento="ALMACEN-ZONAS", indicador=ind, spec=spec, params=PARAMS, codigo=CODIGO_SHA, modulos=MODULOS_SHA, instrumentos={})
    for inst in os.environ.get("INSTS", "ES,NQ").split(","):
        tick = F.TICK_FUTURO[inst]; partes = {}
        for lo, hi in O.trimestres(D0, D1):
            lo_c = int((pd.Timestamp(str(lo)) - pd.Timedelta(days=CALENTAR)).strftime("%Y%m%d"))
            try: Z = fn(F.bloques_futuro(inst, max(lo_c, D0), hi, ent, libro=ind in LIBRO), tick, spec)
            except (ValueError, IndexError) as e: log(f"{inst} {lo}-{hi}: sin datos ({e})"); continue
            Zd = Z if isinstance(Z, dict) else {ind: Z}
            for nombre, Zi in Zd.items():
                if len(Zi):
                    td = F._td(Zi.t_ns.to_numpy()); Zi = Zi[(td >= lo) & (td <= hi)]
                    partes.setdefault(nombre, []).append(Zi)
                log(f"{inst} {lo}-{hi} {nombre}: {len(Zi)} zonas")
        for nombre, ps in partes.items():
            Z = pd.concat(ps, ignore_index=True).sort_values("t_ns") if ps else pd.DataFrame()
            Z.to_parquet(f"ZONAS_{nombre}_{inst}.parquet", index=False)
            res["instrumentos"][f"{nombre}_{inst}"] = dict(zonas=int(len(Z)), sesiones=int(len(np.unique(F._td(Z.t_ns.to_numpy())))) if len(Z) else 0,
                                                           alto_mediano_ticks=float(((Z.hi - Z.lo) / tick).median()) if len(Z) else None)
    json.dump(res, open(f"ALMACEN_ZONAS_{ind}.json", "w"), indent=1, default=float)
    log(json.dumps(res["instrumentos"]))


if __name__ == "__main__":
    main()
