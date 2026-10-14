# GC A/E causal history — corrida terminada, primarios sin soporte

**PRIMARY_INCONCLUSIVE_NO_DIRECT_TRANSITION_SUPPORT**, no edge confirmado ni ausencia física de mecanismos. Kernel138580854/v1 COMPLETE; dos polls/una intención cerrada. Fuente24d8c461/bundle9ecfe10a/plan3abcfe6990fa; reciboSHA199d036eb1e0fe77584e0134e75d9be5fce954b83f7be2136a33896fb39a7774. Auditor independiente de agregados PASS; no recomputación del tape privado.

## Qué se obtuvo realmente
- 1.664.049 ticks GC entre training/evaluación;6sesionestrain originales,9evaluables de10 pedidas. Sept24 vacío, sin reemplazo.
- 101.082 anclas observadas antes de labels en evaluación;53.844 anclas comunes puntuables. No son operaciones ni oportunidades/episodios independientes.
- A_ONLY:2anclas (y2en training), E_ONLY:3.809, BOTH:0, NEITHER:64.400, UNKNOWN:32.871. UNKNOWN permanece en el denominador de observación, no en el scoring.
- Cero transiciones directas A→E/E→A, antes de labels en train y evaluación; cero soporte para ambos primarios y sensibilidad60s. Las deltas primarias son null, no0/mejora/fracaso de mercado.

## Interpretación científica
La conjunción estricta A definida/calibrada produce casi ningún soporte en este bloqueGC; no alcanza para estudiar la trayectoria. No sabemos por este recibo qué conjuncto falla (presión actual/prior, avance neto, rango, camino), ni podemos atribuirlo sólo a transporte de calibraciónJul31. Aumentar configuraciones de zonas no soluciona la ausencia de un estado proxy observable. Transición directa significa estadoA yestadoE en anchors consecutivos, misma dirección y continuidad; trayectorias con NEITHER intermedio no fueron ese primario y no deben contarse ahora como rescate posthoc.

## Diagnósticos secundarios — no rescatan primarios
ΔBrier×1000, positivo=peor; medias por sesión sobre la misma población común, NO pooled:

| Representación | Proxy−HISTORY | Proxy−CAPACITY | Sesiones mejores que HISTORY | Sesiones mejores que CAPACITY |
|---|---:|---:|---:|---:|
| Estado | +0,036793 | +0,044769 |4/9|3/9|
| Duración | +0,235053 | +0,203004 |4/9|3/9|
| Combinado | +0,239996 | +0,103459 |5/9|5/9|

No mejora media frente a amboscomparadores. El combinado sí mejora en5/9sesiones, pero la media es peor; rango de sus deltas contraHISTORY−0,373944…+1,330347. No describir empeoramiento en todas las sesiones o significancia; los efectos medios son inferiores en magnitud al margen práctico1Brier×1000.14representaciones conservadas enreceipt, incluyendo ceros porfeatures de transición constantes. CSV por sesión/familia en `GC_AE_HISTORY_SESSION_ABLATIONS.csv`.

## Tiempo y eficiencia
Runner68,947327s;host78,619451s incluyendotransporte7,734948s. Medición61,207733s,fit3,385261s,score2,118867s;RSSchildmuestreado434.094.080bytes. No speedup contra otra campaña: fechas,detectors/objetivos/poblaciones distintos. Se reutilizó calibraciónGC yuna pasada común de features/labels; no se ejecutaron detectoresnativos innecesarios a la pregunta. No nueva datasetQA o calibración.

## Siguiente hito útil
Diagnóstico **científico de soporte, sin outcomes** sobre eltrainingya fijado:frecuencia de cada conjunctoA/solapamiento y componentescontinuos,coverage,phase/direction,distancia respecto a calibración. No auditoría repetida deldataset. Sólo después diseñarproxy de actividad alta con pocarespuesta relativa ytrayectoriascon estadosintermedios explícitos. Nuevo plan propioantesdenuevosoutcomes; evaluacionesactuales ya inspeccionadas,no holdout virgen. No grid expansiva ni modificación delplan3abcfe para ganar soporte. Propuesta guardada NO canónica.

## Custodia y límites
Journals originales `/data/operational-state/gc-ae-history-3abcfe6990fa-{dispatch,watch}.sqlite`,terminalesCOMPLETE,2/6polls. No reset/reenvío/nuevointento sobre mismo journal. Pasaron954ResearchOps/18navegación y21focal antes de lanzar;auditorposterior sólorecibosagregados. La comparación de NT8no se certificó;holdout/P&L/canonicalwriter/merge/daemonDebian/24x7cerrados. URLfirmadadefuente permaneceen notebookprivadoyexpira72h;noURLfirmadaenrepo.
