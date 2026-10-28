"""Kernel de Kaggle: spread MEDIDO de un futuro del release con el criterio del atlas v4 (para instrumentos sin spread en costos).

Criterio (docs/research/REFERENCIA_COSTOS_PROPS_BROKERS_20261014.md): media de ask − bid en ticks sobre los ticks con libro válido
(0 < bid <= ask), horario regular 08:30–15:00 CT, sólo sesiones de desarrollo (antes de la frontera del holdout). Sin P&L.
Entorno: INST (p. ej. 6B). Salida: SPREAD_<INST>.json. Se empaqueta con construir_kernel (embebe edgelab/holdout.py).
"""
import glob
import json
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


def main():
    inst = os.environ["INST"]; ent = os.environ.get("ENTRADA", "/kaggle/input")
    from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS
    f = glob.glob(ent + f"/**/{inst}_ticks.parquet", recursive=True)[0]; pf = pq.ParquetFile(f)
    cols = [c for c in ("ts_utc_ns", "bid_ticks", "ask_ticks", "trade_date") if c in pf.schema_arrow.names]
    sumas, n, por_ses = 0.0, 0, []
    for g in range(pf.num_row_groups):
        t = pf.read_row_group(g, columns=cols).to_pandas()
        t = t[t.ts_utc_ns < HOLDOUT_APERTURA_UTC_NS]
        if not len(t): continue
        ct = pd.to_datetime(t.ts_utc_ns, utc=True).dt.tz_convert("America/Chicago"); m = ct.dt.hour * 60 + ct.dt.minute
        ok = (t.bid_ticks > 0) & (t.ask_ticks >= t.bid_ticks) & (m >= 510) & (m < 900)
        s = (t.ask_ticks - t.bid_ticks)[ok].to_numpy(float)
        if len(s): sumas += s.sum(); n += len(s); por_ses.append(float(np.median(s)))
    out = dict(instrumento=inst, criterio="media ask-bid en ticks, libro válido, 08:30-15:00 CT, desarrollo", spread_ticks_media=sumas / max(n, 1),
               n_ticks=n, sesiones=len(por_ses), p50_mediana_por_sesion=float(np.median(por_ses)) if por_ses else None, archivo=os.path.basename(f))
    json.dump(out, open(f"SPREAD_{inst}.json", "w"), indent=1); print(json.dumps(out))


main()
