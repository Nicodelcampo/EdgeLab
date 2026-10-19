# R2 — Recorrido bruto disponible vs fricción real (manifiesto)

Estado: VIGENTE (congelado antes de medir)
Fecha: 2026-10-14
Familia / módulo: research · roadmap R2 (`docs/PRODUCT.md`)
North Star: `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`
Procedencia: release `liquid_tick_v1` v4, manifiesto `db9c42cdb714634b131fc8ff886cda67771bea6070d27c0e56e2d2fd6eb14ce5`; sólo `trade_date < 20261001`; `purpose=provisional_research`.

## Pregunta
¿Cuántos ticks de recorrido existen, por activo, horizonte y hora, frente a la fricción de un viaje redondo? Es un **techo geométrico target-free**: si ni el recorrido máximo posible paga la fricción con frecuencia suficiente, ninguna regla de entrada puede pagarla; si la paga, recién ahí tiene sentido pre-registrar una campaña.

## Justificación económica
Un edge neto exige que la ganancia bruta alcanzable supere spread + comisión + slippage. El recorrido (máximo − mínimo en la ventana) es la cota superior de cualquier ganancia direccional en esa ventana, sin conocer la dirección ni la señal.

## Estimando (no direccional y direccional-agnóstico)
- Ventanas de H ∈ {1, 5, 15, 30, 60} minutos que comienzan en cada minuto de la sesión regular (08:30–15:00 CT, `outside_regular == False`), sin cruzar de sesión.
- `R_H` = máx(precio) − mín(precio) en la ventana, en ticks (precio de trade, `price_ticks`).
- `D_H` = |precio final − precio inicial| en ticks (desplazamiento neto; canal direccional sin signo).
- Se publican cuantiles p10/p25/p50/p75/p90/p99 de `R_H` y `D_H`, **por activo, horizonte y hora de inicio CT**, y la fracción de ventanas con `R_H ≥ F` y `D_H ≥ F`, con `F` = fricción de viaje redondo del activo (spread medio RTH medido + comisión + 2 ticks de slippage declarado), en sus dos extremos (comisión mínima y máxima de `REFERENCIA_COSTOS_PROPS_BROKERS_20261014.md`).
- Se publica el número de sesiones y de ventanas. Las ventanas se superponen: **el N efectivo es el de sesiones**, no el de ventanas.

## Qué NO se hace
Sin P&L, sin señales, sin dirección, sin entrada/salida, sin tocar el holdout. El resultado es descriptivo y PROVISIONAL.

## Cómo podría refutarse / qué lo invalida
- Si la fracción de ventanas con `R_H ≥ F` es despreciable en todo horizonte ≤ 60 min para un activo, ese activo queda cerrado para scalping a mercado hasta nueva evidencia.
- Un `R_H` grande puede deberse a unos pocos días extremos: se publica también la fracción de **sesiones** donde al menos una ventana supera `F`, y la mediana por sesión.
- Las cuantiles de ES no se transportan a otros activos ni viceversa.

## Condición de cierre
Se publican las tablas completas (todos los activos, horizontes y horas) en `docs/research/r2_recorrido_vs_friccion_20261014/`. No se selecciona ninguna celda por su valor.
