# Pendiente — aVolClusterPOISim en NQ 12-26, 5 tick: expectativa visual positiva sin fricción (Nico, 2026-10-06)

**Estado: OBSERVACIÓN VISUAL, no evidencia.** Registrada para no perderla; requiere prueba formal antes de cualquier
lectura.

## Configuración (chart de Nico)
- NQ 12-26, **5 tick**. aVolClusterPOISim con percentil **98**, invalidación None, MaxAge 500, resto por defecto.
- Simulador: SL en el **50 % de la zona**; TP **5R**; **BE a 2R** (+0 ticks); cierre al fin de sesión; sin comisión ni
  slippage; trades simultáneos permitidos.
- 14 sesiones cargadas.

## Lo que muestra el dashboard
- 2.140 trades (1.065 long / 1.075 short). 337 ganadores / 1.351 perdedores / 452 BE. Win rate 15,7 %.
- **Expectativa +0,16 R/trade**, total +334 R, PF 1,25, Max DD 81 R, racha perdedora de 35.
- Long +201 R / short +133 R. Neto de 1 contrato: +6.495 USD **sin fricción**.

## Por qué no se puede leer todavía
1. **Fricción:** en barras de 5 ticks y con el SL en la mitad de la zona, el riesgo por trade es de pocos ticks. Con
   1–2 ticks de slippage más la comisión, una expectativa de +0,16 R puede volverse negativa. Hace falta la
   distribución del riesgo en ticks.
2. **SL+TP en la misma barra = SL** es conservador, pero el BE se evalúa al cierre de la barra: el orden dentro de la
   barra importa y sólo se resuelve con ticks.
3. **Sin nulo:** falta saber si entradas al azar con la **misma geometría** (pseudo-zonas, como en AVCL-EXIT) dan lo
   mismo. Con SL chico, TP 5R y BE, una estructura de pagos asimétrica puede dar "positivo" en un tramo corto por la
   asimetría universal de las excursiones (`EXPLO_ASIMETRIA_EXCURSION_20261006.md`).
4. 14 sesiones, un instrumento, parámetros elegidos mirando el chart: selección.

## Prueba formal propuesta (cuando se retome; requiere manifiesto + STOP)
- Simulación **tick a tick** del mismo esquema (SL 50 % zona, TP k·R, BE a b·R) sobre las zonas AVCL de la celda
  pertinente (p98 en 5t, o p95 en 50t con paridad).
- Nulo de pseudo-zonas con la misma geometría y franja.
- Fricción por instrumento.
- Descubrimiento y confirmación por contratos.
- Grilla chica (TP ∈ {3, 5, 10, 30} R × BE ∈ {off, 1, 2} R) con max-T.
