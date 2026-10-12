# Plan para aprovechar e indagar el hallazgo de GC («resto del día → última media hora»)

Referencia: IDM-1, prueba `idm/GC` (futuro 2025-07→2026-09: corr +0,309, n = 274, Holm 10 = 0,009). Todo lo de abajo es **descriptivo** salvo lo que se pre-registra en IDM-2.

## 1. ¿Quedan datos? (corrección de una lectura)
«Hasta mayo» era solo mi caché local (126 sesiones). La corrida de Kaggle usó **todo** el futuro hasta 2026-09-30 (274 sesiones), así que no queda muestra sin usar *en el futuro de GC*. Sí hay datos distintos:
- **Spot XAUUSD (otra fuente), 2022-07 → 2026-09 continuo.** En el mismo período del hallazgo da +0,244 (n = 385): el efecto **no es un artefacto de los datos del futuro**. No es replicación (mismo mercado y mismo tiempo).
- **Spot 2022-07 → 2025-06** (muestra anterior): es la que sirve para probar mecanismos nuevos.
- **Posterior a 2026-09-30:** holdout cerrado.

## 2. Qué muestran los diagnósticos (spot y caché de futuro; descriptivo)
- **Se concentra en un trimestre.** 2026Q1: +0,435; sin 2026Q1: +0,076 (spearman 0,117); sin los 10 días más influyentes: +0,128. Los días de mayor influencia son caídas extremas (2026-01-30: ROD −980 pb, LH −88 pb; 2026-02-02; 2026-03-03).
- **Se concentra en movimientos grandes.** Tercil alto de |ROD|: +0,376; bajo: −0,051 (2025-26).
- **Varía en el tiempo.** Spot: 2022-07→2023-12 +0,204 (n = 462); 2024-01→2025-06 −0,055 (n = 463); 2025-07→2026-09 +0,244; semestres 2025H2 +0,09, 2026H1 +0,36, 2026Q3 +0,01.
- **No es un pico exclusivo de las 14:30:** el scan de medias horas (2025-26) muestra valores de −0,34 (12:30, justo en el cierre de la sesión regular de metales) a +0,24; 14:30 es el mayor positivo, 14:00 (+0,18) lo acompaña.
- **Economía bruta (sin costos, 2025-26):** seguir el signo de ROD de 14:30 a 15:00 rinde +1,94 pb (t 2,18) = USD 0,88/oz (≈ 88 por contrato), 45,7 % de aciertos; en el tercil grande +5,46 pb = USD 2,64/oz, 58 % de aciertos. Spread mediano ≈ USD 0,36/oz. En 2022-25 el mismo cálculo da +0,66 pb (< spread).
- **Lo que miré antes de pre-registrar (transparencia):** en el spot 2022-2025 vi el tercil alto de |ROD|: corr +0,026 (n = 309). Esa versión del refinamiento **no replica** y esa muestra ya no es virgen para ella.

**Lectura honesta:** el hallazgo es real en 2025-26 en dos fuentes, pero es episódico (un trimestre extremo y días de crash), no se extiende a 2024-25 y el refinamiento «movimientos grandes» no se sostiene en 2022-25. Es una pista débil, no un edge.

## 3. Revisión de herramientas y qué se decide usar
| Elemento | Decisión | Por qué |
|---|---|---|
| Literatura (Baltussen et al. 2021): incluye oro y commodities; saltos del día predicen la última media hora; efecto estable 1974-2020; pero solo ~40-50 % de contratos de commodities tienen R² fuera de muestra positivo | **Usar** | Da el mecanismo a probar (saltos) y calibra el prior (a favor y en contra) |
| **IDM-2** (nuevo): descomponer ROD en saltos y movimiento continuo; probar `b_salto > 0` en spot 2022-25 (primaria) y en otros 7 activos; GC futuro como referencia fuera de Holm | **Usar, ya lanzado** | Prueba el mecanismo en una muestra donde la descomposición no se miró; 8 pruebas, Holm 8 |
| **Activos hermanos independientes** (plata, platino, paladio, petróleo spot 2022-07→2026-09) | **Pedir datos** (`PROMPT_SESION_LOCAL_METALES.md`) | Única forma de tener activos independientes en el MISMO período del hallazgo; luego se corre IDM-2 sobre ellos |
| Leave-one-quarter-out por trimestre | **Ya incluido** en IDM-2 (descriptivo) | Cuantifica la dependencia de un trimestre |
| Nulos de calendario y de exposición de `schedule_nulls.py` (PR #64) y costos | **Después**, solo si IDM-2 o los metales dan apoyo | Sin apoyo fuera de muestra no se justifica una prueba de estrategia neta de costos |
| Gamma/DIX (GEX) | **No** para GC | En IDM-1 la diferencia por gamma en ES no pasa (p 0,175) y oro no tiene gamma de índice |
| AVCL / volumen, EMA, familias, calendario Ghost, rebote bid-ask | **No** | Otra información, otro activo o ya fallaron; el horizonte de 30 min no es de rebote |
| Edge Brain | **Usar** | IDM-1 y esta pista quedan como episodios; lección: mirar siempre sin-un-trimestre y qué se miró antes |
| Datos GC 2022-25 de NT8 (futuro) | **Baja prioridad** | Solo aclararía diferencias de venue; el spot ya cubre ese período |
| Confirmación prospectiva (posterior a 2026-09-30) | **Decisión humana** (WAIT-GC_LH_MOMENTUM) | Única muestra independiente en el tiempo |

## 4. Secuencia
1. IDM-2 (en curso): ¿es el componente de saltos lo que predice, y aparece en 2022-25 y en otros activos?
2. Con el resultado: si hay apoyo → DATA-METALS y réplica en hermanos; si no → la pista se degrada y se archiva el hallazgo como episódico.
3. Solo con apoyo repetido: estudio de estrategia neta de costos con nulos de calendario y exposición.
4. Siempre: confirmación prospectiva fuera de muestra decidida por vos.
