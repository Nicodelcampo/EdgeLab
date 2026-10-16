# Auditoría de la corrida Kaggle `ES_MULTIRES_CORRIDOR_ZONES_V4` (EmaCorridorTrend, 4 resoluciones, 299 sesiones)

Estado: PROVISIONAL (auditoría de un solo auditor)
Fecha: 2026-10-15 · Auditor: Claude (un solo auditor; **no** es el panel independiente de la propuesta `PROPUESTA_MODELO_REVERSION_GRILLA_MULTIESCALA_20261015.md`)
Objeto auditado: reporte y JSON consolidados en `EdgeLab_Bridge/resultados_claude_local/` (`RESULTADOS_EMPIRICOS_KAGGLE_ES_MULTIRES_CORRIDOR_ZONES_V4_20261015.{md,json}`), salidas crudas `outbox/out_k16_poll2` (v1) y `out_k18_poll1` (v2), script `edgelab_es_multires_corridor_zones_v4_fast_v2.py`, dossier `DOSSIER_REPRODUCIBILIDAD_Y_AUDITORIA_PASADA1_...md`.

## Veredicto

**NO APROBADA como evidencia de edge. Estado correcto: exploración de Pasada 1, `SIN CONFIRMAR`.**
El reporte afirma que los datos "confirman la hipótesis" y que existe una "ley de bifurcación". Con lo que está en los archivos, **no se puede sostener**: faltan las defensas que el propio dossier de la corrida declara ausentes, el efecto bruto es en su mayoría menor que la fricción, y hay indicios de dependencia entre eventos y de contaminación con información futura en parte de las familias.

## Qué sí es sólido (verificado)
- Holdout: el cargador filtra `trade_date < 20261001` y `ts_utc_ns < 1790812800000000000` (2026-10-01 00:00Z); 299 sesiones, 305.388.908 ticks, consistente entre reporte, JSON y log de Kaggle. Cumple el firewall.
- Se corrigieron en v2 dos sesgos reales de v1 (entrada en el nivel en vez del cierre; control nulo `b−150` condicionado al futuro). Que el control causal `cls_b+30` dé ≈50% en 0,5H/10t/20t/asimétrica es una buena prueba de que **el motor de carreras no tiene sesgo mecánico a barreras cortas**.
- `pnl_computed = False` y la inclusión del control H9 son prácticas correctas.

## Hallazgos

### Bloqueantes
**B1. Se corrió una búsqueda sobre retornos sin el STOP.** Una carrera de barreras es un resultado de precio; `pnl_computed = False` no la exime. `CLAUDE.md` exige manifiesto + número efectivo de hipótesis + riesgos + OK de Nico antes. No hay manifiesto. Todo lo que sigue es exploratorio y no puede promoverse.

**B2. Las defensas anti-sobreajuste no se aplicaron, y el dossier lo admite.** §5 del dossier lista como ausentes en la Pasada 1: guarda de sesión (las barras se concatenaron por contrato trimestral, así que una zona o una carrera pudo cruzar el corte diario), purga de solapamiento, error estándar clusterizado por sesión, MDE, Holm/FDR, MCPT por sesión, estabilidad temporal OOS, espejo y fricción. El reporte presenta como conclusión lo que el dossier llama pasada exploratoria.

**B3. Multiplicidad sin contar.** Del código: 12 combinaciones resolución×preset × (10 tipos de evento × 12 estratos + 2) × 7 barreras ≈ **10.250 celdas de prueba** (cada una con lectura de "atravesar" y de "rebotar"). Bajo el nulo se esperan ≈ 510 celdas con p<0,05, ≈ 100 con p<0,01 y ≈ 10 con p<0,001. El umbral de Bonferroni es p≈4,9·10⁻⁶ (|z|≳4,6). Los resultados tabulados son los mejores por z de ese universo (el JSON sólo conserva las listas "top"; el universo completo **no está** en los archivos entregados).
- **Todos** los ganadores de 500T y 1000T (z 1,8–3,4; p 0,006–0,07; N 56–461) están dentro de lo esperable por azar. Ninguno sobrevive.
- Sólo superan |z|≈4,6 sin corregir por dependencia: algunos de 25T (N de 10⁴) y 100T/H1–H7. Ver B4.

**B4. Los eventos no son independientes y el z asume que sí.** Evidencia en la propia salida: en H1 límite a 25T, "virgen" y "mitigada 2.ª+" dan la **misma** tasa a tres decimales (0,4709 vs 0,4709; 0,4927 vs 0,4928; 0,495 vs 0,4957) con ~18.900 y ~18.500 eventos. Dos retests de la misma zona comparten el resultado, por lo que el N efectivo es del orden de las zonas (y menos, por régimen intradía), no de los eventos. Con z calculado como binomial i.i.d., los z de 25T (9–13) están sobreestimados por un factor desconocido. Se necesita bootstrap/SE clusterizado por sesión (299 sesiones).

**B5. Efecto bruto menor que la fricción en la mayoría de las celdas destacadas.** Con fricción de ES ≈ 3,4–3,6 ticks ida y vuelta (R2) y barrera simétrica ±D, el beneficio bruto por carrera resuelta es (2w−1)·D:

| Celda | w | D (ticks) | Bruto | Neto (−3,5) |
|---|---|---|---|---|
| 25T P3 H2-close ALL, 40t | 53,62% | 40 | +2,9 | **−0,6** |
| 25T P2 H2-close VIRGIN, 40t | 54,18% | 40 | +3,3 | **−0,2** |
| 25T P2 H2-close HIGH_SCORE, 40t (N=1.635, z=4,31) | 55,47% | 40 | +4,4 | +0,9 (no pasa Bonferroni) |
| 25T P2 H2-close VIRGIN, 1,0H (≈20t) | 51,39% | ≈20 | +0,6 | **−2,9** |
| 25T H1 rebote 0,5H (≈10t) | 56,76% | ≈10 | +1,4 | **−2,1** |
| 25T H7 rebote 0,5H (≈10t) | 53,32% | ≈10 | +0,7 | **−2,8** |
| 100T H1 rebote 10t, P1 (N=1.037) | 60,66% | 10 | +2,1 | **−1,4** |
| 100T H7 rebote 1,0H HIGH_SCORE (N=782, z=4,60) | 58,82% | ≈38 | +6,7 | +3,2 *(sólo si el fill límite es real; ver M2)* |

Es decir, las celdas con z alto de 25T y los "rebotes cortos" **pierden dinero neto aun si fueran reales**. La única candidata que deja neto positivo con N razonable es 100T/H7 con fill límite supuesto, y está en el borde de la corrección.

### Mayores
**M1. Posible contaminación con información futura (familia H8 y estratos con la caja final).** El dossier (artefacto 3) reconoce que entrar antes de `cls_b` da "viento de cola" porque se sabe ex post que el corredor se rompe en −z_dir. Eso se corrigió sólo para H4; **H8** (`for b in range(conf_b+1, cls_b)`, primer pullback a la EMA) sigue entrando antes de `cls_b` y su barrera `1,0_ZoneHeight` usa la altura **final** de la caja (conocida recién en `cls_b`). Los ganadores de 1000T H8 (57,9% y 60,7%) están en esa familia. H2/H3/H5/H7 sí escanean desde `cls_b+1` (causal respecto del cierre). Los estratos Q1/Q3 de altura y `AGED/FRESH` dependen de datos finales de la zona; hay que verificar que cada uno esté disponible en el instante de entrada.

**M2. Relleno de órdenes límite optimista.** Los tipos `*_LIMIT` consideran ejecutada la orden en el primer tick que toca el nivel (`t_fill`). Un toque no garantiza fill: la cola y la selección adversa (se llena justo cuando el precio sigue en contra) no se modelan. Los resultados límite (H1, H7, H5: los de z más alto) están sesgados a favor. La regla del repo prohíbe fills imposibles.

**M3. El "exceso vs H9" no es consistente con un nulo de 50%.** En la tabla, H2 25T P2 VIRGIN a 80 ticks gana 58,89% pero el exceso sobre el control es sólo +1,67 pp, lo que implica que el **control H9 gana ≈57%** a 80 ticks. Un control causal "sin información" que gana 57% a 80 ticks sugiere deriva post-cierre de zona o censura por horizonte (sólo carreras resueltas). El reporte sólo muestra H9 en 0,5H/10t/20t/asimétrica, no en 40t/80t, justo donde están los mejores. Hasta publicar H9 en todas las barreras, el exceso real puede ser mucho menor.

**M4. Mezcla de motores.** El titular de 500T `L2_PENETRATION_25PCT` viene del motor **v1**, que el dossier declara con el sesgo de entrada intrabarra (artefacto 1) y con control `b−150` sesgado (artefacto 2). Se compara contra el 50% o contra un control v1 inválido.

**M5. Narrativa "ley de bifurcación" sin prueba.** Las tres "fases" (rebote en el borde, vacío de liquidez, rebote en origen) salen de combinar celdas con distinto punto de entrada, distinta barrera (relativa a la altura de la zona vs ticks fijos) y distinto motor, elegidas por su z. "Atravesar" y "rebotar" son lecturas casi complementarias del mismo evento, así que reportar ganadores en ambos sentidos para geometrías vecinas no es evidencia de dos regímenes. No hubo prueba de interacción ni de estabilidad.

### Menores
- **Hash de manifiesto sin reconciliar:** el diseño y la aprobación usan `db9c42cd…14ce5`; el reporte y el JSON citan `manifest_sha256 = 06d7fb2a…bd84` (no figura en el repo). Puede ser el manifiesto del dataset de Kaggle y no el de la release, pero debe documentarse.
- **"Port 1:1" no verificado:** no hay prueba de paridad numérica Python↔`EmaCorridorTrend.cs` (zonas/barras comparadas con la salida de NT8). Hasta entonces, "1:1" es una afirmación.
- Se afirma "6,52% de barras en zona (v2)" vs "13,08% (v1)": la diferencia es el tope de no-solapamiento, no un detalle; los resultados de v1 y v2 no son comparables sin aclararlo.
- Resultados con N < 100 (1000T, hasta N=56) se presentan como hallazgos.
- Sin espejo, sin corte por régimen horario, sin estabilidad temporal ni por contrato: lo que el propio dossier pide para la Pasada 2.

## Qué haría falta para que esto cuente
1. Manifiesto preregistrado (hipótesis única o pocas, celdas, barreras y fricción) y OK de Nico.
2. Universo completo de celdas y nulos publicado (no sólo los mejores) y multiplicidad con Holm/FDR sobre las ~10.250.
3. Eventos purgados por sesión, SE clusterizado por sesión y MDE.
4. Nulo emparejado por (contrato × media hora) y H9 en **todas** las barreras.
5. Todo escaneo desde `cls_b+1` y toda característica/barrera disponible en el instante de entrada (corregir H8 y estratos de caja final).
6. Fill límite con regla de cola/trade-through, o sólo entradas al cierre.
7. Neto de fricción (y −1 tick adverso), con barreras ≥ 2× fricción.
8. Estabilidad por mitades cronológicas y por los 6 contratos, y espejo largo/corto.
9. Paridad Python↔NT8 verificada.
10. Réplica sellada sin tocar el holdout (≥ 2026-10-01).

## Lo que se puede aprovechar
- Los motores de carreras tick-exact y el control H9 causal son reutilizables para la Etapa 0 de la propuesta de modelo, como etiqueta y como nulo.
- Dos pistas, sólo como candidatas para un preregistro (no como hallazgos): H2/H3 cerrado con barreras largas (≥ 40 ticks) en 25T–100T, y H7 en 100T con zonas de alto puntaje. Ambas con las condiciones 1–8 de arriba.

## Límites de esta auditoría
Revisé el reporte, el JSON consolidado, el log crudo de v2, el dossier y las partes del script que construyen eventos y estadísticos (`evaluate_all_hypotheses_numba`, `summarize_event_matrix`, `binom_z_p`, cargador). **No** leí el detector de zonas ni las funciones de carrera, **no** recalculé desde los ticks, **no** ejecuté nada en Kaggle y **no** pude ver el universo completo de celdas (no está en los archivos). Los netos de fricción son cuentas simples con la fricción medida en R2 y el supuesto de ±D simétrico, sin tiempo de espera.
