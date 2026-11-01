# Decisión: las 12 campañas en CONTEO y los kernels de SV1 (2026-11-01)

Estado: VIGENTE. Fecha: 2026-11-01. Decide la sesión en la nube por delegación expresa de Nico («resolvé vos lo anterior, tomá vos la
decisión»). Insumos: la confirmación V4 del agente de SV1 (Gonza, 2026-11-01 03:17), su contraste por SSH y el estado del repo
(`config/autopilot/grillas/campanas/`, `docs/research/*/embudo/*/estado.json`). Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Situación
Después del #184, el repo tiene 12 campañas `conductor: debian`, activas, en `PENDIENTE/CONTEO` y sin handle. Si se prende el embudo
(`embudo.activo: true` en SV1), las 12 lanzan su CONTEO solas (`embudo.py`):

| Grupo | Campañas |
|---|---|
| De la canasta de 7 (`PREREGISTRO.md` v2) | CVGAP-NQ, CVGAP-CFD-NQ, U1-ORO-GRILLA, U1-RACIMOS-GRILLA-NQ, U1-YM-GRILLA, U1-ZONAS-AVCL-NQ, U1-ZONAS-NQ |
| Excluidas de la canasta | U1-ES-GRILLA, U1-RACIMOS-GRILLA-ES, U1-ZONAS-BT2-ES, U1-ZONAS-BT2-NQ, U1-ZONAS-ES |

En SV1 hay siete kernels de CONTEO ya lanzados antes de la pausa (consultados por el agente, sin bajar resultados):

| Campaña | Slug (ventana) | Estado |
|---|---|---|
| U1-ES-GRILLA | `...-holdout-conteo-20261001` | complete |
| U1-YM-GRILLA | `...-holdout-conteo-20261001` | complete |
| U1-ZONAS-NQ | `nicobuttaro/...-holdout-conteo-20261001` | complete |
| U1-ZONAS-ES | `...-holdout-conteo-20261023` | complete (ventana vieja) |
| U1-ORO-GRILLA | `...-holdout-conteo-20261023` | error |
| U1-ZONAS-AVCL-NQ | `...-holdout-conteo-20261023` | error |
| U1-ZONAS-BT2-NQ | `...-holdout-conteo-20261023` | error |

## Decisión
1. **Las 12 quedan `activa: false`** en su JSON de campaña, con la nota `nota_20261101`. Eso ya está en este commit. Así, prender el
   embudo para campañas nuevas no lanza ningún CONTEO por accidente.
   - Las 7 de la canasta: su holdout lo mide el pre-registro de la canasta, que es **una** prueba sobre la serie por sesión, con
     revisiones a 20, 40 y 60 sesiones. Un CONTEO y una apertura por campaña duplicarían la mirada sobre la misma ventana y se
     contradirían con ese pre-registro.
   - Las 5 excluidas: se excluyeron después de ver el OOS, y gastar su holdout ahora no suma a la canasta. Su ventana queda **sin
     consumir**. Si alguna vuelve, lo hace con una decisión propia y escrita.
2. **Los 7 kernels de SV1 no se usan ni se relanzan.** Sus handles quedan como rastro en este documento y en el respaldo de SV1
   (`backup_20261101`), sin bajar resultados:
   - Los cuatro con slug `20261023` corresponden a la ventana simulada que la directiva 6 dejó sin efecto. Los tres en error son de esa
     misma ventana.
   - Los tres completos de la ventana `20261001` son conteos por campaña. La decisión 1 los deja sin uso.
3. **El embudo sigue apagado en SV1** (`embudo.activo: false`), como pidió Nico. Puede prenderse cuando haya campañas nuevas para
   conducir: con esta decisión no arrastra ningún CONTEO.
4. **Lo que falta para abrir la canasta de 7**, por su propio pre-registro:
   - **Ruta sellada diaria.** El logger de NT8 sube los ticks diarios al dataset sellado de Kaggle
     (`nt8_tools/EdgeLabLiveTickLogger.cs`, `tools/nt8_sellado_diario.py`). Hoy el dataset sólo tiene ES y NQ hasta el 26 de octubre.
   - **GC sellado**, para U1-ORO, que ejecuta en GC. Es la causa más probable del error de su CONTEO; no está verificada porque no se
     bajó el log.
   - **Calentamiento de zonas sobre el sellado**, para U1-ZONAS-AVCL-NQ y U1-ZONAS-NQ. Los almacenes de zonas cubren sólo el
     desarrollo.
   - **Reconciliación de SV1** (en curso, Gonza) y una prueba de punta a punta del camino de Kaggle sellado.
   La medición de la canasta corre cuando esas cuatro cosas existan, nunca antes. Hasta entonces nadie mira el holdout.

## Qué no se decide acá
No se cambian gates, FDR, mandato ni el protocolo de apertura. No se abre el holdout. No se mira ningún resultado de los kernels de SV1.
