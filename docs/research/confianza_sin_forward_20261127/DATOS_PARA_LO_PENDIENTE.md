# Datos para lo que quedó pendiente de CONFIANZA-SIN-FORWARD (relevamiento, 2026-11-27)

Estado: REFERENCIA — búsqueda y verificación de acceso, sin descargar series completas ni medir.

| Pendiente | Fuente encontrada | Historia | Acceso desde el entorno | Nota |
|---|---|---|---|---|
| **T, R y Z en índices extranjeros (M1)** | Datafeed público de Dukascopy (`datafeed.dukascopy.com/datafeed/{INSTRUMENTO}/{año}/{mes-1}/{día}/BID_candles_min_1.bi5`): DEU.IDX, JPN.IDX, GBR.IDX, EUS.IDX, FRA.IDX, AUS.IDX, HKG.IDX, etc. | ≈ 2010–2012 en adelante, según el índice | **Sí** (200 en JPNIDXJPY; un pedido a DEUIDXEUR se cortó, hay que reintentar) | Es la misma fuente que los M1DK de la máquina de Nico (`leer_m1` con `EN_UTC`). Formato bi5 (LZMA): un archivo por día |
| Ídem, alternativa | HistData.com, M1 ASCII de índices CFD (GRXEUR, JPXJPY, UKXGBP, FRXEUR, ETXEUR, AUXAUD, SPX, NSX, UDX) | ≈ 2010 en adelante | Sí (página 200; la descarga pide un token del formulario) | Sirve para cruzar contra Dukascopy |
| **Cripto 2019-09 → 2020-12** | `data.binance.vision` (klines, funding, premiumIndex de USDT-M) | Desde 2019-09, cuando empezaron los perpetuos | **Sí** (200) | Es la fuente primaria que ya usan `cripto_pit*.py`. Los datasets de Kaggle (`mishvnia/binance-1m…` 2021–2026, `naviebayes/b-um-*-2019-12`) son parciales y no agregan nada |
| Diarios de índices 1990–2026 | Yahoo v8 (ya usado en `confianza_sin_forward.py`) | 1990+ | Sí | Ya incorporado |
| Kaggle «Global Markets OHLCV intraday» (`benjaminpo/finance-dataset-intraday`) | Instantáneas de Yahoo acumuladas | Sólo desde 2026 (ventana móvil de Yahoo) | Sí | **No sirve** para historia |
| Kaggle DAX y GER30 de 1 minuto (`sentinelx/…`, `orkadd/…`) | M1 del DAX | ≈ 2 MB: semanas o pocos meses | Sí | **No sirve** |

**Siguiente paso, si Nico lo aprueba:**
1. Bajar el M1 de Dukascopy de 4 a 6 índices desde 2012.
2. Pre-registrar T, R y Z (reglas congeladas, costos estimados y declarados) en esos índices, con la misma lectura que H1.
3. Cripto 2019-09 → 2020-12 con `cripto_pit_v3.py` sin cambios: 15 meses que nadie miró.

## Hecho (2026-11-27)
- **T, R y Z en índices extranjeros:** `trz_extranjeros_20261127/RESULTADO.md`.
  - Dukascopy bloqueó la descarga desde el entorno; se usó HistData.
  - T y R: EN_CONTRA (t −4,57).
  - Z no calibra con CFD.
- **Cripto 2019-10 → 2020-12:** `cripto_v3_2019_20261127/RESULTADO.md`, t 1,64, NO_CONCLUYENTE.
