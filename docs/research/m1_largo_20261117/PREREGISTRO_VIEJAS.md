# EdgeReplica en NQ 2006–2022, el corto de las 04:15 del oro en GC 2008–2022, y re-medición de auditoría (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — commiteado antes de correr. Pedido de Nico: «revisá otros errores de ese estilo … y si se podría medir algo nuevo
con la estrategia de las 4:15 del oro y el EdgeReplica (que supuestamente había decaído)». North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF4. Herramienta: `tools/m1_largo.py` (funciones `viejas_*`).

Antecedentes:
- EdgeReplica (`edgereplica_usatech/RESULTADO.md`): 60 reglas horarias elegidas con datos recientes del NQ, de rango no documentado. Sobre el
  CFD 2023–2026, +4,08 pts/op, «creciendo» de 2023 (negativo) a 2026. Medido en puntos, que no son comparables entre años. Post-publicación
  negativa y no concluyente.
- Oro 04:15 (`barrido_horario_20261004/RESULTADO_ETAPA_P1_H1H2.md`): en spot 2022-07 → 2025-07 el corto sin condición tiene un sesgo bruto de
  ≈ +1,8 ticks (z 2,82), negativo neto por costo. La celda con condición no replica.
- MGC EMA 200/500/2000: barras de 25 operaciones, no se reconstruyen desde M1 → no se mide (medirla con barras de tiempo sería otra regla).

Potencia previa: plan de `holdout_ventanas.plan_potencia` (efectos y desvíos declarados abajo; sin operaciones de desarrollo en futuros):
- EdgeReplica: ≈ 9.000 operaciones por año en el CFD → ≈ 150.000 en 2006–2022. Potencia > 0,99 para la mitad del efecto 2023–2026 (≈ 0,01
  ATR por operación con sd 0,1).
- Oro 04:15: ≈ 250 sesiones por año × 14 años ≈ 3.500 operaciones; efecto 1,8 ticks, sd ≈ 18 ticks → potencia ≈ 0,99 a efecto entero y
  ≈ 0,74 a la mitad.

## 1. EdgeReplica en NQ futuros 2006-01 → 2022-12 (antes del período de selección)
- **Implementación:** las 60 reglas de `rules_v1.json` sin cambios, con el motor de `tools/edgereplica_usatech.py` (`run`). Entrada y salida
  al precio de apertura de la vela M1 de futuros, porque no hay bid/ask, y la fricción canónica de NQ (1,5455 pts) por operación.
- **Unidad:** puntos / ATR20 diario (comparable entre años).
- **Prueba:** media por operación en BRUTO y en NETO, en 2006–2022.
  - **A_FAVOR** si IC90 inferior > 0 (bruto) y ≥ 60 % de años positivos;
  - **EN_CONTRA** si el bruto ≤ 0 con potencia;
  - si no, NO_CONCLUYENTE.
- **Descriptivo:** el neto por año y 2023–2025 en futuros, para comparar con el CFD.
- **Pregunta que responde:** si las reglas tenían algo antes de que las eligieran, o si es selección.

## 2. Oro: corto a las 04:15 CT, 15 minutos, en GC futuros 2008-01 → 2022-06 (antes de la muestra spot)
- **H2** (principal; el efecto de hora que quedó de la etapa C): vender al cierre de la vela de las 04:15 CT, salir 15 minutos después.
- **H1** (secundaria): sólo si los 15 minutos previos subieron.
- **Unidades:** ticks de GC y ticks / ATR20 diario; fricción canónica de GC (0,605 pts).
- **Prueba de H2 en BRUTO:**
  - **SESGO_CONFIRMADO** si IC90 inferior > 0 y ≥ 60 % de años positivos;
  - **SIN_SESGO** si bruto ≤ 0 con potencia;
  - si no, NO_CONCLUYENTE.
- El neto se reporta: la pregunta económica es si el sesgo alguna vez supera al costo.

## 3. Re-medición de auditoría (descriptivo, datos ya vistos)
- **Módulos de FundedSync con stop, en R** (neto / riesgo) además de ATR, por índice y período. Se verifica, para cada módulo, si `riesgo`
  es el stop inicial o el activo al salir, como pasó con T: un R sobre el stop activo no vale.
- **Régimen análogo de T rehecho en R:** el original se hizo en ATR.

## 4. Contador y justificación
- **Contador:** 2 pruebas (EdgeReplica y H2 del oro), familia `M1LARGO_EXTERNAS_20261117`.
- **Justificación económica:**
  - EdgeReplica: patrones de flujo por hora y día (rebalanceos, aperturas, publicaciones) que, si son mecanismo, existían antes.
  - Oro 04:15: presión vendedora en el cierre de la sesión asiática y la apertura europea.
- **Cómo podría refutarse:** bruto ≤ 0 con potencia en los años no usados.
