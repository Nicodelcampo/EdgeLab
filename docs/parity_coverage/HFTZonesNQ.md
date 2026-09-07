# Paridad — motor de zonas HFT (`hftzones_nq` ↔ `HFTClusterZonesNQ.cs`)

> **Resultado: EXACT, 7.494 / 7.494 zonas, 20 campos, 0 diferencias.**
> Reproducción: `.venv\Scripts\python tools\paridad_hftzones_nq.py` (sale 0).
> Certificado: `data/nt8_oracles/paridad_hftzones_nq.json`.
> Fecha: 2026-09-07.

---

## 1. Estimand

*Fracción de zonas del oráculo que el espejo reproduce con **los veinte campos
idénticos**, emparejadas por `(start_ms, end_ms, dir)`.*

Se declara porque no es la única medida posible y las otras dicen otra cosa. En
particular **no** se mide "cuántas zonas encuentra cada lado": el oráculo es una
población incompleta por una limitación propia (§4), así que igualar conteos sería
exigirle al espejo que reprodujera una pérdida de datos.

## 2. Qué se comparó

| | |
| :-- | :-- |
| Oráculo | tabla `hft_zones` de `C:\LoggerHFT\data\hft_logger_v4.sqlite` |
| Instrumento | `ES 09-26` |
| Ventana | 2026-06-14 22:00 → 2026-06-17 19:34 UTC (3 sesiones CME) |
| Ticks | `data/nt8/ES_parquet/ES_09-26_ticks.parquet`, 2.563.396 ticks leídos |
| Espejo | `edgelab/bridge/indicators/hftzones_nq.py` con `ACCEPT_DEFAULTS` |
| Campos | 20 por zona → **149.880 comparaciones**, tolerancia 1e-6 |

Campos comparados: `price_lower`, `price_upper`, `valid_steps`, `pasos`, `avg_ms`,
`total_ms`, `vol_rate`, `total_vol`, `height_ticks`, `max_retro`, `cvd_sweep`,
`buy_vol`, `sell_vol`, `delta_slope`, `delta_first`, `delta_second`, `max_tick_vol`,
`no_move_ticks`, `no_move_vol`, `max_level_ticks`.

**Cero diferencias en los 149.880.**

## 3. Chequeo previo de parámetros

La base **no guarda con qué parámetros se corrió** — no hay `run_id` ni tabla de
configuración. Se verificó que las 19.401 filas de los cinco instrumentos cumplen los
umbrales default (`avg_ms ≤ 25`, `total_ms ≤ 500`, `vol_rate ≥ 100`, `total_vol ≥ 50`,
`valid_steps ≥ 6`, `tick_res = 1`): **cero violaciones**.

Es condición **necesaria, no suficiente**: una configuración más estricta también las
cumpliría. Pero una sola violación habría probado que la corrida no usó los defaults, y
entonces la comparación no habría tenido sentido. El validador repite este chequeo y lo
publica en el certificado.

## 4. Dos límites del oráculo, encontrados al medir

**4.1 — El milisegundo no identifica una zona.** 208 de las 7.494 zonas (2,8 %) tienen
`start_ts == end_ts`: nacen y mueren dentro del mismo milisegundo, con hasta 189 ticks
adentro. Emparejar sólo por `(start_ms, end_ms)` cruza una zona bajista con una alcista
del mismo milisegundo y produce **seis diferencias que no existen**. Por eso la clave
lleva `dir`.

Esto fue un falso positivo del comparador, no del motor. Queda documentado porque el
próximo que compare va a tropezar con lo mismo.

**4.2 — La base descarta zonas en silencio.** `hft_zones` tiene
`UNIQUE(instrument, start_ts)` con `INSERT OR IGNORE`, y `start_ts` está en
milisegundos: **la segunda zona que arranca en el mismo milisegundo se pierde**. El
espejo produce 7.530 zonas contra 7.494 del oráculo, y las 36 de diferencia comparten
milisegundo de inicio con una zona ya guardada.

No son falsos positivos del espejo: son zonas que la base no puede representar. Para
poder comparar **conteos** —y no sólo cobertura— el `.cs` tendría que emitir un id
monotónico por zona o un timestamp sub-milisegundo.

## 5. Alcance de este certificado

Vale para lo que se midió y nada más:

- **Un instrumento** (`ES 09-26`), **tres sesiones**, junio 2026, pre-holdout.
- `tick_resolution = 1`. Con resolución mayor el espejo levanta `NotImplementedError`
  a propósito: dos filtros dejan de ser inertes y no están medidos.
- Los umbrales default. El espejo permite barrerlos, pero sólo estos están certificados
  contra oráculo.

**No se pudo certificar sobre NQ**, que es el instrumento de la investigación: las
zonas de `NQ SEP26` en la base son del 2026-08-06 al 09-07, y el parquet de `NQ 09-26`
llega hasta el 2026-07-28. No hay solape. Tampoco hay parquets de `6E` ni de `ZB` para
las otras ventanas del oráculo.

Para certificar sobre NQ hace falta **una de dos cosas**: exportar los ticks de NQ de
agosto-septiembre, o correr el indicador sobre una ventana de NQ anterior al 28 de
julio. La segunda es más barata y no toca el holdout si se elige antes del 1 de julio.

## 6. Por qué esto importa

Con la paridad certificada, la investigación de clusters **no necesita NinjaTrader**:
las zonas se reproducen desde los parquets de ticks, y todo el barrido de umbrales y de
definiciones de cluster ocurre en Python. NT8 queda como oráculo, no como dependencia
del ciclo de trabajo.

---

**Aporte al referente:** desbloquea el frente de investigación al garantizar que lo que
se mida en Python es el mismo objeto que el indicador dibuja, y deja documentados dos
defectos del oráculo que habrían aparecido como divergencias inexistentes.
