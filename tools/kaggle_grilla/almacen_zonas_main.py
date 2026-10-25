# Principal del kernel ALMACÉN DE ZONAS (target-free; docs/research/u1_zonas_20261025/SPEC_U1_ZONAS.md): corre un indicador de
# zonas PASS sobre los ticks de operaciones de un futuro del release y guarda cada zona con su hora de creación (cierre de la barra
# que la crea) y su banda de precio, para que la gramática de U1 (edgelab/research/u1_zonas.py) la use como fuente de zonas.
# Indicadores: aVolZonePOI2 (edgelab/bridge/indicators/avolzonepoi2.py, PASS en MNQ 25t). Reutiliza fuentes_ticks.bloques_futuro,
# edgelab/bridge/bars (barras de N ticks, footprint total NT8, sesiones) y oro_0530.trimestres. Sin desenlaces ni retornos.
# Entorno: INSTS (p. ej. "ES,NQ"), SPEC (ticks por barra, 25). Salida: ZONAS_AVZP2_<INST>.parquet y ALMACEN_ZONAS.json.
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


def main():
    from edgelab.research import fuentes_ticks as F, oro_0530 as O
    ent = os.environ.get("ENTRADA", "/kaggle/input"); spec = int(os.environ.get("SPEC", "25"))
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    res = dict(experimento="ALMACEN-ZONAS", indicador="aVolZonePOI2", spec=spec, params=PARAMS, codigo=CODIGO_SHA, modulos=MODULOS_SHA, instrumentos={})
    for inst in os.environ.get("INSTS", "ES,NQ").split(","):
        tick = F.TICK_FUTURO[inst]; partes = []
        for lo, hi in O.trimestres(D0, D1):
            lo_c = int((pd.Timestamp(str(lo)) - pd.Timedelta(days=CALENTAR)).strftime("%Y%m%d"))
            try: Z = zonas_avzp2(F.bloques_futuro(inst, max(lo_c, D0), hi, ent), tick, spec)
            except (ValueError, IndexError) as e: log(f"{inst} {lo}-{hi}: sin datos ({e})"); continue
            if len(Z):
                td = F._td(Z.t_ns.to_numpy()); Z = Z[(td >= lo) & (td <= hi)]; partes.append(Z)
            log(f"{inst} {lo}-{hi}: {len(Z)} zonas")
        Z = pd.concat(partes, ignore_index=True).sort_values("t_ns") if partes else pd.DataFrame()
        Z.to_parquet(f"ZONAS_AVZP2_{inst}.parquet", index=False)
        res["instrumentos"][inst] = dict(zonas=int(len(Z)), sesiones=int(len(np.unique(F._td(Z.t_ns.to_numpy())))) if len(Z) else 0,
                                         alto_mediano_ticks=float(((Z.hi - Z.lo) / tick).median()) if len(Z) else None)
    json.dump(res, open("ALMACEN_ZONAS.json", "w"), indent=1, default=float)
    log(json.dumps(res["instrumentos"]))


if __name__ == "__main__":
    main()
