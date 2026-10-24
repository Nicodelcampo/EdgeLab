# Resultados M1/M2/M3 — impulsos LUX-IMB en NQ, descubrimiento (HOLDOUT-A3)

Estado: MEDIDO. Veredicto: **SIN EFECTO DETECTADO** (H1-H7, Holm = 1,0 en todas). Preregistro:
`PREREGISTRO_M1_M2_M3_LUXIMB_NQ_20261020.md` (commit anterior a la corrida). Codigo: `tools/luximb_parity/luximb_outcomes.py`
(commit `d400a8b7` + fix de nombre de columna, sin cambio de reglas). Arbol limpio salvo `bundles/manifest.js` (gitignorado de facto, catalogo del visor).
Datos: NQ 09-25, 12-25, 03-26, 06-26 hasta 31-mar-2026, release v4. Eventos: `RESULTADOS_M1_M2_M3_NQ_DESCUBRIMIENTO_eventos.csv`.

| grupo | n | dias | P(rebalanceo 50 % primero) | P(extension +25 % primero) | P&L fade neto (1 tick) | P&L continuacion neto (1 tick) |
|---|---|---|---|---|---|---|
| T: impulso con zonas (v5) | 330 | 109 | 0,433 | 0,564 | -2,05 pts | +0,84 pts |
| C: misma amplitud, <= 2 zonas | 2.046 | 167 | 0,448 | 0,543 | +0,03 pts | -1,23 pts |

| hipotesis | estimacion | IC 95 % (bootstrap por dia) | p | Holm |
|---|---|---|---|---|
| H1 P(Tg) T - C | -1,4 pp | [-7,6, +4,2] | 0,69 | 1,0 |
| H2 P&L fade T | -2,05 pts | [-5,8, +1,3] | 0,88 | 1,0 |
| H3 P&L continuacion T | +0,84 pts | [-2,5, +4,6] | 0,31 | 1,0 |
| H4 sube / baja | +2,3 / -5,2 pp | [-5,8, +10,1] / [-13,8, +3,6] | | 1,0 |
| H5 cash / resto | -2,5 / +0,2 pp | [-12,6, +7,2] / [-6,8, +6,5] | | 1,0 |
| H6 opuestas < / >= 0,5 | -4,5 / +0,6 pp | [-12,8, +3,4] / [-6,9, +7,5] | | 1,0 |
| H7 P&L fade T - C | -2,07 pts | [-6,0, +1,5] | 0,87 | 1,0 |

**MDE80 de H1 = 8,4 pp.** El IC de H1 excluye un efecto de rebalanceo de +4,2 pp o mas: el "rebalanceo por zonas" de
>= 8 pp esta descartado con potencia. Canal no direccional (60 min, en R): MFE del fade p50 0,64 (T) vs 0,74 (C); MAE p50
0,71 vs 0,70 — las zonas no agregan recorrido en ninguna direccion. Signo por contrato: T no supera a C en ninguno.

## Alcance de la muerte
Muere: rebalanceo (50 % de vuelta antes de +25 %) de impulsos NQ M1 definidos por `LUXIMB-IMPULSOS-v5-reparto`
(vida 500, p80, tercios <= 60 %), con entrada al cierre de la vela de marca, en descubrimiento. No muere: otras
geometrias de salida, otras vidas (200 no medida con desenlaces), otros instrumentos, ni zonas LUX-IMB como nivel
individual. La continuacion (H3) tampoco tiene evidencia.
Replicacion: no corresponde (no sobrevivio nada en descubrimiento). Holdout intacto.

Aporte al referente: descarta con potencia (MDE 8,4 pp) que atravesar muchos desequilibrios OG/VI haga mas probable el
rebalanceo del impulso en NQ, y evita gastar replicacion/holdout en una idea sin efecto.
