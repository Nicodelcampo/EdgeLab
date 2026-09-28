# Pre-registro PROPUESTO: campaña multi-instrumento sobre ticks (5 familias × 5 instrumentos)

**Estado:** PROPUESTO. Espera el OK de Nico (regla STOP). **No se corrió nada.** Retoma `PROPUESTA_ARCHIVADA_CAMPANA_MULTIINSTRUMENTO_20260923.md` con lo aprendido hoy.
**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## 1. Por qué ahora

- El L2 quedó descartado como predictor direccional (`L2_FASE2_RESULTADOS_20260923.md`), pero dejó **costos medidos por instrumento** y horizontes alcanzables: ≥ 5 min en GC y más largos en 6E (`L2_FASE0_RESULTADOS_20260923.md` §4 y §7).
- Los ticks de research-v2 tienen **11 meses pre-holdout** (ago-2025 a jun-2026). Es la mayor potencia disponible.
- El Brain ya puede **contar y limitar** las pruebas: `record_campaign` y `record_trial` en el PR #56, `e64f311`.

## 2. Hipótesis y familias (cada una con justificación económica y refutación)

Barras de 5 min armadas desde ticks, contrato principal del día (el de mayor volumen), sesiones CME. Posición única de 1 contrato, sin pirámide. Cada variante es **una** regla completa: entrada, salida y tamaño. Las variantes se fijan **ahora**.

| Familia | Regla | Variantes (4) | Justificación económica | Se refuta si |
|---|---|---|---|---|
| F1 Momentum | signo del retorno de las últimas L barras; mantener H barras | L ∈ {6, 12} × H ∈ {6, 12} | reacción lenta a la información y flujos institucionales fraccionados | la expectativa neta en validación tiene IC inferior ≤ 0 |
| F2 Reversión a VWAP | contra el precio si \|close − VWAP de sesión\| > k·ATR(14); salir al tocar el VWAP o a las H barras | k ∈ {1,5; 2,5} × H ∈ {6, 12} | provisión de liquidez: los desvíos por presión transitoria revierten | ídem |
| F3 Ruptura del rango de apertura | rango de los primeros R min desde la apertura de referencia; entrar en la ruptura; salir a H o al cierre | R ∈ {15, 30} × salida ∈ {12 barras, fin de RTH} | la apertura concentra información y la ruptura señala desequilibrio | ídem |
| F4 Gap nocturno | contra el gap si \|gap\| > g·ATR diario; salir al cerrar el gap o a H | g ∈ {0,3; 0,6} × salida ∈ {12 barras, fin de RTH} | sobre-reacción nocturna con poca liquidez | ídem |
| F5 Ruptura por volatilidad | a favor de la barra si su rango > m·ATR(20); mantener H | m ∈ {2, 3} × H ∈ {6, 12} | una expansión de volatilidad marca el inicio de un movimiento informado | ídem |

- **Apertura de referencia:** 9:30 ET para ES, NQ e YM; 8:20 ET para GC; 8:00 ET para 6E. Fijada ahora.
- **Instrumentos:** GC, ES, NQ, YM y 6E (research-v2, pre-holdout).

## 3. Tamaño de la búsqueda (N efectivo)

5 familias × 4 variantes × 5 instrumentos = **100 pruebas**. Se registran en el Brain como **5 campañas**, una por familia, cada una con `max_trials = 20`. Una prueba 101 no puede existir: el store la rechaza.

## 4. Partición

- **Descubrimiento:** ago-2025 a feb-2026.
- **Validación:** mar a jun-2026, **por instrumento**.
- El holdout (desde el 01/07/2026) no se toca; lo hace cumplir `holdout_guard`.
- **Sin optimización:** las 4 variantes son todo el espacio. No hay ajuste de parámetros después de ver resultados.

## 5. Costos (no se transportan entre instrumentos)

- **Round-trip** = spread mediano del instrumento en el momento de cada trade, por bloque horario, medido en sus propios ticks, más la comisión supuesta de ese instrumento en ticks, más 0 de slippage adicional en el caso base.
- **Estrés:** costo × 1,5.
- **Referencias medidas:** ES ~1 tick, NQ ~3, YM ~2, GC ~4 y 6E ~1,2 (este último del L2).

## 6. Regla de supervivencia (fijada ahora)

Una variante **sobrevive** si cumple las cuatro condiciones:
1. **Descubrimiento:** la mejor variante de su familia en ese instrumento supera el MCPT sobre el máximo de la grilla de 4 variantes (p < 0,05).
2. **Validación:** expectativa neta por sesión con `PrimaryCI` (bootstrap estacionario agrupado por sesión) con **límite inferior > 0**, con costo base **y** con costo × 1,5.
3. **DSR** con N = 100 pruebas (el que registra el Brain) > 0,95.
4. **Réplica:** la **misma** variante sobrevive 1 a 3 en **al menos 2 instrumentos**.

Lo que sobrevive queda como `LESSON_CANDIDATE` PROPOSED/LOW. **No es un edge:** el siguiente paso es un pre-registro de ejecución (costos L2 reales, latencia medida) y, al final, **una** apertura del holdout.

## 7. Qué se publica

- El landscape completo: 100 pruebas con su expectativa, IC, MCPT y DSR, incluidas las muertas.
- El MDE por instrumento.
- Todo se registra en el Brain: campañas, pruebas y contraejemplos.

## 8. Riesgos y datos faltantes

- **Riesgo 1:** las comisiones son supuestas. Se mitiga con el estrés × 1,5, y el resultado se reporta en función de la comisión.
- **Riesgo 2:** 7 meses de descubrimiento y 4 de validación. Las familias de horizonte largo (F3, F4) dan pocas operaciones por instrumento. Se publica el MDE y un nulo no se confunde con ausencia de efecto.
- **Riesgo 3:** los rolls. El día de roll se excluye.
- **Riesgo 4:** el régimen de 2025-26 puede no repetirse. Es la razón de exigir réplica y, al final, el holdout.
- **Prerrequisito de ingeniería:** las campañas del Brain viven en la rama del PR #56 y las herramientas de datos en la del visor (#48). Hay que correr desde un árbol que tenga las dos (integrar la cadena en `foundation`), o registrar en el Brain en un segundo paso con los hashes de los resultados.

## 9. Cómo podría refutarse la campaña entera

Ninguna variante sobrevive en 2 instrumentos. Las 5 familias quedan cerradas **para estos 5 instrumentos, ago-2025 a jun-2026, costos del feed NT8 y barras de 5 min**, con MDE publicado. Eso también reduce la distancia al referente: descarta la clase más barata de hipótesis antes de invertir en las más caras.

---

## Aprobación y enmienda A1 (2026-09-23, ANTES de ejecutar; ningún resultado visto)

**Aprobado por Nico** ("apruebo, integrá las ramas y corré la campaña"). Se corre desde `integ/viewer-brain-20260923` (visor #48 + Brain #56, suite 1.744 en verde).

**A1.1. Intervalo de validación.** `PrimaryCI` (bootstrap-t estacionario, `studentized_stationary_interval`) exige ≥ 160 sesiones (`MIN_STUDENTIZED_SESSIONS`), y la validación de mar–jun tiene ~85 por instrumento, así que el método autorizado se niega. El criterio 2 usa el **mismo estimand y el mismo bootstrap estacionario por sesión** (`resample_stationary_session_clusters`, 10.000 réplicas, bloque PPW), pero con **intervalo percentil al 95 %** (`percentile_interval`), que el código marca como **diagnóstico, no gate G2**. Consecuencia: **sobrevivir esta campaña NO es pasar el G2.** Un sobreviviente queda como `LESSON_CANDIDATE` y el G2 formal se hace con ≥ 160 sesiones.

**A1.2. Fin de RTH** (salidas "fin de RTH" y rango diario del gap): ES/NQ/YM 16:00 ET, GC 13:30 ET, 6E 15:00 ET. **ATR diario** = media de los últimos 14 rangos RTH.

**A1.3. Mecánica común no escrita antes:**
- La señal se evalúa al cierre de la barra i y se entra en la apertura de i+1. F4 es la excepción: el gap se conoce en la apertura RTH y se entra en esa apertura.
- Todas las posiciones se cierran al terminar la fecha de trading CME (sin overnight). No se entra en la última barra.
- F1, F2 y F5 se reevalúan en cada barra estando flat. F3 y F4 hacen como máximo una operación por día.
- F2 sale cuando una barra cierra del otro lado del VWAP. F4 sale al tocar el cierre RTH previo, a ese precio.

**A1.4. Fecha de trading CME** = fecha de (ts_utc + 2 h). Se excluyen los días de roll: el día en que cambia el contrato de mayor volumen.

**A1.5. Comisión supuesta:** USD 4,50 round-trip por contrato. En ticks: ES 0,36, NQ 0,9, YM 0,9, GC 0,45, 6E 0,72. **Spread:** mediana de (ask − bid) en los trades del **período de descubrimiento**, por instrumento y hora ET.

**A1.6. Nulo del MCPT:** entradas aleatorias dentro de la misma sesión, con la misma cantidad de trades, duración y dirección que cada variante, y salida al cierre. Estadístico = máximo, sobre las 4 variantes, de la expectativa neta por trade en descubrimiento. 1.000 permutaciones, semilla 20260923.
