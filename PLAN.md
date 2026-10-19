# EdgeLab — plan vigente desde 2026-08-10

## Etapa P0 — reconciliación forense

1. Detener writers y procesos que compartan la worktree.
2. Capturar raíz, git-dir, worktrees, HEAD, status v2, diffs, reflog y grafo de refs.
3. Cruzar timestamps de procesos, artefactos y commits (`6a2c08a`, `5a143da` y sucesores).
4. Revisar `git_head()` y todas las llamadas de procedencia con `cwd=repo_root` explícito.
5. Determinar si cada artefacto provino de árbol dirty, otra worktree, una reescritura concurrente o una corrida anterior.
6. Reemitir desde commit limpio todo resultado ambiguo.
7. Integrar por separado el fix de `.gitignore` del proceso `task_e4c25dc3`.
8. Publicar commits y verificar hashes remotos.

**Gate P0:** ningún resultado corregido, barrido de parámetros ni salida ES cambia conclusiones hasta cerrar el expediente de procedencia.

## Etapa A — integridad científica

1. Resolver drift BigTrap2 `.cs` v2.5.1 ↔ Python v2.2.
2. Adjudicar F1.1 corregido, seguimiento y `tick:25` reemitidos.
3. Revisar el barrido target-free de 11 celdas y su cruce `max_touches=1`.
4. Actualizar REGISTRO MEDIDO/NO MEDIDO.

## Etapa B — target-free

1. Adjudicar H-ATTR-1 contra nulos emparejados.
2. Completar lifecycle, competing risks y depleción ordinal.
3. Separar `ticks_per_row` de `bar_spec`.
4. Materializar estado continuo.
5. Enumerar event-space completo.
6. Generalizar a ES/NQ/YM solo desde universos habilitados y commits limpios.

## Etapa C — F4 constitucional: información condicional

Solo tras aprobación explícita del manifiesto. No confundir con el archivo local `F4_PARAMETROS_RESTANTES`.

- curvas de retorno por estado/evento;
- controles de hora, volatilidad y actividad;
- nulos emparejados;
- errores por sesión;
- sin argmax ni estrategia.

## Etapa D — economía

Si F4 sobrevive, elegir como máximo una monetización, estimar bruto/decaimiento/costos propios y clasificar `económico`, `informativo pero sub-fee` o `muerto`.

## Etapa E — confirmación

Replicación instrumental, pre-registro y solo después solicitud de apertura única del holdout.

## Prohibiciones inmediatas

- rescatar H1;
- interpretar la salida ES todavía no adjudicada;
- declarar válidos los reruns porque el proceso terminó;
- usar solo `git rev-parse HEAD` como identidad de un árbol dirty;
- correr dos agentes sobre la misma worktree;
- transportar costos de 6E;
- ejecutar F4 constitucional.
