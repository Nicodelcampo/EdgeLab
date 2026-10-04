# Problemas conocidos y reglas de uso (leer antes de elegir una fuente)

Escrito a mano el 2026-10-04 con cifras de `catalog.json` y notas de la historia del proyecto (no lo regenera `tools/data_catalog_build.py`: revisarlo cada vez que se regenere el catálogo). Las cifras salen del inventario; las notas de contexto, de `docs/research/HANDOFF_20261004.md`.

## 1. Reglas de uso

1. **Elegir la fuente por instrumento y rango con `tools/data_find.py`**, no por el nombre del dataset. Si hay más de una fuente para el mismo contrato, mirar la tabla de conflictos de `INSTRUMENTS.md`.
2. **El contrato líder y los rolls no son una elección libre:** usar el esquema de `README.md` (mayor volumen de la sesión anterior, monótono, sin ajuste de precios, elegibilidad ≥ 50 % de la mediana del contrato).
3. **Una sesión elegible puede igual ser poco líquida respecto del resto del instrumento:** ver la columna «sesiones del líder < 25 % del volumen mediano» del índice de `INSTRUMENTS.md`.
4. **No leer sesiones desde 2026-10-01.** Hay datos de ese período en: MGC (1 sesión/es), MNQ (2 sesión/es). Julio a septiembre de 2026 es exploración.
5. **Spot (Dukascopy) no es futuro:** solo sirve para estrategias que dependen del precio y con su equivalencia medida (`edgelab/equivalence`).

## 2. Hallazgos del inventario

- **Hay 30 datasets en la cuenta**, no 20: la lista de la API es paginada (20 por página) y el conteo anterior de `HANDOFF_20261004.md` quedó corto. Públicos hoy: `mnq-tick-data`, `mnq-parquet` (ticks de CME: pasarlos a privados).
- **MGC sí tiene ticks posteriores al 30 de junio de 2026 en Kaggle** (`edgelab-mgc-nt8-raw-parquet-20261002`: `MGC_08-26` hasta 2026-08-27 y `MGC_12-26` de 2026-06-12 a 2026-10-01). Esto corrige lo afirmado antes («no hay ticks de oro posteriores al 30 de junio»): vale para **GC** (termina el 2026-06-30), no para MGC. Pero los datos de MGC de julio en adelante tienen problemas: faltan las sesiones 2026-07-02, 07-09, 07-16, 07-30, 08-28 y 09-10 a 09-11; **falta el contrato `MGC_10-26`**, que es el que debió ser líder en agosto y septiembre (el catálogo toma `MGC_12-26` desde 2026-07-31 con volumen de 32.339 en la sesión previa (2026-07-29), muy bajo frente a los cientos de miles de un líder normal); y la sesión de 2026-10-01 pertenece al holdout formal. Utilizable con cuidado: julio (líder `MGC_08-26`).
- **Contratos del ciclo estándar que faltan:** GC: GC_08-25, GC_10-25; MGC: MGC_10-25, MGC_10-26. Para GC los dos primeros son anteriores al inicio de los datos (el tramo agosto-octubre de 2025 queda con líder incompleto); `MGC_10-25` ya figuraba como falta en EF0.
- **Días hábiles sin datos y sin explicación (no son feriados):** 6E: 2026-09-03; ES: 2026-08-27; MBT: 2026-06-01..2026-06-05, 2026-06-08..2026-06-12, 2026-06-15..2026-06-18; MES: 2026-08-06, 2026-08-13; MGC: 2026-07-02, 2026-07-09, 2026-07-16, 2026-07-30, 2026-08-28, 2026-09-10..2026-09-11; MNQ: 2026-03-26, 2026-04-02, 2026-05-21; MYM: 2025-09-22..2025-09-26, 2025-09-29, 2026-07-09, 2026-07-16, 2026-07-23, 2026-07-30, 2026-08-20; RTY: 2025-09-22..2025-09-26, 2025-09-29..2025-10-01; YM: 2026-08-20.
- **Liquidez baja del líder:** sesiones por debajo del 25 % del volumen mediano del instrumento: ES 5, MBT 22. MYM, RTY y MBT son los más afectados; no usarlos como series continuas sin un filtro de liquidez más estricto.
- **Artefacto de roll en MGC:** el roll `MGC_02-26 → MGC_04-26` (2026-01-12) se decidió con volúmenes de 1 y 2 de una sesión de domingo casi vacía; la regla «mayor volumen en la sesión anterior» es frágil cuando la sesión previa es un domingo. Conviene que la regla ignore sesiones de menos de la mitad de los minutos típicos.
- **Fuentes que se contradicen de forma material:** `MNQ_12-26` entre `edgelab-ticks-nt8-canonical` y `mnq-parquet` (42 de 63 días comunes con más de 1 % de diferencia en trades; `mnq-parquet` tiene más en 42 días): usar `mnq-parquet` solo después de revisar qué falta en la otra. Diferencias menores (pocos días con más de 1 %) en `ES_03-26`, `NQ_12-25` y `NQ_06-26` entre `edgelab-nt8-historical-missing-20261001` y los `*-preholdout`; el resto de los contratos duplicados coincide en casi todos los días.
- **Los `*-preholdout` son rebanadas parciales** (corte 2026-06-30T22:00Z, no cubren toda la vida de cada contrato): EF0 los marca no elegibles para backtest continuo.

## 3. Esquemas distintos (no asumir las columnas)

| Familia de archivos | Columnas clave | Observación |
|---|---|---|
| Canónico (`*-preholdout`, `nt8-canonical`, `historical-missing`, `es-nq-2026q3-ext`) | `ts_utc_ns`, `price_ticks`, `bid_ticks`, `ask_ticks`, `volume`, `aggressor`, `tick_type`, `contract` | precios en ticks enteros |
| Crudo NinjaTrader de MGC (`edgelab-mgc-nt8-raw-parquet-20261002`) | `ts_utc_ns`, `last`, `bid`, `ask`, `volume`, `sequence`, `source_day_nt_local` | precios en unidades de precio, sin agresor |
| Exportación del usuario (`mnq-parquet`) | `ts` (timestamp[ns], **sin zona**, tratado como UTC según el handoff), `last`, `bid`, `ask`, `volume` | verificar la zona antes de unir con otras fuentes |
| Dukascopy spot (`edgelab-dukascopy-xauusd-ticks-m1`) | ticks: `time_utc_ns`, `bid`, `ask`, `bid_vol`, `ask_vol`; M1: `time_utc_ns` (inicio de vela) y OHLC bid/ask | cotizaciones, no operaciones; meses faltantes en `INSTRUMENTS.md` |

## 4. Límites de este inventario

- Se escanearon **todos** los parquet de los 30 datasets (ticks, barras M1 y artefactos). Los de artefactos (coordenadas de NQ, eventos, `edge-factory`) se agrupan por esquema en `DATASETS.md`; un archivo de `edgelab-nq-selection-checkpoints` (`NQ_09-25.parquet` de un checkpoint) no se pudo bajar.
- Los README y manifiestos de algunos datasets no se pudieron bajar (límite de tasa 429 o 403 de Kaggle): sus extractos faltan en `DATASETS.md`.
- Las sesiones se asignan con la convención de fecha de trading CME; los datos spot usan la misma convención para poder compararse con los futuros.

## 5. Cómo actualizar

Cada vez que se suba un dataset nuevo: `python tools/data_inventory.py --out /data/catalog` y `python tools/data_catalog_build.py --scan-root /data/catalog --out docs/data_catalog`, revisar las diferencias en `git diff docs/data_catalog` y commitear.
