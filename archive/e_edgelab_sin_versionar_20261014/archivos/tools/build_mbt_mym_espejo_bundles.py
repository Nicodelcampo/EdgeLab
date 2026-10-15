import json
import time
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import duckdb
import pyarrow.parquet as pq
import pyarrow as pa
from edgelab.bridge.bars import build_tick_bars
from edgelab.bridge.ticks import TickSeries

MANIFEST_JS = REPO / "viewer/nt8_bridge/bundles/manifest.js"
BUNDLES_DIR = REPO / "viewer/nt8_bridge/bundles"

def build_bundle(asset_id, name, group, instrument, contract, tick_size, precision, parquet_path, max_ticks_25t=None):
    print(f"\n==========================================")
    print(f"Construyendo bundle para {asset_id} ({instrument})...")
    print(f"==========================================")
    
    # 1. 5m
    t0 = time.time()
    q_5m = f"""
        SELECT 
            CAST((ts_utc_ns // 1000000000) - ((ts_utc_ns // 1000000000) % 300) AS BIGINT) as time,
            FIRST(price_ticks) * {tick_size} as open,
            MAX(price_ticks) * {tick_size} as high,
            MIN(price_ticks) * {tick_size} as low,
            LAST(price_ticks) * {tick_size} as close,
            CAST(SUM(volume) AS DOUBLE) as volume
        FROM '{parquet_path.as_posix()}'
        GROUP BY 1
        ORDER BY 1
    """
    rows_5m = duckdb.query(q_5m).fetchall()
    candles_5m = [{"time": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])} for r in rows_5m]
    print(f"1. 5m: {len(candles_5m)} velas en {time.time()-t0:.2f}s")

    # 2. 15m
    t1 = time.time()
    q_15m = f"""
        SELECT 
            CAST((ts_utc_ns // 1000000000) - ((ts_utc_ns // 1000000000) % 900) AS BIGINT) as time,
            FIRST(price_ticks) * {tick_size} as open,
            MAX(price_ticks) * {tick_size} as high,
            MIN(price_ticks) * {tick_size} as low,
            LAST(price_ticks) * {tick_size} as close,
            CAST(SUM(volume) AS DOUBLE) as volume
        FROM '{parquet_path.as_posix()}'
        GROUP BY 1
        ORDER BY 1
    """
    rows_15m = duckdb.query(q_15m).fetchall()
    candles_15m = [{"time": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])} for r in rows_15m]
    print(f"2. 15m: {len(candles_15m)} velas en {time.time()-t1:.2f}s")

    # 3. 25t
    t2 = time.time()
    pf = pq.ParquetFile(str(parquet_path))
    if max_ticks_25t and pf.metadata.num_rows > max_ticks_25t:
        # Leer grupos finales hasta acumular max_ticks_25t
        tables = []
        accum = 0
        for rg in range(pf.num_row_groups - 1, -1, -1):
            tables.append(pf.read_row_group(rg, columns=["ts_utc_ns", "price_ticks", "volume"]))
            accum += pf.metadata.row_group(rg).num_rows
            if accum >= max_ticks_25t:
                break
        tables.reverse()
        recent_table = pa.concat_tables(tables)
    else:
        recent_table = pf.read(columns=["ts_utc_ns", "price_ticks", "volume"])

    ts_obj = TickSeries(
        ts_ns=recent_table["ts_utc_ns"].to_numpy(),
        price_ticks=recent_table["price_ticks"].to_numpy(),
        volume=recent_table["volume"].to_numpy().astype("int64"),
        bid_ticks=None,
        ask_ticks=None,
        sequence=None,
        contract=contract,
        instrument=instrument,
        tick_size=tick_size,
        source="Kaggle_Preholdout"
    )
    bars_25t = build_tick_bars(ts_obj, 25, reiniciar_por_sesion=False)
    candles_25t = []
    for i in range(len(bars_25t)):
        candles_25t.append({
            "time": int(bars_25t.end_ns[i] // 1_000_000_000),
            "open": float(bars_25t.open_t[i]) * tick_size,
            "high": float(bars_25t.high_t[i]) * tick_size,
            "low": float(bars_25t.low_t[i]) * tick_size,
            "close": float(bars_25t.close_t[i]) * tick_size,
            "volume": float(bars_25t.volume[i])
        })
    print(f"3. 25t: {len(candles_25t)} velas en {time.time()-t2:.2f}s")

    # 4. JSON
    bundle_data = {
        "meta": {
            "id": asset_id,
            "name": name,
            "instrument": instrument,
            "contract": contract,
            "tick_size": tick_size,
            "precision": precision,
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

    out_file = BUNDLES_DIR / f"{asset_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(bundle_data, f)
    print(f"4. Guardado {out_file} ({out_file.stat().st_size / (1024*1024):.2f} MB)")

    return {
        "id": asset_id,
        "name": name,
        "group": group,
        "instrument": instrument,
        "contract": contract,
        "tick_size": tick_size,
        "precision": precision,
        "candles": len(candles_5m),
        "zones": 0,
        "rolls": 0,
        "parity_status": "PARITY_ABSTAIN"
    }

def main():
    BUNDLES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. MBT 07-26
    mbt_parquet = REPO / "data/nt8/MBT_parquet/MBT_07-26_ticks.parquet"
    entry_mbt = build_bundle(
        asset_id="MBT_07-26_ESPEJO",
        name="MBT 07-26 · Espejo (5m / 15m / 25t)",
        group="MBT (Espejo Impulsos)",
        instrument="MBT",
        contract="MBT 07-26",
        tick_size=5.0,
        precision=1,
        parquet_path=mbt_parquet
    )
    # También alias MBT_ESPEJO
    import shutil
    shutil.copyfile(BUNDLES_DIR / "MBT_07-26_ESPEJO.json", BUNDLES_DIR / "MBT_ESPEJO.json")
    entry_mbt_alias = dict(entry_mbt)
    entry_mbt_alias["id"] = "MBT_ESPEJO"
    entry_mbt_alias["name"] = "MBT · Espejo (5m / 15m / 25t)"

    # 2. MYM 03-26
    mym_parquet = REPO / "data/nt8_research_v2/MYM_parquet/MYM_03-26_ticks.parquet"
    entry_mym = build_bundle(
        asset_id="MYM_03-26_ESPEJO",
        name="MYM 03-26 · Espejo (5m / 15m / 25t)",
        group="MYM (Espejo Impulsos)",
        instrument="MYM",
        contract="MYM 03-26",
        tick_size=1.0,
        precision=0,
        parquet_path=mym_parquet,
        max_ticks_25t=2_500_000
    )
    # También alias MYM_ESPEJO
    shutil.copyfile(BUNDLES_DIR / "MYM_03-26_ESPEJO.json", BUNDLES_DIR / "MYM_ESPEJO.json")
    entry_mym_alias = dict(entry_mym)
    entry_mym_alias["id"] = "MYM_ESPEJO"
    entry_mym_alias["name"] = "MYM · Espejo (5m / 15m / 25t)"

    # También copiar bundles preexistentes de EdgeLab-multiasset si existen
    multiasset_bundles = Path("E:/EdgeLab-multiasset/viewer/nt8_bridge/bundles")
    for b_name in ["MBT_07-26_25T.json", "MYM_03-26_25T.json"]:
        src = multiasset_bundles / b_name
        if src.exists() and not (BUNDLES_DIR / b_name).exists():
            shutil.copyfile(src, BUNDLES_DIR / b_name)
            print(f"Copiado {b_name} desde EdgeLab-multiasset")

    # Actualizar manifest.js
    content = MANIFEST_JS.read_text(encoding="utf-8")
    entries_to_add = [entry_mbt, entry_mbt_alias, entry_mym, entry_mym_alias]
    
    # filtrar las que no están ya
    new_entries = [e for e in entries_to_add if f'"{e["id"]}"' not in content]
    if new_entries:
        idx = content.find("window.ASSET_CATALOG = [")
        if idx != -1:
            insert_pos = idx + len("window.ASSET_CATALOG = [\n")
            to_insert = "  " + ",\n  ".join(json.dumps(e, indent=2).replace("\n", "\n  ") for e in new_entries) + ",\n"
            content = content[:insert_pos] + to_insert + content[insert_pos:]
            MANIFEST_JS.write_text(content, encoding="utf-8")
            print(f"Agregadas {len(new_entries)} entradas a manifest.js")
    else:
        print("Todas las entradas ya existían en manifest.js")

    print("\n¡Proceso finalizado exitosamente!")

if __name__ == "__main__":
    main()
