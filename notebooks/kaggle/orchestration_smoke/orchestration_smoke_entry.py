"""Prueba de humo de orquestación: ¿un análisis lanzado desde afuera corre en Kaggle con datasets de EdgeLab?

**Target-free. No lee ninguna fila de datos de mercado.** Solo metadatos:

- lista lo que hay montado en /kaggle/input (nombres y tamaños);
- para cada parquet, lee el PIE (`ParquetFile.metadata`: filas, columnas, estadísticas por row-group) y
  compara el máximo de la columna de tiempo contra la frontera del holdout, SIN leer páginas de datos.

Sirve para tres cosas: (1) probar el camino completo crear -> montar datasets -> ejecutar -> recuperar salida;
(2) auditar de forma independiente que los datasets `*-preholdout` no contienen holdout (la migración a Kaggle
lo afirmó; esto lo verifica del lado del servidor); (3) dejar un patrón reutilizable para lanzar análisis.

Salida: /kaggle/working/orchestration_smoke.json
"""
import json
import os
import platform
import sys
import time

HOLDOUT_NS = 1782856800000000000          # 2026-06-30T22:00:00Z; el holdout empieza acá
TS_COLS = ("ts_utc_ns", "ts_ns", "timestamp_ns", "time_ns")

t0 = time.time()
out = {"schema": "edgelab_orchestration_smoke_v1", "holdout_boundary_ns": HOLDOUT_NS,
       "python": sys.version.split()[0], "platform": platform.platform(), "cpus": os.cpu_count(),
       "datasets": [], "rows_read": 0}

try:
    import pyarrow
    import pyarrow.parquet as pq
    out["pyarrow"] = pyarrow.__version__
except Exception as e:                              # pragma: no cover
    out["pyarrow"] = None
    out["pyarrow_error"] = str(e)[:200]
    pq = None

root = "/kaggle/input"
for dirpath, dirnames, filenames in os.walk(root):
    depth = dirpath[len(root):].count(os.sep)
    if depth > 3:
        dirnames[:] = []
        continue
    files = [f for f in filenames]
    if not files:
        continue
    entry = {"dir": dirpath, "n_files": len(files),
             "bytes": sum(os.path.getsize(os.path.join(dirpath, f)) for f in files), "parquets": []}
    if pq is not None:
        for f in sorted(files):
            if not f.endswith(".parquet"):
                continue
            p = os.path.join(dirpath, f)
            rec = {"file": f, "bytes": os.path.getsize(p)}
            try:
                pf = pq.ParquetFile(p)               # SOLO el pie: no se leen filas
                md = pf.metadata
                rec["num_rows"] = md.num_rows
                rec["num_row_groups"] = md.num_row_groups
                rec["columns"] = [md.schema.column(i).name for i in range(md.num_columns)][:30]
                ts_idx = next((i for i in range(md.num_columns) if md.schema.column(i).name in TS_COLS), None)
                if ts_idx is None:
                    rec["holdout_check"] = "NO_TIME_COLUMN_IN_SCHEMA"
                else:
                    mins, maxs, sin_stats = [], [], 0
                    for g in range(md.num_row_groups):
                        st = md.row_group(g).column(ts_idx).statistics
                        if st is None or not st.has_min_max:
                            sin_stats += 1
                        else:
                            mins.append(int(st.min)); maxs.append(int(st.max))
                    rec["row_groups_sin_estadisticas"] = sin_stats
                    if maxs:
                        rec["ts_min_ns"], rec["ts_max_ns"] = min(mins), max(maxs)
                        rec["holdout_check"] = ("PASS_MAX_BEFORE_HOLDOUT" if max(maxs) < HOLDOUT_NS
                                                else "FAIL_HOLDOUT_PRESENT")
                        if sin_stats:
                            rec["holdout_check"] += "_PARTIAL_STATS"
                    else:
                        rec["holdout_check"] = "ABSTAIN_NO_STATISTICS"
            except Exception as e:
                rec["error"] = str(e)[:200]
            entry["parquets"].append(rec)
    out["datasets"].append(entry)

out["elapsed_s"] = round(time.time() - t0, 2)
chk = [r.get("holdout_check", "") for d in out["datasets"] for r in d["parquets"]]
out["resumen"] = {"parquets_revisados": len(chk),
                  "pass": sum(1 for c in chk if c.startswith("PASS")),
                  "fail": sum(1 for c in chk if c.startswith("FAIL")),
                  "abstain_o_sin_stats": sum(1 for c in chk if not c.startswith(("PASS", "FAIL")))}
os.makedirs("/kaggle/working", exist_ok=True)
with open("/kaggle/working/orchestration_smoke.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1)
print("orchestration-smoke OK", json.dumps(out["resumen"]))
