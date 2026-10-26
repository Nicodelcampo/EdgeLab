# GAP_RTH — MEDIDO / NO MEDIDO

Estado: VIGENTE (registro vivo; se actualiza en el mismo commit que cada resultado).

## MEDIDO
- 2026-10-25 DESC (480 pruebas; USATECH/USA500/USA30 2023-01 → 2026-03 con costos del futuro; canal de desarrollo en NQ/ES/YM jul-2025 →
  mar-2026): 2 nominadas por FDR, NQ reciente, gap ≥ 0,6 ATR cerrado entero: +58 y +79 pts/op (n 49). En el futuro NQ la misma celda
  +100 pts/op (n 40). ES positivo más chico; YM no. `RESULTADO_GAP_RTH_DESC.md`.

- 2026-10-25 RÉPLICA NQ abr–sep (43 operaciones por celda): +3,99 y −1,35 pts/op, IC90 ±55–60, MDE 82–93; LORD++ t=1 no rechaza
  -> **SIN_POTENCIA**, no confirmada; estimación puntual ≈ 0 (el efecto del canal reciente estaba inflado por la selección).
## NO MEDIDO
- Holdout (no se abre con una réplica sin potencia y estimación ≈ 0).
- Gap contra el cierre de la sesión CME, primer toque del cierre previo, estado continuo de distancia al cierre previo.
- Filtro de noticias en la apertura (09:30 ET coincide con datos macro de 08:30 ya publicados; no medido el impacto).
