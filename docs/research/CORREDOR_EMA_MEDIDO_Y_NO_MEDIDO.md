# Familia EmaCorridorTrend sobre ES — qué está medido y qué NO

Estado: VIGENTE (registro vivo; se actualiza en el mismo commit que cualquier resultado nuevo)
Fecha: 2026-10-16
Familia / módulo: EXP-CORRIDOR (independiente de HFTZones, BigTrap2, aVolCluster, LUX-IMB, YM-PRERANGE)
Referente rector: `docs/NORTH_STAR.md` (cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`)

## MEDIDO — con alcance preciso
| qué | resultado | alcance exacto |
|---|---|---|
| **`HA`: regreso virgen al borde exterior, cierre de la barra de reingreso, contra la tendencia (F1A), 100T, preset 1, `STEEP_SLOPE`, RTH** | bruto **+1,54 ticks** por operación (IC95 por sesiones −0,26 a +3,32); **neto −2,01** (IC95 −3,81 a −0,21) con fricción ES 3,546 ticks; 61 % de timeouts marcados a mercado | ES, 247 sesiones, N=1.728 tras purga `no_overlap`, barrera 1,0·altura de zona, horizonte 400 barras, entrada al cierre. Detectores `DET_NT8` (ATR=SMA(Rango)) y `DET_PY` (EMA del true range) dan resultados casi iguales |
| Variantes P1/P2/P3 × ALL/STEEP × detector | neto −2,0 a −3,3 ticks, todas con IC95 que excluye 0 por debajo | mismo alcance |
| **Filtros T1–T5** (variable simple, elastic net, árbol 3, LightGBM, abstención calibrada) sobre `HA` ALL | mejor ΔE **+0,94 ticks** (T5), retención 35 %, decae en los últimos pliegues; **nulo del pipeline p = 0,239** (300 repeticiones; nulo medio 0,68, p95 1,64) | ES desarrollo, walk-forward 5 pliegues con purga y embargo; el baseline continuo de hora/volatilidad/trayectoria logra +0,24 |
| `F3` rebote en `orig_px` (Pasada 2) | estadísticamente fuerte (z_cl hasta 9,8; Holm p<0,025 en 25T/100T) pero **bruto 0,6–2,1 ticks < fricción 3,4–3,5**; en 25T con −1 tick adverso 47,4 % | ES, 299 sesiones; estructura real, **no es edge** |
| `F2` penetración 25–33 % en 25T/100T | **refutada** bajo guarda de sesión y purga (acierto < 50 %) | ES |
| Equivalencia de detectores NT8 vs Python (ATR) | zonas 8.617 vs 8.604 (preset 1, 100T) | ES |

## MEDIDO — e inconcluso
| qué | resultado | por qué inconcluso |
|---|---|---|
| `HB`/`F2D` penetración 33,3 %, 500T, `STEEP_SLOPE` | 388 eventos RTH, **72 resueltos** (81 % timeouts); neto −0,50 [−6,7; +5,4] | sin potencia: MDE ≈ efecto |

## NO MEDIDO
- Cualquier otra etiqueta (objetivo estructural `orig_px`, horizontes distintos), población de eventos alternativa (creación, toques), entradas con menor fricción (límite con trade-through), uso de agresor/bid/ask.
- Confirmación en NQ/YM (sellados; no se abrieron porque `HA` ya es negativa neta en ES).
- Paridad zona a zona del port de Python contra NT8 (sólo se midió la sensibilidad al ATR).
- Prueba de prefijo vs streaming de las features.
- Replicación de ES: **no disponible** para esta familia (las 299 sesiones, incluida la ventana abr–sep, se inspeccionaron para diseñar: HOLDOUT-A3 regla 1 y 4).

## k36 y K37 (corredor x HFT con retornos, ES 100T) — 2026-10-17
- **k36** (178 sesiones de descubrimiento, 7 variantes x 3 universos, DSR m=44): **sin efecto detectado**. En el walk-forward ninguna variante supera costos (neto limite inmediato -0.6 a -1.5 ticks). Auditoria: `docs/research/k36_audit_20261017/`. El +1.38 de C2 en las ultimas 32 sesiones es una submuestra afortunada (walk-forward: -0.61).
- **K37** (`EXP-K37-CORREDOR-HFT-LADDER-TRAP-REPLICATION-V1`, replicacion trade_date 2026-04-01 a 2026-09-30, 121 sesiones, 116 con impulsos U1, una sola variante pre-registrada): veredicto **NO_SOPORTADA**. Neto pasivo realista, ARM_NOLADDER: **-1.99 ticks por trade** (IC 97.5 % [-2.95, -1.03], n=1.732); bruto -0.11 (el bruto del base en descubrimiento era +0.68). Nulo de exclusion aleatoria p = 0.47. Prueba de prefijo HFT v2: 1.145 zonas verificadas, diferencias 0.0. Resultados: `docs/research/k37_results_20261017/EXP_K37_RESULTS_20261017.json` (sha256 `ccfa83cc...50a0`).
- **Alcance de la muerte:** invalida exactamente "excluir impulsos con escalera opuesta sin barrer, operando la reversion simetrica 2 etapas tras impulsos de U1 (preset 1, fija 600, HFT tocada en W1), ES, ejecucion pasiva, costo 1.546 ticks". No dice nada sobre otros instrumentos, otras salidas ni otras poblaciones. Consume la replicacion abr-sep de la familia corredor x HFT.
- **No medido:** impulsos sin HFT en W1 operados como reversion; otros costos/ejecuciones; NQ/YM; el holdout >= 2026-10-01 (intacto).

## Retractaciones y correcciones
- Pasada 1 (barrido de ~10.250 celdas) y Pasada 2 (343 pruebas) **no confirman edge**: ver `AUDITORIA_CORRIDA_KAGGLE_ES_MULTIRES_CORRIDOR_V4_20261015.md` y `AUDITORIA_PASADA2_CORRIDOR_ES_V4_20261015.md`.
- Hash de NORTH_STAR citado como `ed4293b5…` en documentos del 2026-10-15: era stale; vigente `05df5c7c…`.
- Clasificación RTH de Pasada 2 (medias horas UTC fijas) incorrecta la mitad del año; corregida con hora real de Chicago en la fase D.

## Informes externos (no verificados en el repo)
- **k32** (`EXP-REV-PREREGISTERED-REPLICATION-AND-CONTINUAL-AI-20261016`, kernel Kaggle 138964727, recibido 2026-10-16): reversión al cierre de barras 100T en micro-zonas de 16 ticks (`P_REENTRY_F1A_P1/P2`), 3–5 op/sesión, con fills pasivos por replay tick a tick causal. En las 153 sesiones que el informe llama OOS (feb–mar + abr–sep 2026) la mejor variante da **−1,30 y −1,60 ticks/op netos**; DSR ≈ 0. **Refuta la familia a esa escala**, coherente con `HA` neto −2,01. Lo que el informe llama "121 sesiones vírgenes abr–sep" **no lo es** según este registro (ver NO MEDIDO): no cuenta como replicación. Auditoría: `AUDITORIA_K32_REPLICACION_RRE_20261016.md`; informe íntegro: `INFORME_EXTERNO_K32_REPLICACION_RRE_20261016.md`.

Resultados: `RESULTADOS_ADENDA_D_DESARROLLO_CORREDOR_20261015.md`. Código: `tools/corridor_pass2/` (Pasada 2 sha256 `10e8fa9f…`).

*Aporte al referente:* deja registrado qué se midió y qué no en la familia del corredor, con su alcance, para que ningún resultado ni ninguna ausencia de resultado se amplíe más allá de lo medido.
