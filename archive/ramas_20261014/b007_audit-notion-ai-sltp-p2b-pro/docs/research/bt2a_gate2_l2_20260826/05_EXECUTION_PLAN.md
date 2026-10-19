# 05 — Plan de ejecución ordenado

## Regla de secuencia

No reanudar el sweep, no usar el Event Store en P2 y no abrir CTX-3 hasta completar las
fases anteriores. Un artefacto local sin hash no se eleva a evidencia formal por el
nombre de su carpeta.

## Fase A — cerrar la auditoría local nocturna

| ID | Tarea | Estado |
|---|---|---|
| A-01 | Ejecutar `CLAUDE_CODE_LOCAL_AUDIT.md` sobre los tres directorios | pendiente local |
| A-02 | Versionar `LOCAL_AUDIT_RESULT.json/.md` sin datos crudos | pendiente local |
| A-03 | Confirmar commit y dirty flags de la corrida L2 | bloqueante |
| A-04 | Hashear modelo, labels, reports y cinco Event Stores | bloqueante |
| A-05 | Leer `code_commit` de los 190 parciales | bloqueante para resume |

Salida: evidencia suficiente para clasificar cada corrida como formal, diagnóstica o
inválida por procedencia.

## Fase B — reconciliar Gate 1 y Event Store

| ID | Tarea | Estado |
|---|---|---|
| B-01 | Filtrar Event Store por las 234 sesiones de la registry | pendiente |
| B-02 | Comparar conteos por contrato/sesión con los CSV Gate 1 | pendiente |
| B-03 | Validar fill estricto y frontera CME | pendiente |
| B-04 | Reproducir event IDs con el runtime congelado Gate 1 | pendiente |
| B-05 | Publicar diff 1:1 y causas de cualquier sobrante/faltante | pendiente |

Criterio: sólo un store con equivalencia exacta o diferencias causalmente explicadas y
excluidas puede alimentar P2. El resultado Gate 1 existente no se reescribe.

## Fase C — implementar Puerta 2

| ID | Tarea | Estado |
|---|---|---|
| C-01 | Aprobar/congelar `bt2a_gate2_first_passage_v1.json` | decisión pendiente |
| C-02 | Implementar kernel first-touch secuencial | pendiente |
| C-03 | Golden tests: TP, SL, timeout, borde CME, último tick | pendiente |
| C-04 | Runner por sesión con checkpoints/hashes | pendiente |
| C-05 | Reproducir cuatro brazos de Gate 1 | pendiente |
| C-06 | Implementar P2-B con simulador y rechazos | pendiente |
| C-07 | Confirmar comisión GC | dato humano pendiente |
| C-08 | Publicar P2 diagnóstico all5 | requiere autorización |

Criterio: P2-A y P2-B deben producir artefactos separados; `TIMEOUT` nunca desaparece.

## Fase D — terminar el sweep correctamente

1. Auditar el commit de los parciales.
2. Elegir una ruta sin mezcla:
   - completar desde el commit original; o
   - recomputar los 396 bajo un commit nuevo congelado.
3. No modificar `code_commit` manualmente.
4. Publicar matriz completa, input hashes y summary.
5. Rotularlo como universo antiguo de 152/133 sesiones y cuatro contratos.
6. Si se necesita sensibilidad all5, crear un spec nuevo sobre 234 sesiones y cinco
   Parquets; no llamar all5 al resultado antiguo.

Uso permitido: estabilidad de población/eventos. Uso prohibido: elegir la config con
mejor outcome o redefinir retrospectivamente Gate 1.

## Fase E — cerrar la evidencia L2

| ID | Tarea | Estado |
|---|---|---|
| E-01 | Repetir extracción sobre árbol limpio si `dirty_start=true` | probable |
| E-02 | Generar reporte target-free derivado de artefactos | pendiente |
| E-03 | Publicar ocupación, persistencia, flip y fallos de libro | pendiente |
| E-04 | Agregar features v2 aprobadas y tests de prefijo | pendiente |
| E-05 | Resolver reloj/identidad de captura | pendiente |
| E-06 | Conseguir L2 de sesiones compatibles con eventos | bloqueante de datos |
| E-07 | Llegar a >=40 sesiones por celda primary | bloqueante de potencia |
| E-08 | Aprobar/congelar `bt2a_gate_l2_context_v2.json` | después de E-01..E-07 |

## Fase F — abrir CTX-3

Sólo después de congelar el estimando P2 y pasar todos los gates target-free:

```text
primary = [(K_ABS-N_RAND)|G-operable]
          - [(K_ABS-N_RAND)|G-stress]
```

Una interacción bilateral, bootstrap por sesiones, headline config únicamente. Los
controles secundarios pagan Holm separado.

## Fase G — confirmación

La muestra all5 es post-outcome. Para cualquier claim confirmatorio:

1. congelar detector, barreras, ejecución y contexto;
2. registrar muestra futura antes de abrirla;
3. ejecutar una vez;
4. aplicar G2 calibrado;
5. mantener promoción fail-closed hasta pasar todos los gates.

## Refuerzos que deben entrar al código

### Gate 1

- Event Store derivado del mismo runtime y registry;
- manifest con input/output/code hashes;
- evento estable y único;
- prueba de equivalencia contra checkpoints.

### Gate 2

- first-touch tick por tick;
- timeout explícito;
- fill estricto y sesión dura;
- capa de mecanismo separada de ejecución;
- costos, rechazos y concurrencia visibles;
- multiplicidad contada.

### Gate L2

- paquete target-free versionado;
- forward-only y prefijo real;
- join por `source_row`, nunca aproximado;
- estabilidad/ocupación de estados;
- interacción directa;
- N por sesión, no por evento.

## Definición global de terminado

```text
Gate 1 reforzada:
  event store reconciliado y resultado original intacto

Puerta 2 terminada:
  spec congelado + código + tests + manifests + corrida diagnóstica

Puerta L2 terminada:
  paquete limpio + datos compatibles + gates de N + spec congelado

Confirmación terminada:
  sólo sobre sesiones nuevas, con G2 y costos
```
