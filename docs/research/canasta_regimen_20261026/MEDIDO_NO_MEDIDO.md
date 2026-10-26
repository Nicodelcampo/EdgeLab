# Canasta de estrategias de régimen — MEDIDO / NO MEDIDO (registro vivo)

Estado: VIGENTE
Fecha de creación: 2026-10-26. Se actualiza en el mismo commit que cada resultado nuevo sobre la tesis de régimen.
Tesis (Nico, 2026-10-26): la ventaja económica de EdgeLab sería una canasta de estrategias de régimen renovada rápido.

## MEDIDO
| fecha | qué | resultado | alcance exacto |
|---|---|---|---|
| 2026-10-26 | persistencia de régimen del rendimiento de celdas (CANASTA-REGIMEN-1) | no detectada; MDE ρ 0,05–0,13 | grilla U1 completa (4,48 M celdas), CFD USA500/USA30/USATECH/XAU con fricción del futuro, feb-2023 → mar-2026, horizontes 1→1, 3→1, 3→3, 6→3 meses |
| 2026-10-26 | canasta top-k por rendimiento reciente (32 reglas) | ninguna pasa BH q 0,10; USATECH positiva en 7/8 | k ∈ {10, 100}, formación 1 o 3 meses, criterio t o media, mismo alcance |
| 2026-10-26 | calidad estática de celdas | persiste a 12 meses; positiva sólo en USATECH | mismo alcance |
| 2026-10-26 | 6 candidatas U1-ES/YM, trimestres 2023–2025 | ≈ 0, autocorrelación trimestral ≈ 0 | `u1_cfd_20261025/LINEA_DE_TIEMPO_CANDIDATAS_U1_ES_YM_20261026.md` |

## NO MEDIDO (la idea general de régimen sigue viva por acá)
- Régimen definido por **estado del mercado** (volatilidad realizada, tendencia, rango, horario, calendario macro) para ponderar estrategias.
- **Otras gramáticas**: LUX-IMB, ZGAP, GAP-RTH, U1-ZONAS (AVZP2/AVCL), escalonadas, aVolClusterPOI, ORB.
- **Futuros con ticks reales** (ES/NQ/YM/GC desde jul-2025) y 6E/EURUSD.
- **Horizontes** de días y semanas; más de 6 meses.
- **Otras reglas de canasta**: ponderación por riesgo, retiro por drawdown, diversificación mínima, combinación entre instrumentos.
- **Período desde abr-2026** (réplica A3 y holdout): el régimen actual puede ser otro.
