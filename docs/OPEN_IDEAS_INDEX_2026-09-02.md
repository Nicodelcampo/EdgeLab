# EdgeLab — índice de ideas y trabajo abierto

Corte: 2026-09-02. Este archivo no autoriza ninguna corrida. Agrupa lo abierto; `PENDIENTE.md`, los specs y los manifiestos conservan la autoridad detallada.

## Prioridad 0 — bloqueos del camino actual

| Línea | Estado medido | Próximo cierre verificable | STOP |
|---|---|---|---|
| Régimen contractual NQ | scan v2: 119.153.201 filas; 0 rolls certificados; abstención | certificar calendario CME y cobertura de fuente por separado | no EF0/outcomes/holdout |
| NQ 09-26 mantenimiento | 363.601 ticks, 9 días; causa formal `UNRESOLVED` | inspeccionar plantilla/export NT8 y `.Last.txt` original | no adjudicar causa por inferencia |
| Manifiesto NQ | v1 inválido; v2 sin evidencia aprobada | producir evidencia de completitud aprobable y reconstruir | aprobación de Nico requerida |
| Trace NQ operable | trace 06-26 no representa cadena contractual certificada | reconstruir desde raw con reset total en cada roll | no recortar post hoc el trace contaminado |

Orden obligatorio: plantilla NT8 → documentos CME hasheados → cobertura de fuente → evidencia de completitud → manifiesto → crossovers → reconstrucción del trace → EF0.

## Prioridad 1 — aVolClusterPOI NQ

| Tema | Estado | Pendiente |
|---|---|---|
| Paridad NQ 06-26 | FAIL: 19 geometry, 57 missing NT8, 48 missing Python | alinear secuencias ignorando ~3 ticks de borde y reclasificar |
| TickBar classifier | `STREAM_MISMATCH` nominal, pero shift +3h correcto | corregir comparación posicional antes de atribuir mismatch |
| Lifecycle | borrador con 44 decisiones abiertas en la rama Gate1B/Gate3 | decidir semántica de touch, episodio, expiración y colapso |
| Gate 1B/Gate 3 | infraestructura fail-closed; no resultado | cerrar decisiones y procedencia antes de ejecutar |
| EF0 | bloqueado por régimen y paridad | no correr hasta cerrar ambos frentes |

## Prioridad 2 — BT2A NQ

La cadena de ramas incluye sweep V2, selección target-free, contrato Gate 1, potencia, capacidad N-RAND, bindings y runner. La adopción `bt2a_nq_7e84981882b0b380` se basó en 2/5 contratos y es informal. El protocolo pedía 4. No reescribir esa historia como selección formal.

El resultado posterior `NO_DIRECTIONAL_MECHANISM` no habilita campaña de salida NQ. Las ramas de implementación sirven como evidencia y tooling; no como promoción.

## Prioridad 3 — BT2A GC económico y salidas

### HP-005 — SL/TP asimétrico + breakeven

Diseño en `research/bt2a-gc-sltp-breakeven-design-v1-20260830`.

Bloqueos:

1. suite de verdad conocida para Romano-Wolf y MCS;
2. artefacto P2-B verificable o retracción formal;
3. auditoría de capas de trayectoria ya presentes en Event Store;
4. freeze explícito antes de outcomes reales.

La prueba sintética de 17.408 llamadas demuestra mecánica, no expectativa económica.

### P2-A horario GC

Cerrado como resultado negativo: 0/12 contrastes Holm. No crear filtros horarios post hoc con los dos contrastes nominales de `(30t,250t)`.

### P2-B GC

Existe rama económica y corrección del orden `(ts, source_row)`. Antes de reutilizar resultados hay que cerrar identidad del artefacto, población contractual y procedencia. Los costos GC no se transportan a NQ.

## Ideas de indicadores

| ID | Idea | Estado correcto | Condición de reentrada |
|---|---|---|---|
| HP-001 | burst de zonas HFT al cierre en ES | no medida en ES | verificar resolución temporal y comparar contra volumen horario |
| HP-002 | VolTicksDef | no agregar | rescatar sólo estimador P² para indicador existente o estrategia |
| HP-003 | aVolClusterPOI | candidato válido, ya convertido en línea activa | EventLog target-free, score descompuesto, paridad y régimen |
| HP-004 | aVolZonePOI | descartado | conservar sólo como control negativo de diseño |
| HP-005 | salidas SL/TP+BE GC | diseño pendiente de freeze | cerrar RW/MCS, P2-B y Event Store |

Nota de procedencia: `foundation/docs/HIPOTESIS_PENDIENTES.md` contiene HP-001…HP-004. HP-005 sólo está completo en la rama `research/bt2a-gc-sltp-breakeven-design-v1-20260830`; por eso queda indexado acá para que no se pierda.

## Líneas secundarias abiertas o aparcadas

| Línea | Estado | Pregunta pendiente |
|---|---|---|
| G2 A1 | dos contratos rivales | adjudicar semántica con verdad conocida, no por CI verde |
| GATE | cimiento ejecutable, no operativo | checkpoint con datos reales y procedencia |
| Crypto/contextos | rama/PR separados | historia de `LOT_SIZE`, fuentes y CI; nada de transportar edges |
| GEX | observacional | cerrar convención de signo GEX-M0 antes de interpretar |
| YM PreRange | histórica | calendario/sesión y nulo correcto antes de reactivar |
| ZAMR-1 | infraestructura/parqueada | decidir vigencia frente a líneas actuales |
| BigTrap2 multiframe ML | aparcada | nuevo manifiesto y STOP antes de reactivar |
| Coordinate store | PR abierta | auditar si la representación es la fuente canónica para trayectorias |
| Event Store PIT | código versionado | recomputación y equivalencia contra poblaciones canónicas |
| ES/MBT a-priori | ramas históricas | adjudicar diff y decidir si conservar sólo como documentación |

## Deuda de repositorio

1. 60 ramas remotas observadas; ninguna protegida.
2. 17 PR abiertas; varias forman cadenas cuya base no es `foundation`.
3. Los registros del 24 y 28 de agosto quedaron superados.
4. `docs/CURRENT.md` todavía describe el corte del 24-ago.
5. La rama de auditoría divergente no debe mergearse completa.
6. Falta auditoría mecánica de ancestry y equivalencia de patches para clasificar ramas históricas como contenidas.
7. El JSON del diagnóstico NQ 09-26 conserva las cuatro hipótesis en `hypotheses_not_decided`, aunque el README descarta dos: reconciliar estado machine-readable sin alterar el artefacto original.

## Cómo registrar una idea nueva

Una idea nueva entra con: ID, fecha, origen, instrumento, mecanismo, comparador no nulo, medición que la falsaría, firewall de outcomes y rama responsable. Si ya existe un mecanismo equivalente, se registra como mejora o control, no como indicador nuevo.

## Aporte al referente

Las ideas dejan de estar repartidas entre ramas, PR y handoffs: cada una tiene estado, bloqueo y condición de reentrada sin convertir infraestructura en evidencia de edge.