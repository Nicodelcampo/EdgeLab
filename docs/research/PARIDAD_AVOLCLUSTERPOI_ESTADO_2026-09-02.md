# Paridad aVolClusterPOI — estado al 2026-09-02

> **SUPERADO PARCIALMENTE — leer primero `PARIDAD_AVOLCLUSTERPOI_INDICE.md`.**
> Existe una segunda línea de trabajo en la rama
> `research/avolcluster-nq-parity-oracle-20260901` (commit `6f4e32f`) que corrigió
> el puente y reporta paridad certificada. Este documento conserva el
> **diagnóstico** (fases F2–F9), que sigue vigente y que esa línea confirma en lo
> estructural, pero su veredicto de abajo **ya no es el estado del proyecto**.
> El índice explica qué aporta cada línea y qué reservas quedan abiertas.

**Veredicto de esta línea al 2026-09-02, hoy superado: NO VALIDADA.** Mejor configuración conocida: 15,27 % de bloques
idénticos (3.436 de 22.507), contra 0,07 % (16) del kernel actual.

Este documento es el punto de entrada de la campaña de paridad. Las siete actas
por fase están en `docs/research/avolcluster_*_20260902/`.

## Qué se sabe ahora y no se sabía ayer

El kernel Python difiere de NT8 por **dos defectos identificados y un residuo
sin hipótesis viva**:

1. **Lag de perfil de −1 tick.** El tick que cierra la barra en NT8 aporta su
   volumen a la barra siguiente. Aislado, sube los bloques exactos de 16 a 2.118
   (9,41 %).
2. **Filtro `Low[0]/High[0]`** de `aVolClusterPOI.cs` (~319-330), que descarta
   sin reasignar. Aislado no hace nada; **junto con el lag** sube a 3.436
   (15,27 %) y descarta 15.239 ticks, reproduciendo el déficit de volumen de
   0,41 % que se había medido por separado (0,9964 obtenido contra 0,9959).
3. **Residuo (84,7 %)**: 3,5 celdas difieren de 93,6 por bloque, en el medio del
   rango de precio, plano a lo largo de la sesión. Es un desajuste de frontera
   de barra por pocos ticks, variable y autocorregido.

## Cadena completa de fases

| fase | pregunta | veredicto | acta |
|---|---|---|---|
| F2 | ¿las barras están desalineadas? | **refutada** — offset 0 al 99,98 %, Δt mediano 0 ns | `avolcluster_alignment_20260902/` |
| F3 | ¿el filtro `Low/High` explica la divergencia? | refutada **como causa aislada** (descarta 0 ticks) | `avolcluster_lowhigh_20260902/` |
| F4 | ¿hay una fase global en la partición? | real pero parcial: `k=−1` da 9,01 % | `avolcluster_phase_20260902/` |
| F5 | ¿NT8 y el parquet ven los mismos ticks? | sí — el desvío es una **pérdida** sistemática de 0,41 % en las 51 sesiones | `avolcluster_conserv_20260902/` |
| F6 | ¿lag + filtro juntos? | **confirmado**: 15,27 %, efectos aditivos, reproduce el déficit | `avolcluster_lagfilter_20260902/` |
| F7 | ¿dónde vive el residuo? | chico, en el medio, plano: ni filtro ni deriva | `avolcluster_residual_20260902/` |
| F8 | ¿NT8 respeta grupos de timestamp? | **refutada** — destruye el emparejamiento | `avolcluster_tsgroup_20260902/` |

Todas las corridas: Kaggle, commit pineado `706c4fe2`, CSV NT8 sha256
`81f32a97…f9da`, `code_modified: false`, `holdout_accessed: false`. No se tocó
el `.cs` ni el kernel Python en ninguna fase.

## Dos reaperturas honestas registradas

- La FASE 3 declaró muerto el filtro `Low/High`. La FASE 5 **lo reabrió**: la
  refutación valía sólo bajo el supuesto de que el perfil coincide con la barra,
  y ese supuesto se cayó. Aplicación de la regla de alcance preciso en la
  dirección incómoda.
- La FASE 2 midió timestamps y dio 0 ns de diferencia; eso **no** probaba
  alineación, porque el 51 % de los ticks comparte timestamp y una barra
  desfasada cierra en el mismo nanosegundo. La medición no tenía resolución para
  la pregunta que parecía responder.

## El código fuente confirma los dos defectos

Leído después de las mediciones, `aVolClusterPOI.cs` (~288-331) contiene ambos:
el perfil se acumula en la **subserie de 1 tick** (`Volumes[1]`, `Closes[1]`) y
se vuelca cuando cierra la **barra primaria** — el orden de entrega entre las dos
series decide de qué barra es cada tick, y es el lag −1. Y el volcado descarta
sin reasignar lo que cae fuera de `[Low[0], High[0]]`, con el comentario del
propio autor: *defensa de borde* — es la pérdida de 0,41 %.

Los dos defectos hallados a ciegas por el barrido están escritos en el código.
El diagnóstico queda cerrado; lo que no cierra es la **cantidad**, porque el
orden de entrega entre series no es constante — y esa variabilidad es exactamente
la firma del residuo de la FASE 7.

## Qué hace falta para cerrar (requiere decisión de Nico)

El parquet no contiene la información que diría dónde puso NT8 la frontera de
cada barra. La vía directa es **logging aditivo** en `aVolClusterPOI.cs`, por
barra y no por bloque: `bar_first_tick_time`, `bar_last_tick_time`,
`bar_tick_count`. No cambia la lógica del indicador. Con eso, la frontera deja
de ser hipótesis y la paridad se cierra o se explica en una corrida.

Toda modificación del `.cs` se consulta con Nico — por eso queda pedida, no
hecha. El bloque exacto, con cabecera y criterio de refutación, está escrito en
`docs/research/P70_PROPUESTA_LOGGING_POR_BARRA_aVolClusterPOI.md`.

## Qué NO hacer mientras tanto

Correr barridos de parámetros sobre aVolClusterPOI. Con 15,27 % de paridad, el
barrido mide un indicador que no es el que corre en el chart, y cualquier
resultado sobre esa familia es no promovible. La familia sigue fuera del embudo.

## Aporte al referente

La segunda familia viva del proyecto estaba bloqueada por una no-paridad sin
diagnóstico. Hoy el bloqueo tiene mecanismo medido, magnitud (15,27 % contra
0,07 %), residuo caracterizado y una acción concreta de una línea de logging que
lo cierra. La distancia hacia poder medir un edge sobre aVolClusterPOI bajó de
"causa desconocida" a "falta un dato que NT8 puede exportar".
