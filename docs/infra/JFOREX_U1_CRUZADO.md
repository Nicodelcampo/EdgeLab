# Estrategia JForex U1-CRUZADO (señal causal sobre USATECH)

Estado: VIGENTE (2026-11-02). Pedido de Nico: «Escribí la estrategia en JForex, yo la compilo y corro, luego comparamos la paridad».
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Qué es
`nt8_tools/jforex/EdgeLabU1Cruzado.java` porta 1:1 `u1_cruzado.senales` con `areas_expansion.disparos_causales`:
- la regla congelada de U1-CRUZADO (N ≥ 3 zonas LUX-IMB en 40 pts, regreso al 25 % de A, A/H ≥ 8);
- **la versión causal**, la que se puede operar en vivo.

**No opera:** sólo calcula la señal. La orden va en NQ, en NT8.

## Cómo correrla
1. En JForex: Strategies → New → pegar el archivo → Compile. Correrla sobre `USATECH.IDX/USD`.
2. Parámetros:
   - calentamiento: por defecto 48 h de ticks históricos, que alcanza porque zonas y áreas viven 500 min;
   - carpeta de salida: vacío = la carpeta de archivos de JForex.
3. Salida:
   - `ticks_USATECHIDXUSD_YYYYMMDD.csv`: todos los ticks usados, incluido el calentamiento;
   - `senales_U1_USATECHIDXUSD.csv`: `t_cierre_s, lado, lo, hi, H, E, A, D, c, t_area_s, fase`.
4. Cada señal se imprime en la consola. `lado = 1` significa que el precio vuelve desde arriba del área: venta hacia el borde lejano.
   `lado = -1` es compra.

## Ejecución en NQ (NT8)
- **Base:** cierre NQ − cierre USATECH en el minuto de la señal (`t_cierre_s`).
- **Entrada:** primer tick de la vela NQ siguiente.
- **Objetivo T3:** borde lejano + base, redondeado al tick.
- **Stop:** E + base, un tick más afuera, con tope de 3 × la distancia al objetivo.
- **Sin vela NQ en ese minuto:** no se opera.

## Paridad
**Medida acá (núcleo Java compilado con javac contra Python, mismos ticks):**

| Datos | A/H ≥ 4 | A/H ≥ 8 |
|---|---|---|
| Muestra 1 (141 mil ticks) | 47/47 | 15/15 |
| Muestra 2 (343 mil ticks) | 22/22 | 8/8 |

- La diferencia máxima en E y A es de 4e-12.
- Test: `tests/research/test_paridad_jforex_u1.py`.
- Las muestras son sintéticas: así se prueba la lógica, no el feed.

**Con la corrida real de Nico:**

```
python tools/paridad_jforex_u1.py comparar --ticks "<carpeta>/ticks_USATECHIDXUSD_*.csv" --senales <carpeta>/senales_U1_USATECHIDXUSD.csv --desde-s <fin del calentamiento + 1000 min>
```

- Compara las señales de JForex con las de Python sobre **los mismos ticks** que logueó JForex.
- Una diferencia ahí es de lógica o de orden de ticks. No es del feed: el feed se compara aparte, contra el parquet de Dukascopy de
  Kaggle.

## Riesgos conocidos
- **Empalme entre calentamiento y vivo:** se descarta un tick vivo idéntico al último del historial. Si JForex entrega ticks
  repetidos con la misma marca, el log lo muestra.
- **Cierre de vela:** se cierra en `onBar` M1 o con el primer tick del minuto siguiente. Un tick tardío del minuto anterior se ignora,
  igual que en el armado de Python, que exige orden.

## Primera corrida de Nico (tester de JForex, 2026-11-02)
Archivo: `jforex_u1_paridad/senales_U1_USATECHIDXUSD_tester_20261102.csv`. Son 8 señales, entre el 2026-10-26 y el 2026-10-29.
Es holdout, pero se usa sólo para paridad, que es target-free.
- **7 de 7 coinciden al minuto y con el mismo lado** con las operaciones de U1-CRUZADO causal en Python sobre el USATECH sellado de
  Kaggle (`RESULTADO_HOLDOUT_CAUSAL_U1_CRUZADO.json`): 10-26 ×3, 10-28 ×4. Esa es la paridad sobre el feed real: tick de JForex
  contra parquet de Dukascopy.
- **Señal extra de JForex el 10-29 14:01.** Python no tiene ninguna operación el 10-29 ni el 10-30. Falta ver si Python tuvo la señal
  y no operó por falta de vela NQ, o si no la tuvo.
- **Lo que no se pudo comparar:** los niveles exactos (lo, hi, E, A). El resultado de Python guarda las operaciones, no las señales.
  Con los archivos de ticks de esa corrida, `tools/paridad_jforex_u1.py comparar` cierra la comparación completa.

## Ejecución real y rango (03/11/2026)

La estrategia ahora **opera** (`operar = true`) con la regla del papel: E1A/T3/S3 con tope de 3×.
- **Entrada:** orden a mercado al cierre de la vela de la señal; llena con el spread y el slippage reales de JForex.
- **SL y TP:** se calculan con el precio de llenado real y quedan en el servidor.
- **Límites:** una posición a la vez; nunca opera señales del calentamiento.
- **Rango:** `Desde` y `Hasta`, en UTC (`yyyy-MM-dd` o `yyyy-MM-dd HH:mm`). Las señales fuera del rango se registran marcadas y no se operan.
- **Cierre forzado:** opcional, a una hora de Nueva York, sin entradas en los últimos N minutos.
- **Registro:** cada operación cerrada va a `operaciones_U1_<instrumento>.csv`, con su R (resultado / riesgo inicial).
El núcleo de la señal no cambió: la paridad con Python (`tests/research/test_paridad_jforex_u1.py`) sigue pasando.
- **Tamaño (corregido el 03/11):** en USATECH, `cantidad` va en millones y 1 unidad = 1 USD por punto. `0.000002` equivale a 1 MNQ y
  `0.00002` a 1 NQ. El valor anterior, `0.001`, eran 1.000 USD por punto: en la primera corrida de Nico hizo llenados parciales por
  margen, un margin cut y dejó la cuenta en cero.

