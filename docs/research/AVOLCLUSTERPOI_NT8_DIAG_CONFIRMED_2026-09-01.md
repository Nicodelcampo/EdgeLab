# aVolClusterPOI — mecanismo de GEOMETRY_DIFF confirmado con datos reales de NT8 (2026-09-01)

**Estado: mecanismo confirmado con `blockCells` reales de NT8 (no inferido vía
`density`). Corrige y reemplaza la sección "no se pudo confirmar con certeza
total" de `AVOLCLUSTERPOI_PARITY_NQ0626_TASKS123_FINDINGS_2026-09-01.md`,
tarea 3.**

Insumo: `data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv`
(sha256 `f42e416b4ab15717a6870d1ad01d686a1e8df5c2228139727d3b288fc286289d`,
22.508 filas, 1 por bloque, `CREATE` y `ABSTAIN`, mismos parámetros que el
oráculo original -- exportado corriendo el parche de
`AVOLCLUSTERPOI_NT8_DIAG_EXPORT_INSTRUCTIONS_2026-09-01.md`, `.cs` commit
`78b5c94`, compilado y corrido por Nico sobre NQ JUN26 120t, ventana
2026-04-07..06-12).

## Tres casos, tres severidades, un solo mecanismo

Se cruzó, por `bar_close_time` exacto (offset `+3h` chart→UTC, confirmado
`diff=0.0s` en los tres casos), el bloque real de NT8 contra el `block_trace`
real de Python para el mismo bloque:

| caso | nt8_id / py_id | ticks sólo en Python (ausentes en NT8) | diffs de valor en ticks compartidos | mediana py / nt8 | resultado geométrico |
|---|---|---|---|---|---|
| `413`/`372` (outlier) | 13 ticks, suma vol=31 | 4 ticks, ±1 a ±5 | 6 / 10 | diff=8 ticks |
| `9`/`106` | 1 tick, vol=1 | 3 ticks, ±1 | 13 / 12 | diff=1 tick |
| `27`/`119` | 0 ticks | 4 ticks, ±1 a ±3 | 17 / 15 | diff=2 ticks |

**El mismo mecanismo, con severidad proporcional**, explica los tres:

1. **Ruido de volumen por celda, siempre presente, siempre chico**: en los
   tres casos, un puñado de ticks (3-4) que SÍ existen en ambos lados tienen
   valores levemente distintos (diferencias de ±1 a ±5 sobre volúmenes de
   decenas a cientos). Esto es ruido de reconstrucción de footprint ya
   documentado como clase `FEATURE_DIFF` -- no es la causa dominante por sí
   solo (ver caso `27`, sin ningún tick ausente, donde este ruido solo alcanza
   para mover la mediana de 17 a 15, geometría diff=2).

2. **Ticks completos ausentes en NT8 en el borde de precio del bloque, en
   cantidad variable (0, 1 o 13 según el caso)**: éste es el efecto que
   domina cuando aparece. El caso `413` pierde 13 ticks completos (todo el
   extremo inferior 122490-122504) -- la mediana salta de 6 a 10, el
   `hotThreshold` de 12 a 20, y eso saca del cluster tanto un tick interno
   (122529=16, por debajo de 20) como toda la cola 122542-122549 (valores
   12-24, insuficientes para sobrevivir un `hotThreshold` de 20 aislados por
   `MaxGapTicks=1`). El caso `9` pierde sólo 1 tick de cola (volumen=1) y el
   efecto es mínimo (mediana 13→12, geometría diff=1).

Este segundo mecanismo es exactamente la clase de defecto ya documentada en
`nt8/aVolClusterPOI.cs` líneas ~304-316: el filtro `if (kv.Key < lowTick ||
kv.Key > highTick) continue;` descarta, por cada barra primaria, los ticks de
la subserie de 1 tick reconstruida que caen fuera de `[Low[0], High[0]]` de
**esa barra específica** -- sin reasignarlos. Si la subserie de 1 tick y la
barra primaria desincronizan en el borde (la misma familia de defecto que
`TICKBAR-001` documentó para otro indicador, a otra resolución), ese puñado
de ticks se pierde del lado NT8 sin más. El kernel Python
(`edgelab/bridge/indicators/avolclusterpoi.py::run()`) no tiene ese filtro:
suma directo `footprints.total[bar]`, así que nunca pierde esos ticks.

## Por qué esto ya no es "sensibilidad de mediana a ruido genérico"

La versión anterior de este hallazgo (`AVOLCLUSTERPOI_PARITY_NQ0626_TASKS123_FINDINGS_2026-09-01.md`,
tarea 3) dejaba la causa como hipótesis -- "sensibilidad del estadístico
mediana a diferencias de footprint ya documentadas", sin poder distinguir
"ruido disperso" de "ticks completos ausentes" porque el oráculo no exportaba
`blockCells`. Con el dato real ahora se ve que **no es ruido disperso
uniforme**: es la combinación de un ruido chico y constante (mecanismo 1,
explica los casos leves) más una pérdida de ticks de borde de magnitud
variable (mecanismo 2, domina cuando aparece y explica por qué el mismo
kernel produce a la vez diffs de 1 tick y de 8). El caso `27` -- sin ningún
tick ausente, sólo con ruido -- es la prueba de que el mecanismo 1 solo no
alcanza para producir un diff de 8 ticks; hace falta el mecanismo 2.

## Lo que esto SIGUE sin decidir

- No reclasifica el gate. `FAIL` se mantiene.
- No dice qué tolerancia (si alguna) es aceptable -- eso sigue siendo decisión
  de Nico, ahora con el mecanismo real en la mano en vez de una hipótesis.
- Si se corrige el `.cs` (reasignar el tick de borde a la barra correcta en
  vez de descartarlo), es un cambio de comportamiento del indicador en
  producción -- no se decide acá.
- No se verificaron los 57 `MISSING_IN_NT8` ni el resto de los 19
  `GEOMETRY_DIFF` con este mismo cruce (se hicieron 3 casos como muestra
  representativa: el outlier más grande y dos casos típicos de la lista).
  Extenderlo a los 19/57 completos es directo con el CSV ya exportado
  (`data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv`) --
  no se hizo todavía por no haber sido pedido explícitamente más allá de la
  muestra.
