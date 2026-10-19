# Paquete STOP — elección de la próxima campaña económica (2026-09-22)

**Estado:** propuesta para decisión de Nico. **No se corrió nada sobre retornos.** Regla `CLAUDE.md`: antes de cualquier búsqueda sobre P&L se presenta manifiesto + número efectivo de hipótesis + riesgos + datos faltantes, y se espera el OK.
**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Por qué ahora hace falta una campaña

Todo lo vivo de research está cerrado o saturado (ver `artifacts/hippocampus/research_history_ledger.jsonl` en #56: 7 contraejemplos confirmados). La infraestructura de medición (MCPT/PBO/DSR/SPA, costos, gates G0–G5, L2, contratos causales de Frontier) ya alcanza para una campaña seria. Sin una campaña en curso, cada sesión agrega infraestructura y ninguna reduce la distancia al referente.

## Candidato A — Réplica multicontrato de HP-008 condicional (días rotacionales + corredor de vacío)

- **Justificación económica:** en NQ 25t, Lo-MacKinlay VR=0,9645 (autocorrelación negativa solo en 20–50 barras); el subconjunto "días rotacionales con vuelo libre a través de corredores de vacío" dio +7,30 pt con WR 63,6 %. Mecanismo propuesto: en régimen rotacional la liquidez pasiva absorbe el clímax HFT y el precio revierte; los corredores de vacío (HP-007, efecto microestructural certificado) marcan dónde no hay fricción.
- **Número efectivo de hipótesis: 1** (congelada tal cual quedó definida en `INFORME_FALSACION_ABSORCION_HFT_EMA_2026-09-17.md`; cero parámetros nuevos).
- **Riesgo principal:** es un **sobreviviente post hoc** — apareció después de que la versión incondicional falló. Alta sospecha de garden-of-forking-paths. Por eso el diseño es de *réplica*, no de búsqueda: mismas reglas, datos no usados.
- **Datos:** otros contratos NQ pre-holdout no usados en el hallazgo original (el scaffold ya existe: PR #33 `research/hp008-causal-multicontract-20260918`, 1 commit único). Falta: enumerar exactamente qué contratos/fechas se usaron en el hallazgo original para excluirlos, y fijar el criterio de "día rotacional" de forma causal (as-of, sin mirar el cierre del día).
- **Cómo podría refutarse:** efecto neto de costos CME ≤ 0 en los contratos nuevos, o IC del efecto que cruza cero con MDE publicado ≤ el efecto original.
- **Costo:** bajo. Un solo test. Mata o sostiene la única hipótesis condicional viva.

## Candidato B — P7 Frontier: tendencia × carriers (TREND_ABLATION_MANIFEST_V1)

- **Justificación económica:** el contrato ya la documenta — la tendencia tiene evidencia pública fuerte a horizontes largos y cross-asset, no como regla intradiaria libre; hay que medir si EMA/SMA/VWAP agregan información marginal sobre el carrier.
- **Número efectivo de hipótesis: 48 políticas cargadas** (8 carriers/mecanismos × 6 celdas incluyendo placebo shuffled, seed 20260921, 100 réplicas). Cada tupla de parámetros adicional multiplica.
- **Riesgos:**
  - 4 de los 8 carriers son BigTrap2 (trapped buyers/sellers). BigTrap2 como S/R e imán está **cerrado**; el mecanismo "fade" es distinto, pero el corpus BigTrap2 tiene un sesgo de población documentado (solo el toque).
  - Los carriers HFT requieren paridad HFT NQ V2 certificada — **solo existe en NQ**; en los otros 10 activos es `PARITY_ABSTAIN`. La campaña queda limitada a NQ o falla cerrado.
  - La calibración HFT multiactivo (`SCALED_FUNNEL_V1`) mostró deriva fuera de muestra en MES/GC/ZB.
- **Datos faltantes (el propio contrato lo dice):** dataset, fechas, contratos, costos, ejecución, no-solapamiento, incertidumbre clusterizada y survival gates — "still need a separate preregistration".
- **Costo:** alto (preregistro completo pendiente + 48 políticas).

## Recomendación

**A primero, B después.** A es un test único, barato y decisivo sobre la única hipótesis condicional que sobrevivió — si muere, se registra en el Brain y se cierra; si sobrevive a la réplica, pasa a ser el primer candidato genuino del proyecto. B tiene mejor diseño estadístico pero todavía le falta el preregistro completo, y la mitad de sus carriers vienen de una familia con historia de cierres.

## Qué necesito para avanzar con A

1. Tu OK explícito a este paquete (regla STOP).
2. Confirmar/enumerar los contratos y fechas usados en el hallazgo original de HP-008 (para excluirlos de la réplica).
3. Con eso redacto el preregistro formal (cita de este hash de North Star, justificación, refutación, MDE ex ante) — y recién ahí se corre.

Aporte al referente: ordena la próxima campaña por costo de falsación, no por atractivo narrativo; la opción recomendada es la que más rápido distingue un edge real de uno fabricado post hoc.
