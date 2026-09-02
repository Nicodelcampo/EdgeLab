# EdgeLab — índice de ideas y trabajo abierto

Corte: 2026-09-02. Este archivo no autoriza corridas. `PENDIENTE.md`, specs y manifests conservan la autoridad detallada.

## Prioridad 0 — camino actual

| Línea | Estado medido | Próximo cierre verificable | STOP |
|---|---|---|---|
| Rolls NQ | 4 fechas/contratos/ratios idénticos a 6 decimales bajo dos calendarios diagnósticos | reconstruir con evidencia aprobada | no llamar certificado |
| Calendario CME | **RESUELTO `4f365bf`**: horas por producto capturadas con URL + SHA-256 vía endpoint JSON de cmegroup.com, que además sirve 2025 (la página no lo publica, el endpoint sí). 322 sesiones, valida contra el gate | adjudicarlo formalmente; resolver Juneteenth 2026-06-19 | no se infirieron horas: se construyó sólo con la fuente y recién después se corroboró contra el dato (7 de 8 dentro de 0-6 min) |
| Cobertura de fuente | separada conceptualmente; no aprobada | particiones esperadas/presentes, estado de extracción y hash | no usar minutos activos |
| Manifiesto NQ | v1 inválido; v2 abstiene | aprobar completitud y reconstruir | no EF0/outcomes/holdout |
| NQ 09-26 | volumen v2 ya excluye mantenimiento | confirmar plantilla NT8 sólo como causa/procedencia residual | no adjudicar causa sin inspección |
| Trace operable | trace 06-26 no representa cadena certificada | reconstruir desde raw con reset en roll | no recortar post hoc |

El calendario sigue siendo obligatorio para certificar, pero P-68 midió que excluir nueve feriados no cambia ninguno de los cuatro rolls. Desde `4f365bf` el acceso a la fuente **ya no es un bloqueo**: el calendario está capturado y hasheado. Lo que queda es de **certificación** — adjudicar el calendario, resolver Juneteenth 2026-06-19 y aprobar la evidencia de completitud — sin evidencia actual de que las fechas de roll vayan a moverse.

## Prioridad 1 — aVolClusterPOI NQ

| Tema | Estado | Pendiente |
|---|---|---|
| Paridad NQ 06-26 | FAIL: 19 geometry, 57 missing NT8, 48 missing Python | alinear secuencias ignorando ~3 ticks de borde y reclasificar |
| TickBar classifier | shift +3h correcto; comparación posicional frágil | corregir alineación antes de atribuir mismatch |
| Lifecycle | 44 decisiones abiertas en Gate1B/Gate3 | decidir touch, episodio, expiración y colapso |
| Gate 1B/Gate 3 | infraestructura fail-closed; no resultado | cerrar decisiones y procedencia |
| EF0 | bloqueado por régimen y paridad | no ejecutar todavía |

## Prioridad 2 — BT2A NQ

La adopción `bt2a_nq_7e84981882b0b380` se basó en 2/5 contratos. Spearman de `n_events` = 0,976 y top-10 idéntico, pero el protocolo exigía 4: no es `SELECTED_STABLE_NQ_CONFIGURATION` formal.

El resultado posterior `NO_DIRECTIONAL_MECHANISM` no habilita campaña de salida NQ. Tooling y runners no equivalen a promoción.

## Prioridad 3 — BT2A GC económico y salidas

### HP-005 — SL/TP asimétrico + breakeven

Bloqueos: suite de verdad conocida Romano-Wolf/MCS; artefacto P2-B o retracción; auditoría de capas de trayectoria; freeze explícito antes de outcomes. Las 17.408 simulaciones sintéticas prueban mecánica, no expectativa.

### P2-A horario GC

Resultado negativo: 0/12 contrastes sobrevivieron Holm. No crear filtros horarios post hoc.

### P2-B GC

Cerrar identidad de artefacto, población contractual y procedencia antes de reutilizar. Costos GC no se transportan a NQ.

## Ideas de indicadores

| ID | Idea | Estado correcto | Reentrada |
|---|---|---|---|
| HP-001 | burst HFT al cierre en ES | no medida en ES | resolución temporal + control por volumen horario |
| HP-002 | VolTicksDef | no agregar | rescatar sólo estimador P² |
| HP-003 | aVolClusterPOI | línea activa | EventLog target-free, score descompuesto, paridad y régimen |
| HP-004 | aVolZonePOI | descartado | control negativo de diseño |
| HP-005 | salidas SL/TP+BE GC | diseño sin freeze | RW/MCS, P2-B y Event Store |

HP-005 sólo está completa en `research/bt2a-gc-sltp-breakeven-design-v1-20260830`; se indexa para que no desaparezca de la vista de `foundation`.

## Líneas secundarias

| Línea | Estado | Pregunta pendiente |
|---|---|---|
| G2 A1 | dos contratos rivales | adjudicar con verdad conocida, no CI |
| GATE | cimiento no operativo | checkpoint real y procedencia |
| Crypto | rama/PR separados | historia de `LOT_SIZE`, fuentes y CI |
| GEX | observacional | convención de signo GEX-M0 |
| YM PreRange | histórica | calendario/sesión y nulo antes de reactivar |
| ZAMR-1 | aparcada | vigencia frente a líneas actuales |
| BigTrap2 multiframe | aparcada | manifiesto y STOP nuevos |
| Coordinate store | PR abierta | autoridad para trayectorias |
| Event Store PIT | versionado | recomputación y equivalencia poblacional |
| ES/MBT a-priori | históricas | adjudicar diff |

## Deuda de repositorio

1. 60 ramas; 0 protegidas; 17 PR abiertas.
2. Falta ancestry/patch-equivalence mecánica para ramas históricas.
3. El JSON original del diagnóstico NQ 09-26 conserva cuatro hipótesis no decididas aunque el README descarta dos; no alterar el artefacto original, publicar enmienda si se corrige.
4. Los handoffs del 24/28-ago son históricos, no puntos de entrada.

## Cómo registrar una idea nueva

ID, fecha, origen, instrumento, mecanismo, comparador no nulo, criterio de falsación, firewall y rama responsable. Un mecanismo duplicado entra como mejora o control, no como indicador nuevo.

## Aporte al referente

El backlog distingue tarea de acceso, decisión científica, diagnóstico robusto y certificación pendiente.