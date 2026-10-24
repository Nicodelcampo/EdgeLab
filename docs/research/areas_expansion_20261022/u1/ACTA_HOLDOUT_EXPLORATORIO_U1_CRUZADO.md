# Acta — mirada EXPLORATORIA del holdout de U1-CRUZADO (2026-10-23), registrada antes de correr

Estado: VIGENTE. Decisión de Nico en el chat: «1». Mirar ahora, como exploración, sabiendo que con unas 10–15 operaciones no se
confirma ni se refuta.

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`

## Regla congelada (sale de `PREREGISTRO_TOPES_Y_DENSIDAD_U1.md`)
- **Señal:** U1 sobre USATECH (Dukascopy): N ≥ 3 zonas en 40 pts, A/H ≥ 8, regreso al 75 %.
- **Ejecución:** NQ, con la base trasladada, en el tick siguiente.
- **Objetivo:** borde lejano del área (T3).
- **Stop:** más allá del extremo, con tope de 3× la distancia al objetivo.
- **Fricción:** canónica de NQ, 1,5455 pts.
- **Código:** `edgelab/research/u1_cruzado.operar(..., tope=("mult", 3.0))`, ejecución `E1A/T3/S3`.
- **Informativo:** también se reporta T1 con el mismo tope.

## Datos (sellados)
| fuente | ruta | período |
|---|---|---|
| USATECH | `E:\DatosNT8\tick_history_HOLDOUT_SELLADO\dukascopy\USATECHIDXUSD\ticks` (JForex) | sesiones 2026-10-01 → 2026-10-22 |
| NQ 12-26 | `E:\DatosNT8\tick_history_HOLDOUT_SELLADO\NQ_12-26_ticks.parquet` | 2026-10-01 → 2026-10-21; hueco del 7–8 de octubre |

Las zonas y áreas se arman sólo con datos del holdout (no hay historia previa cargada), así que las primeras horas tienen menos
señales.

## Consecuencias declaradas antes de mirar
1. Con n ≈ 10–15 el resultado **NO confirma ni refuta**: veredicto NO_CONCLUYENTE salvo que n ≥ 95.
2. **La apertura limpia de U1-CRUZADO sobre las sesiones 2026-10-01 → 2026-10-22 queda consumida.** Una confirmación futura sólo
   puede usar sesiones posteriores al 2026-10-22, con esta misma regla intacta.
3. El resultado no se usa para ajustar la regla (tope, objetivo, celda).

## Resultado (2026-10-23) — `RESULTADO_HOLDOUT_EXPLORATORIO_U1_CRUZADO.json`
- **Señales:** 11 de U1 en el CFD; 8 se operaron en NQ por ejecución. Las otras cayeron en el hueco del 7–8 de octubre o el 22, que
  no tiene NQ. Las 8 están en 4 sesiones.
- **Regla congelada (T3, tope 3×):** n = 8, media neta **+29,4** pts/op, 7 de 8 ganadoras, peor −94,3. IC90 por sesión [−1,2, +72,0], p = 0,15.
- **Informativo (T1, tope 3×):** n = 8, media **+38,6**, 8 de 8 ganadoras.
- **Veredicto: NO_CONCLUYENTE** (n = 8 << 95), como se declaró antes de mirar. Es la primera evidencia fuera de todo lo usado y va
  **a favor** de la regla, pero son 8 operaciones en 4 sesiones.
- **Próximo paso:** la confirmación sólo puede usar sesiones posteriores al 2026-10-22, con esta regla intacta y N fijo. Lo hace el
  embudo: conteo sin P&L hasta N y una sola mirada.
