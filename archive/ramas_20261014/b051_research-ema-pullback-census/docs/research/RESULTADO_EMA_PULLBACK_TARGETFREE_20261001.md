# Retroceso EMA20 multi-activo — censo target-free terminado

## Resultado y decisión

**Kaggle v3 COMPLETE. La regla congelada selecciona TF1min para MNQ, RTY y YM por frecuencia, NO por ganancias.** En cada activo, mediana6intenciones/sesión; TF5 tiene mediana2 y no alcanza el mínimo4. El gate de frecuencia se cumple; utilidad, costos, ejecución y potencia estadística real todavía NO MEDIDOS.

| Activo | Sesiones | Intenciones 1min | Media/sesión | Mediana/sesión | Subconjunto separado |
| --- | ---: | ---: | ---: | ---: | ---: |
| MNQ | 154 | 878 | 5.70 | 6 | 791 |
| RTY | 175 | 975 | 5.57 | 6 | 871 |
| YM | 177 | 984 | 5.56 | 6 | 889 |

Los conteos son intenciones reservadas (31min entre slots), no trades llenados, aciertos ni ventaja. El filtro separación≥0,25TR20SMA deja respectivamente791/871/889intenciones, mediana5en cada activo. Son subconjuntos correlacionados de BASE, sin reprogramar slots: no sumarlos como otra muestra independiente. No se eligió el filtro por beneficio.

## Las seis celdas y la población

| Activo / TF | Intenciones | Media/sesión | Mediana/sesión | Sesiones activas/elegibles | Gate frecuencia |
| --- | ---: | ---: | ---: | ---: | --- |
| MNQ|TF1 | 878 | 5.70 | 6 | 154/154 | PASS |
| MNQ|TF5 | 333 | 2.16 | 2 | 145/154 | NO_SUPPORT |
| RTY|TF1 | 975 | 5.57 | 6 | 175/175 | PASS |
| RTY|TF5 | 399 | 2.28 | 2 | 167/175 | NO_SUPPORT |
| YM|TF1 | 984 | 5.56 | 6 | 177/177 | PASS |
| YM|TF5 | 411 | 2.32 | 2 | 170/177 | NO_SUPPORT |

Toda sesión elegible de cada activo entre20251007 y20260630 según catálogo congelado:154/175/177, no intersección común. Dataset canónico privado v1 no incluyeES; sigue diferido, sin sustituirlo silenciosamente porYM ni atribuirle resultados deYM. Los tres son índices correlacionados y no tres réplicas independientes.

Esta población es DEVELOPMENT previamente expuesto, NO OOS ciego. Sin outcome-based exclusion ni recalibración. Holdout general20260701+ cerrado. Ficheros09-26 descargados/hasheados enteros por custodia pueden incluir bytes sellados; escaneo de precios del estudio limitado antes del corte. MNQ154 no alcanza mínimo160 de componente formal; RTY/YM>=160 tampoco aprueban G2 sólo por tamaño. No PBO/DSR/WF/edge acreditado.

## Regla congelada

EMA20/50/200 sobre barras1/5min, warmup600barras reales y hasta siete días calendario previos, reset contrato. Tendencia de barra anterior:EMA20>EMA50 y cierre>EMA200, inverso short. Referencia EMA20 anterior, no actual/intrabar. Armado tras una barra intacta del lado favorable; tocar y recuperar por cierre, same-bar reclaim permitido. Una emisión por episodio, máximo10barras; reset gaps/tendencia/fecha; rearmado posterior. Horario10ET–cierre14:45ET. U=TR20SMA estrictamente anterior sobre20barras consecutivas, en ticks. Reserva1860s para slots, no posiciones.

TF5 preferido si>=200intenciones, mediana>=4/sesión y actividad>=80%; elseTF1 si mismo gate; elseSTOP sin relajar. TodosTF1pasan con100%fechasactivas. TF5no pasa por mediana2 aunque la actividad sea alta. Base primero, separación como subset sin reschedule.

## Procedencia y errores conservados

Kaggle privado nicolasbuttaro/edgelab-ema-pullback-census-20261001, kernel136606905. V1 mountausenteERROR antes de datos. V2 recorre24combinaciones archivo/TF pero ERROR al serializar un flag NumPy, sin censo/ledger final. V3 cambia sólo castbool() del resumen y hashes/código/documentación correspondiente; `detect()` exacto idéntico. Nueve tests dirigidos PASS incluida regresiónJSON true/false; no fullsuite. Conteos de las24combinaciones de v3 son idénticos a logv2, no mejora seleccionada.

V3 DONE a257,78s (aprox4,3min incluyendo descarga), luego nbconvert. Las advertencias de nbconvert posteriores no son fallas del censo. No usar timestamp de metadata Kaggle para certificar reloj.

Manifiesto original3409f5c3… conservado; enmienda previa a v3 y manifiesto462928c6e045ed05cd98051d5b3dfab11d8d2afd81ae7a379945dd98d90a055f registrados en Notion antes del nuevo censo. Fuente exacta privada v3 verificada. Runner801b066bfb09416982e6d45f87ba1800551415f278219789221eb41a84f46724. Base nativa foundation391314907dec889599493c4a38282171d94a2f25.

## Auditoría realizada y límites

Preflight/custodia/manifiesto verificados antes de leer el censo. Doce hashes fuente contraEXPECTED congelado; manifiesto retornado byteigual local. Veinticuatro perfiles de barras reconcilian ticks del catálogo.72prefijos muestreados PASS (tres por archivo/TF), no prueba independiente exhaustiva de todo raw.

Ledger privado3.980filas, clave compuesta única, cero duplicados/nulls, Upositivo, signos±1 y episodios1–10. Recuento independiente directo por fecha y pandasgroupby reconcilian seis celdas, contratos, meses, medias, medianas, slots separados, horarioET, reservas y selección fija. Signals timestamps repetidos entre activos/TF son legítimos, no filas duplicadas. `day` es textoYYYYMMDD, no medida numérica aunque el profiler lo infiera así. Medianas no se promedian ni agrupan entre activos.

QA escalar independiente anterior sobre una sesiónRTY, dosTF:EMA/TR20/U/condiciones y seis prefijosPASS; no certificar detector completo independiente. Registro bookkeeping completo del ledger no equivale a replay raw independiente.

LedgerSHA028fb739bb33e6a72f6c9104676b59eb707fb559332a07a8fb1c1adc285b8cf4; censoSHA84cc3b90e894f0f098f8c9c82707fd41aed97ab3e3d9165a698ed4b82fc317d6. Evidencia/auditoría agregadas públicas; raw, productor/catálogos embebidos privados, URLs firmadas y ledger reservado no se publican.

NO MEDIDO/certificado:quote entrada/salida observable, fills/quoteage/reloj, comisiones reales, rentabilidad, controles predictivos, modelos o MDE/potencia real. Outcomesfalse, modelos0, holdoutfalse. Frecuencia no convierte una estrategia en edge.

## Siguiente gate

Congelar manifiesto económico antes de abrir retornos: salida fija, costos nativos+stress, controles emparejados por horario/tendencia/volatilidad, exposición/particiones e inferencia por sesión con presupuesto de búsqueda acumulado. No elegir salida o filtro por PnL; no abrir holdout para rescatar. Tras aprobación conforme a guardas, evaluarBASE y separación sin adjudicar al censo un resultado económico.

Acta+código/evidencia+MEDIDO en misma rama research/ema-pullback-census-20261001, sinmerge. Este resultado reemplaza estadoRUNNING como estado actual pero conserva errores históricos.

Aporte al referente: la mecánica nueva tiene unas5,6intenciones por sesión a1min, suficiente para continuar verificando ejecución y utilidad; aún no sabemos si paga los costos ni aporta ventaja estable.
