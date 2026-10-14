# Manifiesto congelado — EMA 200/500/2000 sobre 25T con retroceso y SL/TP/BE

**Estado:** IMPLEMENTADO, AÚN NO MEDIDO EN MGC.  
**Rama:** `research/ema3-25t-pullback-grid-20261002`.  
**Autorización:** pedido explícito de Nico del 2026-10-02 para iniciar, probar entrada tras retroceso e incluir grilla SL/TP/BE.

## Hipótesis y alcance

Se replica causalmente el indicador `EdgeLabTripleEmaCross`: cruce EMA200/EMA500 confirmado en barra cerrada, ambas del mismo lado de EMA2000, entrada posterior. No es TEMA. La unidad es una barra de **25 prints/trades**, no 25 contratos de volumen. No se cruzan contrato ni `trade_date`; la cola incompleta no genera señal.

Dos familias, separadas:

1. `CROSS_NEXT_OPEN`: primer bid/ask válido posterior al cierre de señal.
2. `CROSS_THEN_PULLBACK`: después del cruce espera que el last retroceda 25 o 50 ticks respecto del cierre de señal, hasta 20 barras 25T; luego entra agresivamente en la cotización siguiente. Se denomina `market-after-touch`: no presume fill pasivo.

La dirección NORMAL es primaria. INVERTED es placebo/falsación, no una forma post hoc de rescatar pérdidas.

## Grilla congelada

- Pullback: `0`, `25`, `50` ticks; timeout `20` barras.
- SL: `90`, `200`, `300` ticks.
- TP: `150`, `300`, `450` ticks.
- BE: apagado o trigger de `90` ticks; BE siempre es menor al target.
- Dirección: NORMAL e INVERTED.
- Slippage adverso: 1 tick por lado, además del spread observado.
- Comisión: parámetro explícito en ticks round-trip; default técnico 2,4, a confirmar para MGC.
- Total: 108 celdas. Incluye la paridad visual pedida: NORMAL, pullback 0, SL200, TP300, BE off.

Esta campaña agrega 108 trials al presupuesto; no se empieza el contador en cero. No se promoverá una celda por ranking bruto.

## Partición y firewall

Primera ejecución: sólo desarrollo hasta `2026-03-31`. Abril–septiembre no se abre automáticamente. Octubre+ permanece sellado. El runner descarta filas posteriores al corte antes de construir barras y reporta cuántas no cargó. `UNKNOWN_EXIT`, schema ambiguo, reloj invertido, precios fuera de tick o quotes inválidas producen abstención/no inferencia.

## Ejecución

- Long compra ask; short vende bid.
- Stop dispara por last y sale contra bid/ask.
- Target exige cotización ejecutable atravesando el nivel.
- BE se activa causalmente; empate intratick usa orden conservador stop-first.
- Una posición por celda; no hay trades superpuestos.
- EMAs con recurrencia `adjust=False`, burn-in mínimo 6000 barras.

## Datos MGC

La creación del dataset privado fue aceptada según el checkpoint externo (7 Parquet, 90.076.982 filas), pero las consultas inmediatamente posteriores devolvieron 403. Desde esta sesión no hubo acceso autenticado de Kaggle para certificar que ya terminó el procesamiento; no se repite la subida. El runner acepta aliases o `--column-map`, calcula SHA-256/filas por archivo y falla cerrado ante drift.

## Criterio de revisión

Antes de leer P&L: validar inventario, schema, timezone, tick size 0,10, monotonicidad, contratos, `trade_date`, quotes y paridad de una muestra de barras/señales contra NT8. Los outputs quedan `DESCRIPTIVE_ONLY_NO_PROMOTION` hasta añadir inferencia por sesión, corrección por multiplicidad, sensibilidad de costos y auditoría independiente.

## Cómo puede refutarse

La hipótesis queda sin apoyo si NORMAL no supera costos con estabilidad por contrato/sesión, si el efecto depende de una isla de SL/TP/BE, si INVERTED rinde igual/mejor, si el retroceso sólo mejora por selección/muestras menores, o si falla la paridad 25T/NT8.

## Justificación económica

El retroceso intenta reducir precio de entrada y excursión adversa sin anticipar el futuro; la grilla mide si esa mejora compensa señales perdidas, spread, slippage y comisión. La prioridad es expectativa neta operable, no porcentaje visual de aciertos.

**Aporte al referente:** convierte la observación visual del indicador en una campaña causal, costada y falsable, sin abrir replicación ni holdout.
