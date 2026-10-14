"""L2 fixture tooling v0 — parser NT8 + validador estructural.

Regla de uso (HP-006, enmienda 2026-08-31): los archivos fechados dentro del
holdout (ej. 20260828.csv, export historical de la prueba gratuita de NT8) son
FIXTURES DE TOOLING (`TOOLING_FIXTURE_NOT_MEASUREMENT_DATA`): se usan para
desarrollar y validar el parser/ETL. Este script solo reporta propiedades
ESTRUCTURALES del feed (formato, dominios, completitud de campos, invariantes
del parser). Ninguna estadística de mercado (spread, imbalance, profundidad,
patrones de sesión) se computa ni se imprime desde esos archivos.

Uso: python3 tools/l2_fixture_validate.py <archivo.csv>
Formato esperado (export NT8): 9 campos ';' sin header, decimales con ',':
record_type;market_data_type;timestamp;subsecond;operation;position;market_maker;price;volume
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

COLS = ["record_type", "market_data_type", "timestamp", "subsecond",
        "operation", "position", "market_maker", "price", "volume"]

f = Path(sys.argv[1] if len(sys.argv) > 1 else "/data/zb_l2_sample/20260828.csv")
print(f"fixture: {f.name}")

raw = pd.read_csv(f, sep=";", header=None, names=COLS, dtype=str,
                  na_values=[""], keep_default_na=False, on_bad_lines="warn")
print(f"filas leídas: {len(raw):,}")

empty = {c: int((raw[c] == "").sum()) for c in COLS}
print(f"campos vacíos por columna: { {k: v for k, v in empty.items() if v} or 'ninguno' }")

print(f"record_type: {raw['record_type'].value_counts().to_dict()}")
mdt = pd.to_numeric(raw["market_data_type"], errors="coerce")
print(f"market_data_type: valores {sorted(mdt.dropna().unique().astype(int).tolist())}, no-parseables: {int(mdt.isna().sum())}")
# NT8 MarketDataType: Ask=0, Bid=1, Last=2, DailyHigh=3, DailyLow=4, DailyVolume=5; identificar el 8 observado.
op = pd.to_numeric(raw["operation"], errors="coerce")
pos = pd.to_numeric(raw["position"], errors="coerce")
print(f"operation: valores {sorted(op.dropna().unique().astype(int).tolist())} (NT8: Add=0/Update=1/Remove=2), no-parseables: {int(op.isna().sum())}")
print(f"position: rango [{int(pos.min())}..{int(pos.max())}] (dominio válido 0..10), no-parseables: {int(pos.isna().sum())}")

TS_FMT_OK = raw["timestamp"].str.fullmatch(r"\d{14}")
print(f"timestamp con formato YYYYMMDDHHMMSS: {int(TS_FMT_OK.sum()):,} / {len(raw):,}")
ts = pd.to_datetime(raw["timestamp"], format="%Y%m%d%H%M%S", errors="coerce")
sub = pd.to_numeric(raw["subsecond"], errors="coerce")
print(f"timestamp parseable: {int(ts.notna().sum()):,} | subsecond parseable: {int(sub.notna().sum()):,} | subsecond rango [{sub.min():.0f}..{sub.max():.0f}]")
if ts.notna().all():
    ns = ts.astype("int64") + (sub.fillna(0).astype("int64") * 100)  # subsecond en unidades de 100ns
    d = np.diff(ns.to_numpy())
    print(f"monotonía ts: violaciones (d<0): {int((d < 0).sum()):,} | empates exactos (d=0): {int((d == 0).sum()):,}")
print(f"fecha(s) en el archivo: {sorted(ts.dt.date.unique().astype(str).tolist())} (si no cruza medianoche => el export es día-calendario de la TZ fuente, no sesión CME: el ETL debe re-cortar por 17:00 CT)")

price = pd.to_numeric(raw["price"].str.replace(",", ".", regex=False), errors="coerce")
print(f"price parseable: {int(price.notna().sum()):,} / {len(raw):,}")
on_grid = np.isclose((price / 0.03125) % 1, 0, atol=1e-9) | np.isclose((price / 0.03125) % 1, 1, atol=1e-9)
pos_price = price > 0
print(f"price > 0: {int(pos_price.sum()):,} | de esos, fuera de la grilla 1/32: {int((~on_grid[pos_price]).sum()):,}")
vol = pd.to_numeric(raw["volume"], errors="coerce")
print(f"volume parseable: {int(vol.notna().sum()):,} | negativos: {int((vol < 0).sum())}")

print(f"duplicados exactos de fila: {int(raw.duplicated().sum()):,}")

l2 = raw["record_type"] == "L2"
sub_df = raw.loc[raw.index[l2][:200_000]]
ask_rows = sub_df[pd.to_numeric(sub_df["market_data_type"], errors="coerce") == 0]
bid_rows = sub_df[pd.to_numeric(sub_df["market_data_type"], errors="coerce") == 1]
print(f"[decoder-check] filas L2 en muestra: {len(sub_df):,} (ask={len(ask_rows):,}, bid={len(bid_rows):,})")
print("FIN — solo propiedades estructurales reportadas. Ninguna estadística de mercado computada.")
