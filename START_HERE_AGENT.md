# EdgeLab — inicio rápido y seguro para agentes

> Este archivo reduce el contexto inicial sin sustituir ninguna autoridad existente.
> No autoriza merges, borrados, movimientos de datos, outcomes ni acceso al holdout.

## Lectura inicial mínima

1. `AGENTS.md` — reglas permanentes y firewalls.
2. `repo_state.json` — estado compacto y legible por máquinas.
3. `docs/CURRENT.md` — estado vivo y bloqueos con matices.
4. `PROJECT_INDEX.md` — mapa hacia la evidencia relevante.
5. Sólo después, el spec/manifest o documento del objeto concreto.

Los specs y manifests congelados conservan autoridad sobre cualquier resumen. `PENDIENTE.md` conserva la autoridad detallada de decisiones P-NN, pero no es necesario cargar sus 146 KB completos antes de conocer el objeto: localizar primero el ID o tema pertinente y leer su sección.

## Estado operativo resumido

- Rama viva declarada: `foundation/f0b-compatibility-probe`.
- `main` es baseline histórico; no asumir que contiene el estado vigente.
- 60 ramas remotas observadas el 2026-09-15; ninguna protegida.
- EF0 permanece bloqueado.
- Rolls NQ certificados: 0; los cuatro rolls provisionales no equivalen a certificación.
- Completitud de fuente: no aprobada.
- `PREEXISTING_OUTCOME_EXPOSURE=YES`.
- Holdout sellado: `2026-07-01` a `2026-12-31`.
- Rama congelada: `audit/notion-ai-sltp-p2b-provenance-20260830` — `FROZEN_READ_ONLY / DO_NOT_MERGE / DO_NOT_DELETE`.

## Cómo ahorrar contexto sin perder rigor

Antes de leer archivos grandes:

1. Resolver rama y commit exactos.
2. Consultar `repo_state.json`.
3. Buscar el objeto en `PROJECT_INDEX.md` y `docs/OPEN_IDEAS_INDEX_2026-09-02.md`.
4. Leer sólo el spec/manifest y el resumen vigente de ese objeto.
5. Abrir auditorías, cronología y artefactos crudos únicamente si una afirmación depende de ellos.

No usar el nombre de una rama, la fecha o un check verde como prueba de vigencia, contención, causalidad o equivalencia de patches.

## Política de preservación

- No borrar ramas, tags, archivos, datos, artefactos, cuarentenas ni historia.
- No mover ni renombrar rutas citadas sólo por orden estético.
- No reescribir artefactos históricos: publicar una enmienda o un nuevo corte.
- Toda futura limpieza requiere snapshot de refs, análisis de ancestry, equivalencia de patches, inventario de artefactos y aprobación explícita de Nico.
- La ausencia de datos local-only en Git no demuestra inexistencia.

## Alcance de esta reorganización

La primera fase es aditiva y reversible: agrega este índice, `repo_state.json`, un snapshot inmutable de las 60 refs y un plan de consolidación. No modifica código, datos, specs, resultados ni documentos históricos.

## Aporte al referente

El acceso inicial queda reducido a un mapa compacto sin degradar autoridad, firewalls ni trazabilidad y sin eliminar información.