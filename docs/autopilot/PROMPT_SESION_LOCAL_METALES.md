# Prompt para la sesión local (copiar y pegar)

Necesito datos nuevos de Dukascopy (JForex) para replicar un hallazgo de oro en activos hermanos. Misma metodología y mismo formato que el dataset del oro (`edgelab-dukascopy-xauusd-ticks-m1`):

- Instrumentos (M1 bid/ask OHLC + volumen, y ticks solo si es barato): **XAGUSD (plata), XPTUSD (platino), XPDUSD (paladio) y petróleo WTI y Brent (los CFD de commodities de Dukascopy)**.
- Período: **2022-07-01 a 2026-09-30** (no tocar fechas posteriores: holdout cerrado).
- Formato: parquet `time_utc_ns` (int64, inicio de minuto UTC), `bid_open/high/low/close`, `ask_open/high/low/close`, `bid_vol`, `ask_vol`; un archivo por instrumento (`XAGUSD_m1.parquet`, etc.) y un `calidad.json` por instrumento con: filas, desordenados, bid>ask, precios ≤ 0, huecos > 60 min, y las exclusiones que apliques (como `spot_exclusions` del resolver).
- Subir como UN dataset privado nuevo (por ejemplo `edgelab-dukascopy-metals-energy-m1`) con README que diga zona horaria UTC, versión de JForex, fecha de extracción y SHA256 de cada archivo. No hace falta subir ticks.
- Avisar cuando esté para que la sesión de la nube agregue las fuentes al resolver y corra el estudio ya pre-registrado.
