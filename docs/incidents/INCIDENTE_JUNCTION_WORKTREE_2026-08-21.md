# Incidente — `git worktree remove` borró los parquets de ES a través de una junction

- **Fecha**: 2026-08-21, durante el sellado de R1
- **Estado**: **CERRADO** — datos restaurados y verificados byte a byte
- **Pérdida definitiva**: ninguna
- **Responsable**: Claude (Opus 5). No fue una acción pedida por Nico.

---

## Qué pasó

Para correr el rerun de R1 desde una worktree detached y limpia (exigencia de ATJ-14), la
worktree necesitaba los datos gitignoreados. Los enlacé así:

```
runs/oraculo_espurev2flat_ES_snapshot.sqlite   ->  HARDLINK de archivo
data/nt8/ES_parquet                            ->  JUNCTION de directorio
```

El rerun corrió bien. Al terminar ejecuté:

```
git worktree remove --force E:/EdgeLab_wt_r1_20260821
```

El borrado recursivo **siguió la junction** y vació el directorio **destino**,
`E:\EdgeLab\data\nt8\ES_parquet\` — 10 archivos, 4.004.759.221 bytes.

## La asimetría que no anticipé

| tipo de enlace | qué pasa al borrar el enlace |
|---|---|
| **hardlink de archivo** | se borra **sólo ese nombre**; el inodo sobrevive mientras quede otro nombre |
| **junction de directorio** | el borrado recursivo **atraviesa** y destruye el contenido del destino |

Traté las dos como equivalentes. No lo son. El snapshot sobrevivió intacto —era
hardlink— y su sha256 sigue siendo `a7dec2ee382c32ead53eeaffe9b02bbe`. Los parquets no.

## Por qué no hubo pérdida definitiva

Los parquets tenían **link count 2**: existía otra copia en `E:\EdgeLab_Repo\ES_parquet\`.
Verificado antes de restaurar nada:

- **sha256 de `ES_03-26_ticks.parquet`**: `948067CFB66A6C7CD19BED1C6F87C2A0877B1764740A00714E23EDD1749A9C35`,
  idéntico en las dos copias supervivientes.
- El `total 3910932` del `ls -la` previo al incidente cuadra con la suma de los cinco
  contratos (≈ 4,00 GB), lo que confirma qué archivos había que reponer:
  `ES_03-26`, `ES_06-26`, `ES_09-25`, `ES_09-26`, `ES_12-25`, más sus cinco manifests.

Restaurado por hardlink desde `E:\EdgeLab_Repo\ES_parquet\`. Total repuesto:
**4.004.759.221 bytes**.

## Verificación de contenido, no sólo de tamaño

Se comparó el parquet restaurado contra mediciones hechas **antes** del incidente en la
misma sesión, sobre la sesión `20260102`:

| control | esperado | obtenido |
|---|---|---|
| precio en el `start_ts` de referencia | 27728 | **27728** |
| precio del tick anterior | 27727 | **27727** |
| máximo de ticks en un mismo milisegundo | 182 | **182** |
| milisegundos distintos en 400 ticks | 31 | **31** |
| `sequence` estrictamente creciente | True | **True** |

## Alcance del daño

- **Perdido y repuesto**: `data/nt8/ES_parquet/` (10 archivos).
- **Intacto**: el snapshot del oráculo, `runs/` completo, el resto de `data/nt8/`
  (6B, 6E, 6J, BTC, GC, MBT, MES, MGC, MNQ, NQ…), el repositorio Git, `stash@{0}`.
- **Sin efecto sobre resultados**: el rerun de R1 (`run_id 0e16a11b81dcb865`) corrió
  **antes** del borrado, contra los datos correctos, y su artefacto ya estaba sellado.

## Causa raíz

Usar una **junction de directorio dentro de una worktree que iba a ser borrada por Git**.
`git worktree remove --force` no distingue entre contenido propio y punto de reparse.

## Qué cambia para que no se repita

1. **Nunca** poner una junction ni un symlink de directorio dentro de una worktree
   temporal. Si hace falta enlazar, sólo **hardlinks de archivo**.
2. **Mejor aún: no enlazar.** Los scripts deben aceptar las rutas de datos por argumento
   (`--parquet`, `--snapshot`), de modo que una corrida desde worktree apunte al árbol
   principal sin tocar el sistema de archivos. Implementado en `r2_matchability_es.py`.
   `memoria_nivel_nulo_correcto.py` queda pendiente: cambiarlo ahora obligaría a
   re-sellar R1 sin motivo de contenido.
3. Antes de `git worktree remove`, **inspeccionar puntos de reparse**:
   `Get-ChildItem <wt> -Recurse -Force | Where-Object { $_.LinkType }`.
4. Preferir `git worktree remove` **sin** `--force` cuando el árbol está limpio: el
   `--force` fue innecesario acá.

## Nota lateral que sí sirve para research

El manifest recuperado (`ES_09-26_manifest.json`) documenta de forma explícita:

> `sequence/source_row = orden estable del archivo (sin dedup, sin reorden)`

Eso es **evidencia documental** de procedencia del orden de fila, que es justo lo que la
precisión 1 del auditor pedía y que yo había afirmado por inferencia. Queda para incorporar
al diseño de `H-ES-HFT-BT2-ATLAS-1`, donde el identificador canónico de ticks
(`raw_stream_sha256` + `available_source_row`) es precondición.
