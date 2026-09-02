# EdgeLab — cronología consolidada

Corte: 2026-09-02. Reconstruida desde los registros de ramas del 24 y 28 de agosto, los 60 tips remotos observados, `PENDIENTE.md`, los handoffs y los artefactos del 1–2 de septiembre.

## 1. Fundación portable — 21 a 23 de julio

`main@cde6d93` preservó la baseline portable. `backup/foundation-f0b-local` y `preserve/f0b-local-divergente-2026-08-04` conservan el snapshot `a48efcd`. Estas refs son origen histórico o backup, no ramas de trabajo.

## 2. Arquitectura científica y primeras hipótesis — 4 a 9 de agosto

Aparecieron el gate mínimo de sesiones, las iteraciones multimodelo y el rechazo de `IndicatorSpec v0` como listo para implementar. Se registraron HP-001…HP-004: burst HFT al cierre en ES; rescate del estimador P²; aVolClusterPOI como candidato distinto; descarte de aVolZonePOI por irreproducibilidad.

## 3. Corrección de procedencia y contratos — 10 a 15 de agosto

Se alineó el estado real del repo, se documentó el incidente de procedencia y nacieron ramas de LUX, YM, G2 y BigTrap2. El fix BigTrap2 v2.5.2 corrigió timestamps de exportación y drenaje de cola. Las líneas de nulos de BigTrap2 maduraron hacia desplazamiento local. La auditoría del 15-ago dejó el diagnóstico rector: proyecto fuerte para no engañarse, todavía débil para producir expectativa económica neta. También quedó registrada exposición previa a outcomes; nunca resumir el estado global como `OUTCOMES_NOT_OPENED`.

## 4. Expansión de familias y consolidación BT2Absorption — 16 a 24 de agosto

Se abrieron o documentaron H-Z2A, HFTZones, GEX, rango Asia, L2 y contextos. BigTrap2Absorption pasó a ser línea principal: Puerta 0 firmada, paridad local condicional, sweep target-free y Event Store PIT. GATE quedó como cimiento ejecutable no operativo. Crypto/contextos quedó aislado. El registro del 24-ago encontró 28 ramas remotas.

## 5. A-priori por activo y defecto de paridad fuera del default — 25 de agosto

Las ramas ES/MBT prepararon configuraciones a-priori. `fix/sweep-finalize-contract-scope@ee07c34` detectó que `MinExportVolume` se leía y descartaba en Python mientras NT8 sí filtraba: Puerta 0 había pasado porque el default volvía inerte el defecto. Se agregaron pruebas fuera del default.

## 6. Gate 1, Gate 2 y auditoría de outputs — 26 de agosto

Las ramas `work/bt2a-gate1-*` fijaron procedencia de specs y registros. La auditoría L2 midió que el Event Store GC all5 no era equivalente 1:1 a Gate 1: 71/234 sesiones diferían. También detectó raw GC 08-26 con filas de holdout en disco, aunque el filtro de sesiones respetaba la frontera. Gate 2/L2 quedó endurecido pero separado de cualquier promoción.

## 7. P2-A, P2-B, coordinate store y aVol en dos etapas — 27 y 28 de agosto

P2-A ejecutó el diagnóstico horario GC: 16.869 eventos, 215 sesiones completas, 0/12 contrastes sobrevivieron Holm-12. Resultado: no hubo señal de heterogeneidad horaria; tampoco se probó homogeneidad.

P2-B abrió una línea económica GC. El coordinate store materializó coordenadas target-free. aVolClusterPOI abrió compresión/dos etapas y un sweep target-free de microticks. La infraestructura Kaggle fail-closed y las cadenas de PR crecieron. El registro del 28-ago observó 45 ramas iniciales y 46 tras la rama de trazabilidad.

## 8. Selección NQ y Gate 1 — 29 a 31 de agosto

La selección target-free NQ se detuvo por decisión de Nico en 2/5 contratos. Spearman de `n_events` = 0,976 y top-10 idéntico, pero el protocolo formal exigía 4 contratos: `bt2a_nq_7e84981882b0b380` quedó como adopción informal, no `SELECTED_STABLE_NQ_CONFIGURATION`.

Después se abrieron ramas de contrato, capacidad N-RAND, potencia, bindings, runner y outcomes. El corrigendum D6 fijó fases gruesas de 4 horas, no 2. Las ramas son una cadena histórica de construcción y no deben mergearse por fecha. El resultado posterior registrado para NQ fue `NO_DIRECTIONAL_MECHANISM`; por eso no habilita transferencia de la campaña SL/TP a NQ.

En paralelo, el diseño SL/TP+breakeven GC registró HP-005: 372 celdas primarias, gatillo BE denso y corrección familiar. Sigue bloqueado por suite de verdad conocida RW/MCS, procedencia P2-B y auditoría de capas de trayectoria.

## 9. Paridad aVolClusterPOI, régimen contractual y manifiesto NQ — 1 de septiembre

La paridad NQ 06-26 quedó en FAIL: 19 `GEOMETRY_DIFF`, 57 `MISSING_IN_NT8`, 48 `MISSING_IN_PYTHON`. El supuesto mismatch de stream se redujo a un desfase de 3 ticks en el borde de ventana; falta alinear secuencias antes de adjudicar causa.

Se creó `contract_regime.py` con liderazgo causal por volumen D-1, no retroceso, empate conserva vigente y dato faltante bloquea. La rama divergente de auditoría se congeló; sólo se trasladaron commits quirúrgicos, nunca la rama completa.

El manifiesto v1 de NQ quedó invalidado por 28 fines de semana, completitud inferida con un tick y falta de separación entre cero y ausencia. El scan v2 procesó 119.153.201 filas y abstuvo correctamente por falta de evidencia de completitud.

## 10. Diagnóstico NQ 09-26 — 2 de septiembre

El diagnóstico target-free procesó 6.235.464 filas. Midió 363.601 ticks —5,8312 %— y volumen 398.066 en 16:00–17:00 CT, concentrados en 9 días hábiles del 17 al 30-jun-2026.

Se descartaron como explicación la semántica UTC/local y el re-corte del holdout. La hipótesis dominante es una plantilla NT8 distinta para `NQ 09-26.Last.txt`, pero la causa formal sigue `UNRESOLVED`. El roll del 16-jun no queda contaminado por esta anomalía; los volúmenes del 17–30 no son comparables sin normalizar sesión.

`foundation` avanzó hasta `f896ca6`, que acota el gate de schema a presencia nominal de columnas. No certifica tipos, nulabilidad, invariantes ni semántica.

## Lectura causal del conjunto

La cronología no es una escalera lineal hacia un edge. Es una sucesión de capas:

1. portabilidad y procedencia;
2. paridad y contratos;
3. población target-free;
4. régimen contractual y calendario;
5. outcomes autorizados;
6. economía neta;
7. replicación fuera de muestra.

Las ramas de infraestructura no prueban la capa siguiente. Los resultados negativos o abstencionistas son cierres científicos válidos, no fallas técnicas.

## Aporte al referente

La historia queda ordenada por dependencias científicas y no por cantidad de commits: primero identidad y población, después outcomes y recién al final edge neto.