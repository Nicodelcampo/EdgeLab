# Plan hacia un edge neto — decisión de Claude local tras leer el chat completo de Gemini (2026-10-14)

Estado: PROPUESTA  
Fecha: 2026-10-14

Fuente leída: el chat compartido de Gemini ("Estado y Backlog de EdgeLab", 287 mil caracteres). Jerarquía de CLAUDE.md: expectativa neta → OOS → robustez → ejecutabilidad.

## Qué tomo de Gemini
- Diagnóstico de fricción: un objetivo de 3 ticks en ES no puede sobrevivir a spread + comisión + slippage. La excursión favorable mediana es 3 ticks.
- Idea de ampliar el recorrido objetivo (16–32 ticks ES) y condicionar por régimen causal (`session_auction` v3). Es una hipótesis con mecanismo, no un resultado.
- Retractación correcta de los 4 informes y del parche 05 (P&L simulado con `np.random.binomial`).
- Hallazgo `prefix_check` del parche 07 (barra final truncada) como práctica de causalidad.

## Qué corrijo
1. **El ranking de fricción de Gemini asume spread = 1 tick en todos los activos.** El atlas real (kernel 06, release v4, RTH) dice otra cosa: ES spread medio 1,09 (p50 1); **GC p50 = 3 ticks (media 3,43)**, NQ 3,03, MGC 2,72, MBT 2,69, MNQ 2,11. GC no es el "#2 de eficiencia": su fricción real es mucho mayor. Antes de elegir activo prioritario hay que recalcular el ranking con spread medido y comisiones reales del broker.
2. **Comisión "LucidFlex 0,28 t"** es de una cuenta fondeada puntual, no la fricción real del capital propio. Falta el dato real de Nico (P&L OK + comisiones ES vs MES).
3. **Win rate de equilibrio 31–35 %** es aritmética de payoff, no evidencia. No hay ninguna medición de acierto real para ninguna estrategia del repo.
4. **"+14,5 ticks"** del parche 07 sale de `mirror_check` sobre precios sintéticos. No es un resultado.
5. **Grinold (IR ≈ IC × √breadth)** exige apuestas independientes. Apilar 4 motores × 14 activos multiplica el número efectivo de hipótesis; hay que pagarlo con Holm/PBO, no tratarlo como gratis. Sharpe > 2 es un deseo, no una cifra.
6. **ARB 6E "Sharpe > 0,7 OOS 18 meses"**: heredado de un artefacto legacy en spot no verificado, que el propio Gemini archivó después. No cuenta.

## Estado empírico real hoy (sin P&L)
- Edges promovidos: **0**. O5 (compresión de rango tras racimo) es real en ES/MES/MNQ, no en NQ; no es dirección ni P&L. O1 desaparece con el nulo espejo. Presión/progreso en GC: décimas de tick. Auditoría de contenido v4: PASS técnico, no aprobación de research.

## Orden de trabajo (con puertas)
**Fase A — sólo target-free, puede correr ya (sin OK extra):**
- A1. Leer y registrar los 4 resultados nuevos: atlas 14 activos, censo de regímenes (3.838 sesiones), subasta × AVZP2 (ES, MNQ), barras escaladas (NQ, GC, MGC, 6E).
- A2. Recalcular el ranking de fricción por activo con spread medido (atlas) y dejar la comisión como parámetro a completar por Nico.
- A3. Calcular, con el censo, el recorrido bruto disponible (rango intradía, IB, extensión) por régimen y activo: *cuántos ticks hay en juego* antes de cualquier regla de entrada. Es la prueba de si un target de 16–24 ticks siquiera existe con frecuencia suficiente. Target-free.
- A4. Reunir el MDE de cada estimand: no seguir con celdas sin potencia (NQ 25t).

**Fase B — antes de tocar retornos (STOP de CLAUDE.md):** manifiesto de campaña, N efectivo de hipótesis, riesgos, comisiones reales. Debe enumerar por escrito el espacio de eventos (creación, aproximación, toque, rotura IB, rotación VA, estado continuo) y por qué se congela uno; incluir "cómo podría refutarse". Todas las familias (IB breakout, rotación VA, ARB, GEX) se registran **separadas**, con presupuesto de multiplicidad propio y sin transportar costos entre instrumentos. Requiere OK de Nico.

**Fase C — recién entonces:** señales puras bajo `CONTRATO_LLM.md`, `full_audit`, MCPT/PBO/SPA, walk-forward; holdout (trade_date ≥ 2026-10-01) abre una sola vez por candidato.

## Integración y solidez del repo
- Un solo escritor por árbol: Gemini entrega parches en `patches_for_review/`; nada se aplica sin revisión. Parche 06: anclar la IB a 08:30 CT por reloj de Chicago y tick/comisión por instrumento.
- Cada kernel de Kaggle imprime recibo agregado y se archiva en `docs/` con su SHA; Kaggle COMPLETE no es resultado válido hasta leer el recibo.
- Registro MEDIDO/NO MEDIDO en el mismo commit que cada resultado.
- Limpieza de Kaggle: no borrar los datasets L2 (`edgelab-nq-nt8-2026q3-l2ctx`, `edgelab-l2-gc-bookmap-audit-20260921`); la lista de candidatos de borrado no revisó dependencias.
- Pendientes de Nico (no son míos): comisiones reales ES/MES, OK de P&L, licencia / política de liquidez / calendario oficial, exports faltantes.
