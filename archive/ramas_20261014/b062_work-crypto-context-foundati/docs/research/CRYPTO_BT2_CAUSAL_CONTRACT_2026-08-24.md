# Crypto BT2 — contrato causal de ingesta Binance USD-M

**Estado:** infraestructura target-free implementada; outcomes cerrados.  
**Rama de trabajo:** `work/crypto-context-foundation-20260824`.  
**NORTH STAR:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`.

## Decisiones congeladas

1. Fuente gratuita inicial: Binance Data Vision, futuros USD-M.
2. Archivos: `trades` + `bookTicker` del mismo símbolo y día.
3. Join causal: `bookTicker.transaction_time < trade.time`.
4. Un book con timestamp igual al trade no puede clasificarlo.
5. `tick_size` y `quantity_unit_base` son argumentos obligatorios y quedan en el manifest.
6. La unidad candidata `0.001 BTC` sigue **provisional**: no se convierte en default oculto.
7. Trade IDs duplicados, precios fuera de tick y cobertura incompleta fallan cerrado.
8. Los gaps de ID no se tapan: se cuantifican y el estado los declara.
9. No se accede a outcomes ni se selecciona una parametrización por cantidad de zonas.

## Event-space y población

- Espacio: todos los trades presentes en el archivo diario descargado.
- Población técnica: trades con al menos un `bookTicker` estrictamente anterior.
- Exclusión: trades sin book previo; el default aborta. La exclusión sólo puede habilitarse
  explícitamente y queda cuantificada.
- Buckets, zonas y fills son derivados posteriores; este contrato no selecciona ninguno.

## Salidas

`tools/binance_bt2_pilot.py` produce:

- parquet de ticks compatible en memoria con `TickSeries`;
- sidecar con trade ID, book elegido, edad del book y comparación maker/quote;
- manifest con hashes, contrato, gaps, cobertura y procedencia dirty-aware.

Ejemplo:

```bash
python tools/binance_bt2_pilot.py \
  --trades /data/BTCUSDT-trades-2024-03-30.zip \
  --book-ticker /data/BTCUSDT-bookTicker-2024-03-30.zip \
  --symbol BTCUSDT \
  --tick-size 0.1 \
  --quantity-unit-base 0.001 \
  --out-dir /data/btcusdt_bt2_2024-03-30
```

## Bloqueantes antes de outcomes

1. Verificar y congelar metadata histórica de `PRICE_FILTER.tickSize` y `LOT_SIZE`.
2. Explicar los siete gaps del piloto original contra archivos/checksums oficiales.
3. Repetir un segundo día antes de ampliar a 30 días.
4. Preregistrar el orden BTCUSDT → ETHUSDT → SOLUSDT y la sensibilidad de unidad.
5. No interpretar cantidad de zonas como evidencia de edge.

## Justificación económica

Crypto ofrece negociación 24/7, regímenes de liquidez más heterogéneos y otra estructura
de participantes. Eso puede aumentar la información condicional de la absorción, pero sólo
es útil si finalmente sobrevive costos, validación OOS y ejecución real.

## Cómo podría refutarse

El programa se detiene o reformula si el join no es reproducible, la señal depende de una
unidad arbitraria de volumen, los gaps cambian materialmente la reconstrucción, o el efecto
no es estable en los días y activos preregistrados después de costos.
