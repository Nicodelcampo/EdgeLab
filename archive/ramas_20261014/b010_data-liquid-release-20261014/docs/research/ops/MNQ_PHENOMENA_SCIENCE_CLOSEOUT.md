# Cierre científico de desarrollo: estados A/E y respuestas MNQ

**COMPLETE, no edge ni identificación de mecanismo.** PrivadoCPU `nicolasbuttaro/edgelab-mnq-phenomena-response-pilot`, id138417158/v1, source`ed82301d4c884ac73e84e5d32142882dd90b13ea`. Plan/bundle/source y hash físico del science receipt vinculados; conteos por estado y por fase×dirección crossfootPASS. No lectura/recuento independiente de filas privadas. Split fijo June12calibración / June15-16evaluación; feature development previo ya inspeccionado, no holdout virgen.

## Resultado nuevo

4.262.580ticks incluyendo train,29.473anclas de evaluación,24,70s host(incluye8,41s retrieval),13,92s runner(tiempos anidados, no sumarlos).38.539.778elementos escaneados vectorizados en respuestas; no producto configs×escenarios. Peak runner756.396.032bytes de ese proceso, sampledchild756.879.360bytes otra medida; no cgroup/24×7 ni ratio de speedup contra otra carga.

Calibración congelada sólo con2.946anclas elegibles June12: RTH−1351/RTH+1344/OTHER−144/OTHER+107; las4celdas cumplen mínimo100 de ingeniería, no potencia independiente. UNKNOWN/NEITHER separados. Gates P0 preservados y cobertura signo80% adicional sólo para clasificación.

| Estado | Anclas | Respuestas utilizables | Censura/origen desconocido | Continuación | Reversión | Sin pasada observada |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A_ONLY | 88 | 78 | 10 | 22 | 31 | 25 |
| E_ONLY | 654 | 472 | 182 | 169 | 163 | 140 |
| BOTH | 4 | 4 | 0 | 0 | 2 | 2 |
| NEITHER | 14080 | 11787 | 2293 | 4489 | 4811 | 2487 |
| UNKNOWN | 14647 | 0 | 14647 | 0 | 0 | 0 |

Respuestas utilizables=primer cruce temprano observado antes de censura, o horizonte completo sin pasada observada. No exigir horizonte completo después de cruce resuelto. EOF/gap/contexto/quote desconocidos nunca son sin-pasada. UNKNOWN de estado no es ausencia A/E; ninguna comparación elimina esas14.647anclas del censo. Son anclas solapadas, no episodios/trades independientes. Controles y estados no son muestras intercambiables.

## Cambios de signo que un pooled escondía

| Sesión | A_ONLY reversión / utilizable | E_ONLY reversión / utilizable | NEITHER reversión / utilizable | A−NEITHER(pp) |
| --- | ---: | ---: | ---: | ---: |
| 2026-06-15 | 17/50(34.00%) | 79/239(33.05%) | 2023/4933(41.01%) | -7.01 |
| 2026-06-16 | 14/28(50.00%) | 84/233(36.05%) | 2788/6854(40.68%) | +9.32 |

A_ONLY pasó de34%reversión enJune15 a50%enJune16; comparadorNEITHER≈41,01%/40,68%. No hay ventaja descriptiva uniforme, y sólo50/28respuestas A observables por fecha. PooledA31/78reversiones(39,74%) vsNEITHER4811/11787(40,82%) NO prueba equivalencia, ausencia de efecto o ventaja ajustada.

E_ONLY:169continuaciones vs163reversiones sobre472utilizables(35,81% vs34,53%); no predomina reversión en este resumen. Censura27,83% de E vs11,36%A y16,29%NEITHER: tasas condicionales de poblaciones con distinta observabilidad, no tasas del mercado completo. BOTH4anclas, sólo primera fecha; insuficiente, no extrapolar50%por2casos.

A también cambia la fracción sin pasada observada:21/50(42%) enJune15 vs4/28(14,29%)enJune16; NEITHER1078/4933(21,85%) y1409/6854(20,56%). La continuación A12/50(24%) vs10/28(35,71%) tampoco se interpreta como efecto independiente. No ocultar la respuesta sin pasada para convertir todo en reversión/continuación forzadas.

## Qué representa A realmente

A requiere progreso neto≤2ticks, presión alta relativa al train y range/path≤q25 del train. Los caps reales son33–56,5ticks de rango y138–283,5ticks de recorrido según celda: **confinamiento relativo, no precio quieto**. Todavía permiten excursiones no triviales. No afirmar iceberg/reposición pasiva ni apretar ahora caps por haber leído resultados. Cualquier nuevo proxy sería otro intento explícito y no confirmación con estas mismas dos fechas.

Orientar por flujo previo puede introducir regresión a la media; E exige impulso+presión previa alta y caída presión Y frecuencia, pero eso no elimina sesgos. Fuente sólo trade/bid/ask, sin profundidad/MBO. Barriers trailing60s varían por anchor y no están igualadas entre grupos; no adjudicar diferencias a A/E sin baseline continuo/control de contexto.

## Controles sin zonas, sin matching causal

Tags de control pueden solaparse con estados/otros tags; no sumar como poblaciones independientes.

| Tag | Anclas | Utilizables | Reversión | Continuación | Sin pasada |
| --- | ---: | ---: | ---: | ---: | ---: |
| LOW_PRESSURE_SMALL_NET | 103 | 29 | 9 | 18 | 2 |
| DECAY_WITHOUT_PRIOR_IMPULSE | 334 | 193 | 93 | 72 | 28 |
| PRIOR_IMPULSE_NO_JOINT_DECAY | 6688 | 6309 | 2437 | 2181 | 1691 |
| HIGH_PRESSURE_PROGRESS | 3697 | 3605 | 1293 | 1183 | 1129 |
| HIGH_PRESSURE_EXCURSION_RETURN | 455 | 442 | 173 | 170 | 99 |

LOW_PRESSURE_SMALL_NET sólo29de103observables: ejemplifica sesgo de cobertura, no control bien igualado. HIGH_PRESSURE_EXCURSION_RETURN tiene173reversiones/442observables(39,14%), parecido al A pooled bruto, pero no efecto comparable por sí solo. Todos los counts por sesión y por fase×dirección quedan en ANALYSIS/RECEIPT; no valores privados individuales.

## Aprendizaje propuesto, siguiente hito y límites

- Se puede medir, clasificar y obtener respuestas con rigor causal de features sin ejecutar miles de detectores. Preservar registros/UNKNOWN/censura/negativos antes de buscar configuraciones.
- Este desarrollo NO respalda la regla “absorción/exhaustion⇒reversión”. Eso es límite de este piloto, no falsificación universal ni equivalencia con suficiente potencia.
- Próximo hito útil: evaluación en más sesiones de research disjuntas del ajuste, baseline continuoM1 con actividad/fase/dirección/rango/path/barrier/observabilidad y representaciónM2, ponderación por sesión/episodio, purge/embargo y mínimos de precisión previos a inferencia. No nuevosumbralesvariantes elegidos por estas respuestas.
- Después, interacción/llegadas AVZP2/racimo/BT2/BT2A contra geometría/densidad/ocupación comparable. Densificar zonas no reemplaza soporte independiente ni controles. No reabrir V3fallida para producir este resultado.

No M2−M1 ajustado, CI/MDE/p-values/FDR, P&L/holdout, modelos ni escritores canónicos en este piloto. Lecciones scoped conservadas como propuestas revisables, NO autoappend al EdgeBrain canónico. Tests812ResearchOps+18nav y57focalesPASS. No pipeline/daemonDebian desplegado; un solo envío manual finito.

## Recuperación

Intención1pre-send→ACK→COMPLETE y watchconsulta1/4 preservados. Ancla pública anterior10consultas; esta línea manual suma11consumidas y máximo14 con el batch, no auditoría de otros agentes ni cuota global. No resetear/reconstruir journals viejos como latest. Todos los jobs de este hilo quedaron cerrados. Fuentes/ticks/labelsprivados no salen deKaggle; sourceURLfirmada sólo en notebook privado, expira72h.

Perfil: JSON anidado no convertible a tabla por profiler; CSV10filas sesión×estado, sin duplicados. Nulos de tasas son cero denominadores(UNKNOWNyBOTH vacío), no cero tasas; fechasISO son categorías cronológicas, no dospuntos para inferir tendencia. Hints de promedio diario no se usan como tasa de muestras independientes. No drops/imputación de mercado.

## Reproducir sólo agregados

`python -m tools.research_ops.audits.review_phenomena_science --out-dir /tmp/phenomena-science-review` reproduce CSV/evidence/chart spec desde los recibos limpios publicados, chequea hash/plan/conteos y conserva denominadores/censura. Sin red, carga de labels privados, modelos, journals ni escrituraBrain. Los checks no autentican el proveedor a partir de JSON solos. Revisión independiente de counts por fase×dirección coincide con estados por sesión; soporte no se transforma en n independiente.
