# Auditoría de "Iteración 2: herramientas acopladas y sistema de 3 franjas grilla" y cómo encaja con lo que el repo ya tiene

Estado: PROVISIONAL (un solo auditor: gonzasib-claude)
Fecha: 2026-10-16
Familia / módulo: TRES-FRANJAS (DESDE DÓNDE / POR DÓNDE / A DÓNDE) · se solapa con EXP-CORRIDOR y HP-007 · módulo `autopilot`
North Star: `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`
Procedencia: informe de diseño enviado por Nico por Chaski el 2026-10-16, copia íntegra en `INFORME_EXTERNO_ITERACION2_TRES_FRANJAS_20261016.md`. No trae datos ni corridas: se audita como propuesta, no como resultado. Antecedente k32: `AUDITORIA_K32_REPLICACION_RRE_20261016.md`.

## Veredicto

**La idea central es buena y ya tiene media implementación en el repo; la arquitectura propuesta es diez veces más grande que la muestra que la puede sostener.** Las tres franjas son exactamente lo que HP-007 llama murallas y corredores del campo de densidad `D(p,t)`, con dirección en `corridor_geometry`. Lo nuevo y aprovechable es (a) segmentar por perfil de volumen con `find_peaks` y compararlo con el campo, (b) tratar la travesía del corredor como una cadena de tres preguntas con veto por etapa, y (c) la disciplina de fills causales y cota conformal frente a la fricción. Lo que no se sostiene es querer resolverlo con tres sub-modelos, un ranker, un encoder convolucional con atención y cuatro calibradores a la vez, sobre un instrumento cuya ventana sin usar antes del holdout ya no existe.

## Hallazgos

1. **Ya está medido lo que la propuesta da por bueno, y el número va en contra.** HP-007 §4.3 midió la travesía pared a pared por amplitud del corredor: angosto (4–7 ticks) atraviesa el 42,5 %, medio (8–14) el 22,2 %, amplio (15–30) el **9,3 %** con expectativa −0,275 R. La Iteración 2 exige `H_por ≥ max(24 ticks, 6·ATR)` para que la fricción sea < 10 % del canal. Con la tasa medida, el recorrido esperado `p · H` es ≈ 2,2 ticks (angosto), 2,4 (medio) y 1,9 (amplio): **todos por debajo de la fricción de ES (3,55 ticks por viaje), y el bucket que la propuesta elige es el peor.** La hipótesis real, la única que vale medir primero, es: ¿el estado de DESDE DÓNDE (ignición, absorción) y de A DÓNDE (imán, virginidad) levanta la tasa de travesía de corredores amplios del 9 % a algo que pague? Eso es una pregunta de información, no de P&L, y entra en la cadena del producto antes de cualquier modelo.
2. **"Sin parámetros arbitrarios" es falso.** Conté más de veinte constantes: σ = 2 ticks, `distance=8`, `prominence=P_min`, `rel_height=0.65`, 0,35·H para DESDE, 24 ticks / 6·ATR, 180 s de espera, 0,35·H de escape, 25 % de ignición, 80–100 % de tránsito, 32 columnas en 4 regímenes, 6/12/6 filas, 6 canales, 3 umbrales τ, M ≤ 5, α del CQR, ΔS = 20, decay 0,90, ≥ 32 ticks para PU. Cada una es una perilla. El mandato permite 3 parámetros libres por candidata: la propuesta tiene que partirse en candidatas, cada una con sus 3 perillas declaradas y el resto congelado en un manifiesto antes de tocar datos.
3. **Muestra.** El objetivo operativo es 0,3–0,8 operaciones por sesión. Con ~150 sesiones utilizables de ES eso son 45–120 operaciones: no entrena ni un árbol de profundidad 2 con 36 features. HP-007 tuvo ~3.200 travesías pared a pared para la capa de información; un encoder 6×24×32 con FiLM, strip pooling y atención axial sobre 3.000 eventos, cuyos embeddings fuera de pliegue entran después a LightGBM, es una máquina de sobreajuste con dos niveles de fuga. El encoder queda como `falta` en el catálogo, sólo para proponer, hasta que haya ≥ 10⁴ eventos etiquetados.
4. **El veto TreeSHAP por bloque es una buena regla de no compensación, pero son tres parámetros más y pierde sentido con embeddings en las features.** Si las features son legibles (densidad, ancho, absorción, virginidad), la atribución por bloque es útil para el post-mortem F1/F2/F3 de §3. Con embeddings, Φ_Cross se come la explicación.
5. **El ranker de tripletes necesita etiquetas contrafactuales por replay causal para cada par candidato** (¿llegó a A_m antes del stop?), y esas etiquetas están correlacionadas dentro del episodio. Con pocos episodios por sesión, `lambdarank` no tiene con qué ordenar. Medir N antes.
6. **La cota inferior conformal (CQR + ACI) como compuerta de ejecución es un filtro aprendido**: cuenta como prueba, se calibra en partición propia y se evalúa en otra. Bien planteada, pero no es "libre de heurísticas": es un modelo más.
7. **Datos.** Los canales C2 (delta por agresor) y C3 (tamaño medio) existen en la captura (`aggressor` en `edgelab/data/capture_tsv.py`) pero el registro de la familia los lista como NO MEDIDO. El L2 tiene 34–60 sesiones por producto y la captura está cortada desde el 2026-09-28: cualquier feature de libro deja la propuesta sin potencia. Primera versión: sólo trades.
8. **Ventana.** Abr–sep 2026 de ES está quemado para diseño (registro de la familia y `AUDITORIA_K32_...`); el holdout empieza el 2026-10-01. Todo desarrollo sobre ES es desarrollo. La confirmación de esta familia es en NQ/YM sellados, con manifiesto previo, o con datos nuevos.
9. **Lo que sí aporta y entra al sistema.** Segmentación topográfica por volumen (para comparar con el campo), Wasserstein como feature de absorción/asimetría, veto aditivo por bloque, Venn-Abers, CQR+ACI, ranker, encoder: las siete quedan en `config/autopilot/herramientas.json` con estado `falta`, su referencia, lo que exigen y contra qué se verifican. El agente puede proponerlas; no puede medir con ellas hasta que alguien las implemente con paridad.

## Cómo encaja con el resto del proyecto

| Pieza de la Iteración 2 | Lo que el repo ya tiene | Qué hacer |
|---|---|---|
| POR DÓNDE (valle de volumen) | corredor de baja densidad en `density_field.detect_density_intervals` (HP-007), paridad JS probada | medir solapamiento IoU entre valles por volumen y corredores por densidad antes de elegir una definición |
| DESDE / A DÓNDE (crestas) | murallas de alta densidad; zonas HFTZones / BigTrap2 (familias ya medidas y cerradas como edge) | reutilizar como ubicación; la novedad es el estado (ignición, virginidad), no la zona |
| Dirección del viaje | `corridor_geometry` BULL/BEAR/DUAL (no certificada) | certificarla es prerequisito del flujo A |
| p_tránsito | HP-007 §4.1–4.3 (velocidad en vacío 3× en tiempo real; travesía por amplitud) | es la línea base; la candidata tiene que superarla con el estado de DESDE y A |
| Fricción | `edgelab/autopilot/friccion.py` (3× por viaje; ES 3,55) y R2 (recorrido 15–60 min paga fricción en índices) | el horizonte útil es 15–60 min, no 180 s |
| Fills | `edgelab/engine.py` (tick a tick, trade-through) | falta la máquina de estados de orden límite con espera y cancelación (k32) |
| DSR/PBO, MCPT, SPA | `edgelab/research/g2.py`, `validation/` | ya verificadas; usarlas, no reimplementarlas |
| Filtros ML | `tools/corridor_pass2/dev_filters_analysis.py` (T1–T5, LightGBM ad hoc) | pasar a técnica verificada con prueba de paridad si se va a medir con ella |

## Plan por etapas (cada una es una candidata con ≤ 3 parámetros libres y manifiesto propio)

1. **E0 Geometría (target-free).** Franjas por `find_peaks` sobre el perfil de volumen vs corredores del campo HP-007 en las mismas sesiones: solapamiento, estabilidad de bordes, cuántas franjas por sesión. Salida: una definición de franja con prueba de paridad. Perillas: σ, `prominence`, `rel_height`.
2. **E1 Información.** ¿El estado de DESDE (absorción C3, giro de delta C2, Wasserstein) y de A (virginidad C4, prominencia) predice la travesía de un corredor amplio por encima de la tasa base de HP-007 §4.3? Un modelo monótono chico (o una regresión logística con 3 features), walk-forward con purga y embargo, Venn-Abers cuando esté verificado. Criterio de éxito pre-registrado: levantar la tasa del bucket amplio del 9 % a un umbral declarado, fuera de muestra.
3. **E2 P&L bruto.** Sólo si E1 pasa: fills causales de orden límite (técnica a implementar), fricción 3×: con `H` = 30 ticks hace falta `p ≥ 0,36`. Replay tick a tick, reporte IS / VAL / OOS por separado, DSR/PBO con M del ledger.
4. **E3 Replicación.** Manifiesto sobre NQ/YM sellados o datos nuevos. ES no tiene ventana.
5. **Encoder y ranker:** sólo después de E1 positiva y con N medido; antes, no son candidatas.

## Qué queda abierto

- Decidir con Nico si LightGBM, MAPIE y torch entran a `requirements` (hoy sólo scipy y scikit-learn en scripts ad hoc): chequeo de salud y decisión humana.
- Cablear el cierre del ledger de herramientas (hit / nulo / fallo) en el análisis de corridas (`brain.py`): hoy sólo se registra `lanzada` al promover.
