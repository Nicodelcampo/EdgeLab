# EdgeLab — cronología consolidada

Corte: 2026-09-02. Reconstruida desde registros de ramas, 60 tips remotos, `PENDIENTE.md`, handoffs y artefactos.

## 1. Fundación portable — 21 a 23 de julio

`main@cde6d93` preservó la baseline portable. Los dos refs `a48efcd` son backup/preservación, no ramas de trabajo.

## 2. Arquitectura científica y primeras hipótesis — 4 a 9 de agosto

Gate mínimo de sesiones, iteraciones multimodelo y rechazo de `IndicatorSpec v0` como implementation-ready. HP-001…HP-004 separaron observaciones, mejoras reutilizables y diseños descartados.

## 3. Procedencia, contratos y paridad — 10 a 15 de agosto

Se documentó el incidente de procedencia y nacieron LUX, YM, G2 y BigTrap2. BigTrap2 v2.5.2 corrigió timestamp y cola. Los nulos evolucionaron hacia desplazamiento local. La auditoría del 15-ago dejó el diagnóstico rector: fuerte para no engañarse, todavía lejos de expectativa económica neta. Se registró exposición previa a outcomes.

## 4. Expansión y BT2Absorption — 16 a 24 de agosto

H-Z2A, HFTZones, GEX, rango Asia, L2 y contextos. BigTrap2Absorption: Puerta 0, paridad local condicional, sweep target-free y Event Store PIT. GATE quedó no operativo; Crypto aislado. Registro: 28 ramas.

## 5. A-priori y defecto fuera del default — 25 de agosto

ES/MBT prepararon configuraciones a-priori. `MinExportVolume` se leía y descartaba en Python mientras NT8 filtraba. Puerta 0 no lo vio porque el default era inerte. Se agregaron pruebas fuera del default.

## 6. Gate 1/Gate 2 y outputs — 26 de agosto

Se fijó procedencia de specs. El Event Store GC all5 difería de Gate 1 en 71/234 sesiones. Se detectó raw GC 08-26 con filas de holdout en disco, aunque el filtro de sesiones respetaba la frontera. Gate 2/L2 quedó endurecido sin promoción.

## 7. P2-A, P2-B, coordinate store y aVol — 27 a 28 de agosto

P2-A horario GC: 16.869 eventos, 215 sesiones, 0/12 contrastes Holm; no señal, tampoco prueba de homogeneidad. P2-B abrió economía GC. Coordinate store materializó coordenadas target-free. aVolClusterPOI abrió compresión y microticks. Registro: 45 ramas iniciales, 46 tras trazabilidad.

## 8. Selección y Gate 1 NQ — 29 a 31 de agosto

Selección NQ detenida en 2/5: Spearman 0,976 y top-10 idéntico, pero sin cumplir mínimo de 4 contratos. Config adoptado informalmente, no selección formal.

Se construyeron contrato, potencia, N-RAND, bindings y runners. D6 corrigió fases a 4 horas/6 fases. El resultado NQ posterior fue `NO_DIRECTIONAL_MECHANISM`; no habilita transferencia de salidas.

HP-005 diseñó 372 celdas SL/TP+BE GC; sigue bloqueada por RW/MCS, P2-B y Event Store.

## 9. Paridad aVolClusterPOI y régimen NQ — 1 de septiembre

Paridad NQ 06-26: 19 geometry, 57 missing NT8, 48 missing Python. El supuesto mismatch de stream se redujo a ~3 ticks de borde.

`contract_regime.py` implementó liderazgo causal D-1. La rama de auditoría divergente quedó congelada.

El manifiesto v1 fue invalidado por 28 fines de semana, completitud inferida con un tick y confusión cero/ausencia. El scan v2 procesó 119.153.201 filas y abstuvo por falta de completitud aprobada.

## 10. Diagnóstico NQ 09-26 — 2 de septiembre

6.235.464 filas; 363.601 ticks y volumen 398.066 en 16:00–17:00 CT; 9 días hábiles. UTC/local y re-corte descartados. Plantilla NT8 distinta: hipótesis dominante, no causa certificada.

El roll del 16-jun usa volumen D-1 y no queda afectado. El scan v2 ya excluye mantenimiento.

## 11. Sensibilidad P-68 — 2 de septiembre

Se comparó la implementación real con:

- 237 weekdays;
- 229 weekdays tras excluir nueve feriados US.

Resultado medido: cuatro fechas y contratos idénticos; ratios idénticos a 6 decimales:

| Roll | Contrato | Ratio |
|---|---|---:|
| 2025-09-17 | NQ 12-25 | 3,396162 |
| 2025-12-16 | NQ 03-26 | 1,260126 |
| 2026-03-17 | NQ 06-26 | 1,125767 |
| 2026-06-16 | NQ 09-26 | 2,286790 |

Esto vuelve robustas las fechas frente a la perturbación probada. No certifica completitud: el diagnóstico asumió sesiones completas para aislar ese efecto.

**2026-09-02, `4f365bf` — calendario CME resuelto.** El WAF bloquea `curl` y el fetcher, pero el endpoint JSON oficial que la propia página consume responde 200 desde el origen y sirve fechas históricas, cubriendo también 2025. Calendario de 322 sesiones (2025-08-01..2026-06-18) con URL + SHA-256 por override, validado contra `cme_equity_index_calendar.py`. Construido sólo con la fuente y corroborado después contra el dato: 7 de 8 early-close dentro de 0-6 minutos, y el patrón de 1140 minutos queda explicado como early close 12:00 CT. Juneteenth 2026-06-19 sin adjudicar (fuente ambigua vs 115.146 ticks observados), por eso el rango corta el 18-jun.

## Lectura causal

1. portabilidad/procedencia;
2. paridad/contratos;
3. población target-free;
4. calendario/cobertura/completitud;
5. outcomes autorizados;
6. economía neta;
7. replicación fuera de muestra.

Infraestructura no prueba la capa siguiente. Un resultado negativo o una abstención puede ser un cierre científico válido.

## Aporte al referente

La cronología incorpora P-68 sin coronar los rolls: estabilidad diagnóstica y certificación quedan separadas.