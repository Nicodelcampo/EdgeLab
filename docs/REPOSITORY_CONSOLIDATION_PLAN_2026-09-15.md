# EdgeLab — plan de consolidación sin pérdida

**Estado:** FASE 0 / DOCUMENTACIÓN SOLAMENTE  
**Rama:** `docs/safe-agent-onboarding-20260915`  
**Base:** `foundation/f0b-compatibility-probe` en `08153f5438a766e8e67d761727fc17c26d97677e`

## Mandato

Ordenar el repositorio para que un agente pueda orientarse rápido y con poco contexto, con prioridad absoluta en no perder información ni borrar datos.

## Invariantes

1. No borrar ramas, tags, archivos, datos, resultados, specs, manifests, oráculos, cuarentenas ni historia.
2. No mover o renombrar rutas citadas durante la fase inicial.
3. No modificar artefactos históricos; toda corrección es una enmienda o un nuevo corte.
4. No mergear ni cerrar ramas sin decisión explícita de Nico y verificación mecánica previa.
5. La rama `audit/notion-ai-sltp-p2b-provenance-20260830` permanece `FROZEN_READ_ONLY / DO_NOT_MERGE / DO_NOT_DELETE`.
6. No tocar outcomes, P&L, MAE/MFE, EF0, holdout, tolerancias, specs congelados ni parquets.
7. Toda fase debe ser reversible y dejar evidencia de refs antes y después.

## Fase 0 — completada en esta rama

- Crear snapshot inmutable de las 60 ramas y sus SHA.
- Crear `repo_state.json` como router, sin reemplazar autoridades.
- Crear `START_HERE_AGENT.md` con una lectura inicial corta.
- No modificar código, datos ni documentación histórica.

## Fase 1 — auditoría mecánica, sin cambios destructivos

Para cada rama:

- obtener merge-base contra la rama viva;
- enumerar commits exclusivos en ambos sentidos;
- calcular patch-equivalence con `git cherry`;
- inventariar archivos exclusivos, renombres y artefactos;
- identificar PR asociada y estado de checks;
- clasificarla como `ACTIVE`, `FROZEN`, `HISTORICAL_UNINTEGRATED`, `PATCH_EQUIVALENT`, `DUPLICATE_REF` o `UNKNOWN`;
- registrar evidencia y nivel de confianza.

Ninguna clasificación autoriza borrar o mergear.

## Fase 2 — índice de rutas y reducción de contexto

Sin mover archivos existentes:

- agregar índices por objeto científico;
- señalar autoridad, estado, rama, spec, manifest, resumen y evidencia;
- marcar documentos históricos o sustituidos mediante índices, no editándolos;
- añadir límites de tamaño y contratos de resumen para nuevo material.

## Fase 3 — integración revisable

Sólo con aprobación explícita:

- crear una rama de integración desde la rama viva;
- aplicar cambios validados en grupos pequeños;
- ejecutar suites y verificaciones de procedencia después de cada grupo;
- conservar SHA origen y destino;
- abrir PRs separados por objeto, nunca un merge masivo de 60 ramas.

## Fase 4 — preservación histórica

Sólo después de demostrar ancestry o patch-equivalence y con aprobación explícita:

- crear tags de preservación;
- exportar bundle o snapshot verificable de refs;
- documentar checksums y ubicación;
- decidir por separado cualquier cierre o eliminación futura.

Este plan no propone borrar datos. Incluso una rama demostrada como duplicada se conserva hasta que Nico autorice explícitamente otra cosa.

## Criterio de éxito

Un agente nuevo entiende estado, autoridad, bloqueos y ruta de evidencia leyendo menos de cinco archivos, mientras toda evidencia original sigue disponible por la misma ruta o por una referencia de preservación verificada.

## Aporte al referente

La reorganización comienza por trazabilidad y routing, no por limpieza destructiva, reduciendo costo de contexto sin aumentar riesgo científico ni operativo.