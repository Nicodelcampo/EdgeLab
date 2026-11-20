# T-REGIMEN: el T de FundedSync desde 2021 es un régimen, no un sobreajuste de parámetros (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (1 prueba en `FUNDEDSYNC`), propuesta `PROPUESTA.md` (P-97). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `RESULTADO.json`, `GRILLA_OPS.csv.gz` (81 variantes, NQ
M1 real de futuros 2012-01 → 2026-09-29 — el motor de T arranca por defecto en 2012 (`portfolio_start_cash_date`; corrección de la auditoría de Antigravity, `AUDITORIA_ANTIGRAVITY_20261119.md` punto 1), R neto con fricción canónica). Etapa EF3, sin holdout.

## 1. Veredicto: REGIMEN_ROBUSTO (regla fijada antes de correr)
- **Meseta:** las **81 de 81** variantes tienen R neto > 0 en 2021-02-10 → 2026-09-29 (mínimo +0,087, p10 +0,116, mediana +0,149,
  máximo +0,205 R/op). La fábrica da +0,191 y queda 5.ª de 81; sus 8 vecinos a un paso tienen mediana +0,172 y los 8 son positivos.
- **PBO (CSCV, 16 bloques, 68 meses):** 0,17 (< 0,3): elegir la mejor variante en una mitad de los meses no se derrumba en la otra.
- **Año por año desde el quiebre:** todas las variantes positivas en 2021–2025 y el 98 % en 2026 (mediana de la grilla por año:
  +0,12 · +0,21 · +0,12 · +0,17 · +0,16 · +0,09).
- **Antes del quiebre (2012-01 → 2021-02-09, descriptivo; la grilla no cubre 2008–2011):** **0 de 81** positivas (mediana −0,037, mejor −0,004). Ningún ajuste de
  parámetros rescata a T antes de 2021 y ninguno la rompe después: lo que cambió es el mercado, no la elección de parámetros.

## 2. Lectura
- Lo que Nico sostenía queda respaldado con la prueba que lo podía refutar: la ventaja 2021+ no depende de la configuración elegida por el
  vendedor. Sí hay un poco de ajuste del diseñador (K38): la fábrica está en el 6 % superior de su vecindario. Para pronosticar conviene
  usar la mediana de la grilla (≈ +0,15 R/op neto) y no los +0,19 de la fábrica.
- Con +0,15 R/op y ≈ 229 operaciones por año, la tabla de `PROPUESTA.md` §2 da ≈ +34 R esperados en 12 meses con todo el efecto y
  P(12 m > 0) ≈ 0,85 aun reteniendo la mitad.
- El riesgo que queda no es de parámetros sino de régimen: si el flujo que lo produce se corta, todas las variantes caen juntas (como
  antes de 2021). Eso no se diversifica eligiendo otra variante; se vigila (prueba 4).
- Alcance: NQ. ES y YM tienen el mismo salto en bruto pero no pagan la fricción hoy (`RESULTADO_T_2020.md`); no se extiende a ellos.

## 3. Qué sigue
- **Prueba 2 (datos que el vendedor no vio):** falta la fecha de compra o de la versión de FundedSync (Nico).
- **Prueba 4 (vigilancia secuencial):** diseñar el corte en papel/forward sobre el R de T en NQ con `edgelab/funnel/secuencial.py`,
  calibrado al nivel 2021+ (≈ +0,15 R/op, sd 1,16).
- **Paso a candidata:** con la prueba 2 y la vigilancia armada, T en NQ pasa de pista a candidata con tamaño chico (micro).

## 4. Notas de la auditoría de Antigravity (2026-11-19)
- Corregido: la grilla empieza en 2012-01, no en 2008-01.
- Con `orb_bars` 10 y 20 la ruta rápida `direct_first_signal_near_vwap` no se activa (exige que el ORB termine en un cuarto de hora): esas variantes pierden una forma de entrada y aun así son todas positivas, lo que refuerza la meseta.
- Las 81 variantes están muy correladas (mediana 0,70; primer autovalor 72 %): la grilla descarta el ajuste fino de esos cuatro parámetros, no el de salidas y multiplicadores (1,25; 3 R; 15:30). La prueba 2 (datos que el vendedor no vio) sigue siendo la que cierra la duda.

## 5. Prueba 2 (datos que el vendedor no vio) — fecha resuelta (2026-11-19)
- El DLL analizado es el build `2026-10-29.1-FUNDEDSYNCSTACK` (`fundedsyncstack_20261115/INGENIERIA_INVERSA_FUNDEDSYNCSTACK.md`): el vendedor pudo ver toda la historia hasta el 2026-10-29. Fuera de muestra para él sólo hay ≈ 2 semanas del holdout ya abierto (30-oct → 13-nov, muy pocas operaciones) y el forward desde el 2026-11-14, que vigila `regimen_forward_20261119/` (canasta T+R, e-procesos de edge, futilidad y drawdown). La prueba 2 es, por lo tanto, el forward: no hay historia limpia que medir antes.
