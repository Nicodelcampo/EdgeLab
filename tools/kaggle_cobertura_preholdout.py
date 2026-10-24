"""Cobertura REAL de los datos en Kaggle hasta la apertura del holdout (pedido de Nico, 2026-10-22). Corre DENTRO de un kernel.

Target-free (integridad): por cada parquet montado en /kaggle/input lee el pie y SOLO la columna de timestamps, grupo por
grupo; un grupo cuyo mínimo ya es holdout no se lee, y dentro de cada grupo se cuentan sólo los timestamps anteriores a la
apertura. Nunca lee precios ni volumen. Para el release líquido lee además `metadata/session_index.parquet`.
Sesión CME = fecha de cierre: (ts en America/Chicago + 7 h).date() (la sesión abre 17:00 CT del día anterior).

  python tools/kaggle_kernel.py push --slug nicolasbuttaro/edgelab-cobertura-preholdout --script tools/kaggle_cobertura_preholdout.py \
      --dataset nicolasbuttaro/<cada dataset de RESOLVER.json> --dataset nicolasbuttaro/edgelab-liquid-ticks-20261014
Salida: cobertura_preholdout.json (por dataset/archivo: instrumento, filas pre-holdout, sesiones; y resumen por instrumento).
"""
import glob
import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HOLDOUT_APERTURA_UTC_NS = 1_790_805_600_000_000_000          # copia de edgelab/holdout.py (verificada por tests/test_holdout_unico.py)
MIN_TICKS_SESION = 1000
TS_COLS = ("ts_utc_ns", "timestamp_ns", "ts_ns", "ts")


def sesiones_de(ts_ns: np.ndarray) -> dict:
    if not len(ts_ns): return {}
    t = pd.to_datetime(ts_ns, utc=True).tz_convert("America/Chicago") + pd.Timedelta(hours=7)
    d = pd.Series(1, index=t.date).groupby(level=0).sum()
    return {str(k): int(v) for k, v in d.items()}


def archivo(path: str) -> dict:
    pf = pq.ParquetFile(path); names = pf.schema_arrow.names
    col = next((c for c in TS_COLS if c in names), None)
    out = dict(file=path.split("/kaggle/input/")[-1], rows=pf.metadata.num_rows, row_groups=pf.num_row_groups, ts_col=col, sesiones={},
               grupos_holdout_saltados=0, ticks_holdout_no_leidos=0)
    if col is None: out["error"] = f"sin columna de timestamp ({names[:8]})"; return out
    ix = names.index(col); ses = defaultdict(int)
    for g in range(pf.num_row_groups):
        st = pf.metadata.row_group(g).column(ix).statistics
        if st is not None and st.has_min_max and int(st.min) >= HOLDOUT_APERTURA_UTC_NS:
            out["grupos_holdout_saltados"] += 1; out["ticks_holdout_no_leidos"] += pf.metadata.row_group(g).num_rows; continue
        ts = pf.read_row_group(g, columns=[col]).column(0).to_numpy()
        if ts.dtype.kind == "M": ts = ts.astype("datetime64[ns]").astype(np.int64)
        keep = ts < HOLDOUT_APERTURA_UTC_NS; out["ticks_holdout_no_leidos"] += int((~keep).sum())
        for k, v in sesiones_de(ts[keep]).items(): ses[k] += v
    out["sesiones"] = dict(sorted(ses.items())); return out


def instrumento(rel: str) -> str:
    base = os.path.basename(rel).split(".")[0]
    return base.split("_")[0].upper()


def main():
    res = dict(holdout_apertura_utc_ns=HOLDOUT_APERTURA_UTC_NS, min_ticks_sesion=MIN_TICKS_SESION, archivos=[], release=None)
    for p in sorted(glob.glob("/kaggle/input/**/*.parquet", recursive=True)):
        if p.endswith("session_index.parquet"):
            si = pd.read_parquet(p)
            res["release"] = dict(file=p.split("/kaggle/input/")[-1], columnas=list(si.columns), por_instrumento={
                str(a): dict(selected=int((g.status == "SELECTED").sum()) if "status" in g else None,
                             desde=int(g.trade_date.min()), hasta=int(g[g.trade_date < 20261001].trade_date.max()),
                             selected_hasta=int(g[(g.get("status") == "SELECTED") & (g.trade_date < 20261001)].trade_date.max()) if "status" in g and (g.status == "SELECTED").any() else None,
                             filas_holdout_en_indice=int((g.trade_date >= 20261001).sum()))
                for a, g in si.groupby("instrument")})
            continue
        if "/metadata/" in p or "liquid-ticks" in p: continue                  # del release basta su índice de sesiones
        try: a = archivo(p)
        except Exception as e: a = dict(file=p, error=repr(e)[:300])
        a["instrumento"] = instrumento(a["file"]); res["archivos"].append(a)
        print(a["file"], a.get("rows"), len(a.get("sesiones", {})), flush=True)
    agg = defaultdict(lambda: defaultdict(int))
    for a in res["archivos"]:
        for d, n in a.get("sesiones", {}).items(): agg[a["instrumento"]][d] += n
    ref = sorted({d for s in agg.values() for d, n in s.items() if n >= MIN_TICKS_SESION})       # calendario observado (unión de activos)
    res["resumen"] = {}
    for inst, s in sorted(agg.items()):
        ok = sorted(d for d, n in s.items() if n >= MIN_TICKS_SESION)
        q3 = [d for d in ref if "2026-07-01" <= d <= "2026-09-30"]
        res["resumen"][inst] = dict(sesiones=len(ok), desde=ok[0] if ok else None, hasta=ok[-1] if ok else None,
                                    jul_sep=sum(d in set(ok) for d in q3), jul_sep_calendario=len(q3),
                                    faltan_jul_sep=[d for d in q3 if d not in set(ok)],
                                    ultimos_dias_sep=[d for d in ("2026-09-28", "2026-09-29", "2026-09-30") if d not in set(ok)])
    res["ticks_holdout_no_leidos_total"] = sum(a.get("ticks_holdout_no_leidos", 0) for a in res["archivos"])
    json.dump(res, open("cobertura_preholdout.json", "w"), indent=1)
    print(json.dumps(res["resumen"], indent=1)[:6000]); print("release", json.dumps(res["release"])[:3000])


if __name__ == "__main__":
    main()
