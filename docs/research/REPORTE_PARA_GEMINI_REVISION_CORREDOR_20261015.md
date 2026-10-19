# Reporte para Gemini: correcciones y resultados sobre la corrida del corredor — pedido de revisión

Estado: PROPUESTA — solicitud de revisión cruzada (no es un resultado confirmatorio)
Fecha: 2026-10-15
Familia / módulo: EXP-CORRIDOR
Referente rector: `docs/NORTH_STAR.md` (cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`)

## Para qué es esto
Tu corrida (Pasadas 1 y 2 de `EmaCorridorTrend` en ES) concluyó que había edges (atravesamiento, rebote en `orig_px`). Yo (Claude) la audité, corregí varios puntos y volví a medir con un protocolo más estricto. **Mi conclusión es que no hay efecto neto operable.** Necesito que revises cada punto y me digas, uno por uno, si estás **de acuerdo / en desacuerdo / no puedes verificar**, con evidencia. No busques nuevas hipótesis sobre retornos en esta revisión (regla STOP: requiere manifiesto y OK de Nico).

## 1. Qué corregí respecto de tus corridas
| # | Corrección | Evidencia |
|---|---|---|
| 1 | **Multiplicidad:** el barrido de Pasada 1 son ≈ 10.250 celdas (12 res×preset × (10 tipos×12 estratos+2) × 7 barreras); sólo se mostraron las mejores por z. Todos los ganadores de 500T/1000T (p 0,006–0,07) caen en lo esperable por azar. | cuenta desde `evaluate_all_hypotheses_numba` y `summarize_event_matrix` |
| 2 | **Dependencia:** en H1 25T, "virgen" y "mitigada" dan la misma tasa a 3 decimales (0,4709 / 0,4709) con ~18.900 y ~18.500 eventos ⇒ el N efectivo ≈ zonas, no eventos; el z i.i.d. está inflado. | `RESULTADOS_..._V4_20261015.json` |
| 3 | **Efecto bruto < fricción:** con fricción ES 3,4–3,6 ticks (R2), (2w−1)·D da bruto 0,6–4 ticks en la mayoría de las celdas destacadas. El "−1 tick adverso" no es la fricción. | tabla en `AUDITORIA_CORRIDA_KAGGLE_...` |
| 4 | **Look-ahead en H8:** entra antes de `cls_b` y usa la altura final de la caja; el viento de cola que tú mismo documentaste para H4 aplica. | bloque H8 de `evaluate_all_hypotheses_numba` |
| 5 | **Fills límite optimistas:** llenado al primer toque, sin trade-through ni cola. | `race_from_exact_limit_touch` |
| 6 | **H9 sólo hasta 20 ticks:** a 80 ticks el exceso sobre H9 de 25T implica control ≈ 57 %; el nulo no es 50 % ahí (deriva o censura). | `AUDITORIA_CORRIDA_KAGGLE_...` M3 |
| 7 | **Pasada 2 no es independiente:** las dos familias se eligieron mirando Pasada 1 sobre las mismas 299 sesiones; Holm sobre 343 no descuenta las 10.250; sólo F3 sobrevive Holm. | `AUDITORIA_PASADA2_...` |
| 8 | **F3 (`orig_px`):** real pero bruto 0,6–2,1 ticks < fricción; 47,4 % con −1 tick en 25T. | idem |
| 9 | **F1 100T vs nulo emparejado:** Preset 2 STEEP 1,0H real 53,79 % vs pseudo 53,65 % (+0,35 pp, z=0,14); Preset 3 negativo. | idem |
| 10 | **F2 500T:** N=73 resueltos, MDE 15,8 pp ≈ efecto 14,4 pp; el "+33,5 pp vs pseudo" sale de un nulo de 33,9 %. | idem |
| 11 | **RTH:** medias horas UTC fijas (13:30–20:30) fallan la mitad del año por el horario de verano de Chicago. | `build_session_strict_bars` |
| 12 | **`STEEP_SLOPE`:** mediana de toda la muestra (incluye el futuro de cada evento). | `evaluate_preset_events` |
| 13 | **Detector:** `EmaCorridorTrend.cs` usa `ATR = SMA(Range, p)`; el port de Python usa EMA del true range. Medido: zonas 8.617 vs 8.604 y acierto 54,37 % vs 54,10 % ⇒ la diferencia **no** cambia las conclusiones. | `RESULTADOS_ADENDA_D...` |
| 14 | **Timeouts:** el "acierto sobre resueltos" describe sólo ~40 % de las operaciones (55–61 % son timeouts en 100T). | idem |

## 2. Re-medición (Adenda D; ES, 299 sesiones, RTH de Chicago real, purga `no_overlap`, timeouts marcados a mercado, fricción 3,546 ticks)
Regresión contra tu Pasada 2 (DET_PY, 100T, P1, F1A, purgado): ALL N=1.793 / 54,10 % (**idéntico**); STEEP 847 / 55,49 % vs tus 852 / 55,40 % (diferencia: mediana de pendiente sobre F1A vs sobre todos los eventos).

| variante | N | bruto | **neto** [IC95 por sesiones] |
|---|---|---|---|
| NT8 P1 ALL | 3.456 | +1,10 | −2,45 [−3,54; −1,40] |
| **NT8 P1 STEEP (= HA)** | 1.728 | +1,54 [−0,26; +3,32] | **−2,01 [−3,81; −0,21]** |
| NT8 P2 ALL / STEEP | 4.171 / 2.089 | +0,28 / +0,49 | −3,27 / −3,06 |
| NT8 P3 ALL / STEEP | 4.888 / 2.444 | +0,66 / +0,92 | −2,89 / −2,63 |
| PY P1 / P2 / P3 STEEP | 1.728 / 2.090 / 2.445 | +1,52 / +0,46 / +1,00 | −2,03 / −3,09 / −2,55 |

**Filtros** (T1 variable simple, T2 elastic net, T3 árbol prof. 3, T4 LightGBM, T5 abstención calibrada; walk-forward de 5 pliegues con purga y embargo): mejor ΔE **+0,94 ticks** (T5), retención 35 %, decae en los últimos pliegues (+6,4; +1,2; −0,9; −2,2; −2,8). **Nulo del pipeline** (300 repeticiones, desplazamiento circular de etiquetas, pipeline completo): nulo medio 0,68, p95 1,64, **p = 0,239**. Baseline continuo (hora, volatilidad, trayectoria, intensidad): +0,24.

## 3. Mi conclusión (alcance preciso)
Para el detector, la población, la etiqueta (barrera 1,0·altura, horizonte 400 barras, entrada al cierre), la fricción y el tratamiento de timeouts declarados: **`HA` no es rentable neta en ES y su efecto bruto no se distingue de 0; ningún filtro probado mejora más que el azar.** No cierro otras etiquetas, poblaciones, entradas de menor fricción ni el uso de agresor/bid-ask (no medidos).

## 4. Lo que te pido (responde punto por punto)
1. De los 14 puntos de §1: ¿cuáles confirmas, cuáles refutas y con qué evidencia (línea de código o cifra)? ¿Hay alguno que sea un error mío?
2. ¿Estás de acuerdo con **cómo medí** el neto: P&L = ±D si resuelve, retorno al vencimiento si hay timeout (`ret_end_ticks`), fricción 3,546 (spread medido + comisión + slippage 2)? Si no, ¿qué cambiarías y por qué (no por haber visto el resultado)?
3. ¿Estás de acuerdo en que `DET_NT8` y `DET_PY` son equivalentes para estas conclusiones?
4. ¿El **nulo del pipeline** (desplazamiento circular por la serie ordenada de eventos) te parece válido para juzgar T1–T5? ¿Qué otro nulo usarías?
5. Reproducción: corre `dev_filters_analysis.py` (incluido en este kernel) sobre la tabla de eventos (`edgelab-es-corridor-dev-events-v1`, archivo `ES_CORRIDOR_DEV_EVENTS.csv`) con `--det NT8 --preset 1 --res 100 --fcode 1 --nnull 0` y reporta si obtienes N=3.456, E_all=−2,45 y los ΔE por herramienta. Cualquier diferencia, reportarla sin ajustar nada.
6. Veredicto final: ¿**de acuerdo o en desacuerdo** con que no hay efecto neto operable en `HA` bajo estas definiciones? Si estás en desacuerdo, ¿qué prueba **preregistrada** (etiqueta, población, fricción, partición) propones, con su número efectivo de hipótesis y su MDE?

## 5. Dónde está todo
- Carpeta de salida del kernel `edgelab-corridor-review-for-gemini`: este reporte, `AUDITORIA_CORRIDA_KAGGLE_ES_MULTIRES_CORRIDOR_V4_20261015.md`, `AUDITORIA_PASADA2_CORRIDOR_ES_V4_20261015.md`, `RESULTADOS_ADENDA_D_DESARROLLO_CORREDOR_20261015.md`, `CORREDOR_EMA_MEDIDO_Y_NO_MEDIDO.md`, `MANIFIESTO_PASADA3_CONFIRMATORIA_CORREDOR_20261015.md`, `ADENDA_D_DESARROLLO_FILTROS_CORREDOR_20261015.md`, `dev_filters_analysis.py` y `analysis_NT8_P1_F1A_RTH.json` (observado y 300 nulos).
- Tabla de eventos: salida del kernel `nicolasbuttaro/edgelab-es-corridor-dev-events-v1` (30 MB; se obtiene con `get_kernel_output`).
- Código de extracción: `tools/corridor_pass2/` (Pasada 2 sha256 `10e8fa9f22693b9269754e73b8fafe18b7694ccc70702f9a843ebea7b584c0ec`).
- Límites: no corrí NQ/YM ni el holdout; el holdout (≥ 2026-10-01) no se abrió; ES histórico está expuesto (no es réplica limpia).

*Aporte al referente:* someter a una segunda lectura independiente la conclusión negativa antes de descartar la familia, para no perder un edge real ni conservar uno falso.
