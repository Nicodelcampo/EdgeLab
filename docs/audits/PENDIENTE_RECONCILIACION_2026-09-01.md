# Reconciliación de PENDIENTE.md — 2026-09-01

## Veredicto

La restauración del board hecha en esta rama no fue íntegra. El commit `bca71898`
instaló una reescritura condensada de 15.003 bytes (blob `f924a60d`) y no el contenido
preexistente. La verificación posterior probó que **un archivo** había aterrizado, pero
no que sus contenidos fueran los originales.

## Linaje verificable

| Revisión | Rama verificada | Alcance |
|---|---|---|
| `e2e0cf40d4606fadb836878bbed304e4f0c40ea0` | `research/bt2a-nq-gate1-nrand-capacity-t2-20260830` | board largo P-01…P-57, 108.777 B |
| `252215c11b89252400919d16464454bcff7306bb` | `foundation/f0b-compatibility-probe` y `research/avolcluster-nq-parity-oracle-20260901` | revisión posterior P-01…P-59, 112.595 B |
| `f924a60dc7b98d075ed98f8cb9cc07ec0928af00` | rama de auditoría | sustitución condensada, 15.003 B; no canónica |

La revisión `252215c1` conserva las entradas tempranas P-56/P-57 del 21-ago y P-58/P-59
del 26-ago. Por precedencia temporal, esas numeraciones no se mueven.

## Mapa de renumeración

| Registro de auditoría anterior | Número corregido |
|---|---|
| Tres palancas de ejecución liviana | P-60 (antes P-58 en canal 017) |
| ML/LightGBM como generador de hipótesis | P-61 (antes P-59 en canal 018) |

Este acta **no inserta todavía** P-60/P-61 en el board canónico: evita otra copia y deja
la mutación para quien trabaje directamente sobre la rama canónica. Hasta entonces, el
contenido y su procedencia siguen en los documentos de research citados por los canales
017/018.

## Cuarentena de procedencia

Las siguientes entradas exclusivas de la reescritura condensada no se trasladan al
board canónico porque sus artefactos citados no aparecieron ni en la rama de auditoría
ni en la rama foundation, y las búsquedas de repo no aportaron evidencia independiente:

- barras 15m descartadas;
- prototipo standalone 5m;
- cola first-touch H4b;
- frase «detección separada de ejecución»;
- ingesta Dukascopy supuestamente auditada;
- descarte de fuentes públicas de ticks CME.

En particular no resolvieron los paths
`docs/research/RESEARCH_PUBLIC_TICK_DATA_SOURCES_2026-08-16.md`,
`docs/GAPS_DUKASCOPY_NT8.md`, `data/registry/` ni
`tools/audit_nt8_dukascopy.py` en las ramas examinadas. Cuarentena no significa
falsedad: significa **procedencia insuficiente para numerarlas como hechos del repo**.

## Regla permanente

1. Un solo board canónico por linaje activo.
2. Próximo número libre; ante colisión conserva el número el registro verificable más
   temprano.
3. Verificar identidad del contenido (blob/linaje), no sólo existencia, tamaño o éxito
   del push.
4. Un canal que introduzca un P-NN debe asentar la entrada en el board canónico en el
   mismo commit o declarar explícitamente que queda pendiente.
