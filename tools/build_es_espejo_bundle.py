import json
import time
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import duckdb
import pyarrow.parquet as pq
from edgelab.bridge.bars import build_tick_bars
from edgelab.bridge.ticks import TickSeries

PARQUET = REPO / "data/nt8/ES_parquet/ES_03-26_ticks.parquet"
OUT_BUNDLE = REPO / "viewer/nt8_bridge/bundles/ES_03-26_ESPEJO.json"
MANIFEST_JS = REPO / "viewer/nt8_bridge/bundles/manifest.js"

print("1. Generando velas 5m con DuckDB...")
t0 = time.time()
q_5m = """
    SELECT 
        CAST((ts_utc_ns // 1000000000) - ((ts_utc_ns // 1000000000) % 300) AS BIGINT) as time,
        FIRST(price_ticks) * 0.25 as open,
        MAX(price_ticks) * 0.25 as high,
        MIN(price_ticks) * 0.25 as low,
        LAST(price_ticks) * 0.25 as close,
        CAST(SUM(volume) AS DOUBLE) as volume
    FROM 'data/nt8/ES_parquet/ES_03-26_ticks.parquet'
    GROUP BY 1
    ORDER BY 1
"""
rows_5m = duckdb.query(q_5m).fetchall()
candles_5m = [{"time": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])} for r in rows_5m]
print(f"   5m: {len(candles_5m)} velas en {time.time()-t0:.2f}s")

print("2. Generando velas 15m con DuckDB...")
t1 = time.time()
q_15m = """
    SELECT 
        CAST((ts_utc_ns // 1000000000) - ((ts_utc_ns // 1000000000) % 900) AS BIGINT) as time,
        FIRST(price_ticks) * 0.25 as open,
        MAX(price_ticks) * 0.25 as high,
        MIN(price_ticks) * 0.25 as low,
        LAST(price_ticks) * 0.25 as close,
        CAST(SUM(volume) AS DOUBLE) as volume
    FROM 'data/nt8/ES_parquet/ES_03-26_ticks.parquet'
    GROUP BY 1
    ORDER BY 1
"""
rows_15m = duckdb.query(q_15m).fetchall()
candles_15m = [{"time": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])} for r in rows_15m]
print(f"   15m: {len(candles_15m)} velas en {time.time()-t1:.2f}s")

print("3. Generando velas 25t de la ventana reciente (marzo 2026)...")
t2 = time.time()
pf = pq.ParquetFile(str(PARQUET))
rg_count = min(3, pf.num_row_groups)
tables = []
for rg in range(pf.num_row_groups - rg_count, pf.num_row_groups):
    tables.append(pf.read_row_group(rg, columns=["ts_utc_ns", "price_ticks", "volume"]))
import pyarrow as pa
recent_table = pa.concat_tables(tables)
ts_obj = TickSeries(
    ts_ns=recent_table["ts_utc_ns"].to_numpy(),
    price_ticks=recent_table["price_ticks"].to_numpy(),
    volume=recent_table["volume"].to_numpy().astype("int64"),
    bid_ticks=None,
    ask_ticks=None,
    sequence=None,
    contract="ES 03-26",
    instrument="ES",
    tick_size=0.25,
    source="Kaggle_Preholdout"
)
bars_25t = build_tick_bars(ts_obj, 25, reiniciar_por_sesion=False)
candles_25t = []
for i in range(len(bars_25t)):
    candles_25t.append({
        "time": int(bars_25t.end_ns[i] // 1_000_000_000),
        "open": float(bars_25t.open_t[i]) * 0.25,
        "high": float(bars_25t.high_t[i]) * 0.25,
        "low": float(bars_25t.low_t[i]) * 0.25,
        "close": float(bars_25t.close_t[i]) * 0.25,
        "volume": float(bars_25t.volume[i])
    })
print(f"   25t: {len(candles_25t)} velas en {time.time()-t2:.2f}s")

print("4. Guardando bundle JSON...")
bundle_data = {
    "meta": {
        "id": "ES_03-26_ESPEJO",
        "name": "ES 03-26 · Espejo (5m / 15m / 25t)",
        "instrument": "ES",
        "contract": "ES 03-26",
        "tick_size": 0.25,
        "precision": 2,
        "n_zones": 0
    },
    "bar_series": {
        "time_5m": {
            "kind": "time_5m",
            "name": "5 Minuto (Macro Continuo)",
            "candles": candles_5m
        },
        "time_15m": {
            "kind": "time_15m",
            "name": "15 Minuto (Macro)",
            "candles": candles_15m
        },
        "tick_25": {
            "kind": "tick_25",
            "name": "25 Tick (Micro Sesión)",
            "candles": candles_25t
        }
    },
    "runs": []
}

OUT_BUNDLE.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_BUNDLE, "w", encoding="utf-8") as f:
    json.dump(bundle_data, f)
print(f"   Bundle guardado en {OUT_BUNDLE} ({OUT_BUNDLE.stat().st_size / (1024*1024):.2f} MB)")

print("5. Actualizando manifest.js...")
entry = {
    "id": "ES_03-26_ESPEJO",
    "name": "ES 03-26 · Espejo (5m / 15m / 25t)",
    "group": "ES (Espejo Impulsos)",
    "instrument": "ES",
    "contract": "ES 03-26",
    "tick_size": 0.25,
    "precision": 2,
    "candles": len(candles_5m),
    "zones": 0,
    "rolls": 0,
    "parity_status": "PARITY_ABSTAIN"
}

content = MANIFEST_JS.read_text(encoding="utf-8")
if '"ES_03-26_ESPEJO"' not in content:
    idx = content.find("window.ASSET_CATALOG = [")
    if idx != -1:
        insert_pos = idx + len("window.ASSET_CATALOG = [\n")
        new_content = content[:insert_pos] + "  " + json.dumps(entry, indent=2).replace("\n", "\n  ") + ",\n" + content[insert_pos:]
        MANIFEST_JS.write_text(new_content, encoding="utf-8")
        print("   Entrada agregada al principio de window.ASSET_CATALOG en manifest.js")
else:
    print("   Entrada ya existía en manifest.js")

print("Listo! Bundle creado y registrado con éxito.")
