# AVZVOL: qué evidencia orienta lógicas de entrada

## Conclusión práctica de investigación

**Usar la zona como ubicación/contexto y estudiar qué hace el precio después, no entrar automáticamente porque aparece o porque retestea.** La primera hipótesis a investigar es **retest + confirmación observable de rechazo/aceptación**, enfrentada a **reentrada confirmada al rango** como explicación rival. Es prioridad de discriminación de triggers, **no recomendación operativa ni regla más rentable**.

La evidencia disponible no descubre un setup fuerte de entrada:

- El retest es muy frecuente tanto en reales como en pseudo: por sí solo no distingue una oportunidad.
- Después del retest, alcanzar primero una barrera geométrica hacia la salida u otra hacia el interior está cerca de mitad y mitad, sin mejora general frente al control.
- Combinar mecánicamente tendencia y momentum alineados con la salida **no** mejoró el contraste O2 de los exports en ese corte. No elegir el corte contrario sólo porque arroja mejor gap.
- Rango relativo, dirección de salida, continuación y comportamiento posterior al retest son preguntas diferentes. No convertir ninguna en P&L o tasa de trades ganadores.

## Datos revisados y semántica que importa

Se analizaron O3a/O3b ya exportados, junto con identificadores y signos previos; no ticks/precios crudos, nuevo detector, nuevas etiquetas desde precios o simulación de operaciones. Los seis hashes/footers y la fuente histórica fijada se verificaron antes del payload. Plan antes de leerlo, sin claim de ceguera o preregistro: las familias se escogieron tras la revisión previa expuesta.

**O3a:** tras la salida observada, un low toca o atraviesa el borde superior si salió arriba (o high el inferior si salió abajo), dentro de hasta 2.000 barras posteriores de la sesión. Eso no exige rechazo, cierre favorable, límite ejecutable, ni que el retest llegue antes de otra excursión. **No es necesariamente un test limpio del nivel.** Ausencia registrada está limitada por ventana/sesión/archivo, no ausencia para siempre.

**O3b:** a partir de la barra *posterior* al primer retest, qué se toca antes: `edge + dir*h` o `edge - dir*h`, con `h=H-L+1`, otra ventana de hasta 2.000 barras de la sesión. No analiza la barra del retest, no conserva el precio de entrada, el tiempo del retest ni un trigger de rechazo. Si ambas barreras se tocan en una misma barra posterior, código −2; si no se resuelve, −1. **No hay fills, costos, stops, órdenes ni rentabilidad calculados.** Llegar a una barrera medida desde el borde no equivale al mismo recorrido desde un precio real de entrada.

## 1. Retest y rebote: una interacción común no es una señal discriminante

Población especialmente pertinente para estudiar una ruptura nueva: **ancla dentro de banda (`pos=0`)**, condición previa al outcome. Se publica aparte, sin reemplazar el universo original.

Con igual peso por sesión soportada, 31 celdas comunes y seis contratos:

| Desenlace | Reales | Pseudo legacy | Diferencia real−pseudo |
|---|---:|---:|---:|
| Retest observado entre salidas registradas | 98.6008% | 98.9030% | -0.3022 pp |
| Barrera hacia salida primero, sólo retests resueltos no ambiguos | 49.0022% | 49.6734% | -0.6712 pp |

Universo legacy completo, incluidas anclas ya fuera de banda: retest **98.4916% vs 98.3475%**; rebote resuelto **49.1699% vs 49.2012%**, gap **-0.0313 pp**. No ocultar que restringir anclas cambia el estimando.

Tasas reponderadas, no proporciones pooled ni probabilidad out-of-sample. No implica que 98,6% de rupturas sean falsas: un retest puede ocurrir después de una excursión favorable, y su ventana es larga en barras, no fija en segundos.

### Excepciones por contrato: no elegir ganador

| Contrato | Barrera salida primero, real | Pseudo | Gap (pp) |
|---|---:|---:|---:|
| MNQ_09-25 | 52.3015% | 50.5661% | +1.7353 |
| MNQ_12-25 | 50.2171% | 49.7076% | +0.5095 |
| MNQ_03-26 | 45.7281% | 48.2023% | -2.4742 |
| MNQ_06-26 | 49.0919% | 49.2450% | -0.1531 |
| MNQ_09-26 | 49.7943% | 49.4013% | +0.3930 |
| MNQ_12-26 | 46.8802% | 50.9182% | -4.0381 |

MNQ_09-25 tiene +1,7353 pp; MNQ_12-26 **−4,0381 pp** y MNQ_03-26 **−2,4742 pp** en esta población. En la revisión anterior MNQ_12-26 tenía mayor coincidencia tendencia–salida: eso no se transforma automáticamente en mejor oportunidad después de retest; son outcomes y poblaciones distintas, no una contradicción estadística. Se preservan todos los contratos/celdas.

En el diagnóstico exacto de horario/signo de tendencia, el rebote da **-1.1395 pp** en **28** celdas comunes. Misma población de solapamiento sin reponderar estratos: **−0,8243 pp**. No comparar directamente con las 31 celdas como si fuera efecto corregido causal; el soporte cambia y sigue sin control zone-free certificado.

## 2. ¿Tendencia + momentum sugieren perseguir la ruptura?

Se declaró un corte sencillo, sin umbrales elegidos por resultados: al momento hipotético de **salida confirmada**, su dirección ya puede ser observable; se contrasta con los signos de tendencia previa de 500 barras y momentum previo de 100. **`dir` es futuro e inadmisible como feature al ancla original**, aunque se conozca después de completar la barra de salida. Los signos son los exportados en el **ancla original**, no indicadores recalculados al salir; son conocidos pero pueden estar desactualizados para el nuevo trigger. Todos los cuatro estados se conservan:

| Contexto conocido tras salida | Filas real / pseudo | Celdas comunes O2 | Gap continuación O2 (pp) | Celdas comunes rebote | Gap rebote (pp) |
|---|---:|---:|---:|---:|---:|
| BOTH_ALIGNED | 28,200 / 108,148 | 30 | -2.2495 | 30 | -1.5763 |
| BOTH_OPPOSED | 13,805 / 71,054 | 27 | -1.0750 | 27 | -1.9502 |
| MIXED | 31,088 / 159,175 | 30 | +1.2106 | 30 | -1.2167 |
| NEUTRAL_OR_ZERO | 1,537 / 7,426 | 11 | +1.8512 | 11 | -4.2660 |

`BOTH_ALIGNED`: ambos signos previos coinciden con la salida. `BOTH_OPPOSED`: ambos se oponen; `MIXED`: uno a favor y otro contra; `NEUTRAL_OR_ZERO`: alguno cero. Sólo anclas inicialmente dentro de banda y salida observada; las filas no son eventos independientes. Distintos soportes y poblaciones por estado y endpoint; **no ordenar estos gaps como rendimiento de estrategias**. El estado neutral sólo soporta 11 celdas: no promover su O2 positivo.

En BOTH_ALIGNED, O2 real es **13,1191%**, pseudo **15,3685%**, gap **−2,2495 pp**; rebote gap **−1,5763 pp**. Por tanto, *tendencia + momentum del mismo lado* no queda acreditado como filtro que mejora la zona. Los otros cortes positivos de O2 no autorizan invertir la señal ni elegirlos como ganador. Hay exposición previa, múltiples celdas, censura, controles no equivalentes y dependencia.

## 3. Tiempo de decisión: no confundir conocer la zona con conocer la salida

Mediana de demora desde ancla inicialmente dentro de banda a salida registrada, reales, **barras de 25 trades** (no segundos). Se deriva de índices ya exportados, con cuantiles recomprobados por ordenamiento/listas independientes:

| Contrato | Filas con salida | Mediana barras | P90 barras |
|---|---:|---:|---:|
| MNQ_09-25 | 7,682 | 9.0 | 49.0 |
| MNQ_12-25 | 14,799 | 10.0 | 47.0 |
| MNQ_03-26 | 13,198 | 8.0 | 41.0 |
| MNQ_06-26 | 14,437 | 8.0 | 37.0 |
| MNQ_09-26 | 19,997 | 8.0 | 39.0 |
| MNQ_12-26 | 4,517 | 9.0 | 48.0 |

Medianas entre 8 y 10 barras; no imponer un temporizador de 8/10 barras a partir de estas medianas. La duración real varía; no están exportadas la barra/UTC del retest, reentrada ni confirmación de rechazo. Faltan para evaluar entradas que ocurran allí.

## 4. Qué lógica de entrada merece estudiar y qué sería observable

| Hipótesis, NO regla aprobada | Momento de información | Trigger conceptual a registrar | Qué tenemos / qué falta |
|---|---|---|---|
| H1: salida confirmada con contexto | Después de completar el cierre fuera de banda congelada | Salida por un borde; contexto previo fijado, no dirección futura al ancla | O2 y dirección ya expuestos; no ventaja general validada, falta precio/tiempo de nueva decisión y comparación limpia |
| H2: retest + rechazo/aceptación observable | Después del retest y de completar nueva confirmación | Distinguir tocar el borde de volver a cerrar del lado de salida o aceptar de nuevo el interior | Retest común y barreras futuras disponibles; **no está el trigger de rechazo** ni su timestamp/snapshot. Primera pregunta a investigar, no evidencia de rentabilidad |
| H3: ruptura fallida + reentrada confirmada | Sólo al observar el cierre nuevamente dentro | Estado de vuelta al rango frente a continuación, sin entrar contra una ruptura aún activa | O2=0 acredita un retorno antes de un umbral geométrico, pero no trayectoria desde una entrada nueva ni resultado hacia borde opuesto |

No se han escogido buffers, número de cierres, volumen mínimo, temporizador, stops, objetivos, fills o costos. [Registro de hipótesis](../../config/research/avzvol_entry_hypotheses_v1.json): PROPOSED_UNVALIDATED, parámetros null, gates científicos intactos. H2 debe competir con H3 y H1 de referencia; no desarrollar H2 mirando qué versión maximiza un backtest.

**Qué NO hacer:** comprar/vender automáticamente al aparecer la zona, al tocarla, por `dir` futuro, por O5 negativo, o porque un retest ocurre con frecuencia; tampoco invertir a contrarian tomando 1−O2 como tasa de operaciones ganadoras.

## 5. Fuentes externas: mecanismos que motivan hipótesis, no evidencia transferida

- Osler estudió soportes/resistencias suministrados por seis firmas de divisas: encontró capacidad de anticipar interrupciones intradía, con variación por firma y moneda. Motiva examinar interacción con niveles, no asumir que nuestros racimos MNQ replican ese resultado.[^https://www.newyorkfed.org/research/epr/00v06n2/0007osle.html]
- Otro trabajo de Osler, sobre órdenes stop-loss/take-profit en un banco de FX, relaciona patrones diferentes de agrupación de órdenes con reversión en niveles y momentum tras atravesarlos. Motiva separar **rechazo** de **ruptura aceptada**, no etiquetar cada zona siempre como soporte o siempre como acelerador. Nuestros racimos de volumen ejecutado no acreditan esas órdenes ni el mismo mecanismo.[^https://www.newyorkfed.org/research/staff_reports/sr125.html]
- Cont, Kukanov y Stoikov relacionan cambios de precio de corto intervalo con desequilibrio de flujo de órdenes en mejor bid/ask y profundidad, en 50 acciones estadounidenses. Motiva investigar confirmación direccional de flujo **si se dispone de la cinta necesaria**, no usar volumen total como dirección.[^https://arxiv.org/abs/1011.6402] OFI de libro incluye eventos de órdenes/cancelaciones y no equivale al delta de trades ni a precios bid/ask aislados; esa medición y la calidad/as-of del agresor no están acreditadas aquí.

La búsqueda pública fue acotada a estas fuentes de mecanismos; no exhaustiva de toda literatura/estrategia, ni prueba de beneficio en futuros. Se cargaron los originales, no se usaron snippets como certificación. Se revisaron antes las fuentes del proyecto sobre endpoints, controles y temporalidad. Las referencias antiguas a lecciones de memoria histórica no están materializadas en el árbol actual y no se usaron como nuevos resultados.

## Censura, ambigüedad y accounting

| Población/tipo | Filas | Sin salida | Retests observados | Ambas barreras misma barra | No resuelto tras retest |
|---|---:|---:|---:|---:|---:|
| all_legacy_anchors / real | 96,755 | 85 | 95,267 | 0 | 449 |
| all_legacy_anchors / pseudo | 447,776 | 202 | 440,608 | 11 | 1382 |
| inside_band_anchors / real | 74,711 | 81 | 73,709 | 0 | 341 |
| inside_band_anchors / pseudo | 345,995 | 192 | 341,723 | 8 | 1077 |

Los códigos ambiguos y no resueltos no se convierten a fracasos ni éxitos. Bounds adversariales del gap de rebote, sobre los exactos grupos soportados del endpoint y todas sus filas con retest: **-1.2231 a -0.2420 pp** para anclas dentro de banda; para universo completo, **−0,7192 a +0,3965 pp**. No CI ni resolución de sesgos upstream o no salida. Cero casos ambiguos reales registrados **no** valida orden temporal intrabar, punto de entrada o detector; la barra del retest fue excluida por diseño histórico.

## Siguiente información que realmente necesitamos

1. Bandas/snapshots de formación disponibles as-of, calendario/reloj/warmup acreditados y censo de controles zone-free de consolidación (P1/P2). Hay 412 pseudo que también aparecen como anclas reales en la misma celda; no borrar sólo esas filas y declarar limpio el resto.
2. Cinta de estados de interacción con la banda: UTC/barra de salida, retest, cierre de rechazo/aceptación y reentrada, incluido UNKNOWN, sin usar membresía final del racimo ni desenlace futuro para definir la candidata.
3. Covariables **al momento de cada trigger**, no sólo al ancla antigua: dirección/actividad/momentum/duración/localización. Calipers, soporte y balance fijados antes de medir efectos; la diferencia previa en volumen100 no es un predictor por sí sola.
4. Congelar la predicción no económica que cada estado hace y comparar H1/H2/H3 contra situaciones equivalentes sin zona y contra el censo propio del control, con horizontes de reloj y censura (P3). Para H2, O3 histórico no sustituye el endpoint desde la confirmación nueva.
5. Sólo si sobrevive y con nueva autorización explícita, una evaluación económica congelada (P4). Esta solicitud busca orientar lógicas: **no habilita ahora P&L, simulación de posiciones, promociones ni holdout**.

## Evidencia y reproducción

[Plan](avzvol_entry_hypotheses_20261011/analysis-plan.json), [evidencia completa con fuentes](avzvol_entry_hypotheses_20261011/evidence.json), [todas las celdas](avzvol_entry_hypotheses_20261011/all_cells.csv), [receta](../../tools/review_avzvol_entry_hypotheses.py). CLI: inventario de seis exports, fuente histórica fijada, `--out-dir` nuevo, `--allow-exposed-entry-hypothesis-review`. Agregación revisada/importada del helper descriptivo, no del runner histórico. SHA de helper/receta en evidencia; seis pins y fuente histórica antes de payload. Medias, conteos, bounds y cuantiles contrastados independientemente.

[Dirección y continuación](AVZVOL_DIRECCION_Y_CONTINUACION_20261011.md), [comparabilidad sin outcomes](AVZVOL_CONTROLES_COMPARABILIDAD_20261011.md), [mapa candidato](AVZVOL_MAPA_Y_DECISION_20261011.md). No calidad certificada, matching causal, inferencia formal, nuevos outcomes desde precios ni económicos. Publicación añade referencias externas y hash de receta sin cambiar resultados privados originales. La carga de gráficos al chat sigue fallando sin archivo válido; tablas y CSV conservan la lectura, sin URI inventada.
