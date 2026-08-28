# HANDOFF 2026-08-21 — estado completo y cómo seguir sin este chat

> **Punto de entrada operativo vigente.** Reemplaza a
> `docs/research/HANDOFF_AUDITORIA_2026-08-14.md`.
>
> Escrito para que el proyecto continúe **sin acceso a la conversación que lo produjo**.
> Todo lo afirmado acá está en un artefacto versionado; nada depende de recordar algo.

- **Rama**: `foundation/f0b-compatibility-probe` · **HEAD al escribir**: `47f9116`
- **Holdout `2026-07-01 → 2026-12-31`: INTACTO.** Ninguna medición de esta sesión lo tocó.
- **Detector `HFTZonesESPureV2Flat`: NO modificado.** Sigue congelado.

---

## 1. Qué se estaba haciendo, en una frase

Averiguar si las zonas que dibuja `HFTZonesESPureV2Flat` sobre ES **significan algo**,
comparando cada zona contra **una banda casi idéntica que el indicador no marcó**.

No hay estrategia, ni reglas, ni P&L. Se está validando la materia prima.

## 2. Resultado de la familia: cinco mediciones, ninguna positiva

| # | qué se midió | resultado | artefacto |
|---|---|---|---|
| 1 | ¿el precio frena en la zona? | no (~96 % de ruptura) | 6E, F2.x — **no transporta a ES** |
| 2 | ¿el precio vuelve? | vuelve 99,7 % — **y el control era inválido** | `retorno_a_zona_es.json` |
| 3 | volumen dentro → excursión | ρ ≈ 0 | `h_es_vol_1.json` |
| 4 | **costo de cruce** | **equivalencia declarada** ±7,91 | `r3_inferencia_cruce_es.json` |
| 5 | **costo de cruce condicionado** | **sin efecto**; 2 celdas sin potencia | `h_es_ctx2_condicionado.json` |

**Estado formal de la familia: `SIN EFECTO DETECTADO, NO CERRADA`.**

La condición de cierre pre-registrada exigía equivalencia en los tres terciles de
volatilidad. **Sólo uno la alcanzó**; `bajo` y `alto` tienen MDE 14,5 y 9,6 contra un
margen de 7,91 — están **sin potencia**, no positivos.

**Lo que falta para cerrarla es dato, no análisis**: más sesiones, o sea otra exportación
de oráculo desde NT8 (P-53: el límite es N, no el modelo).

## 3. La cadena de artefactos, en orden

Cada uno se selló con **Commit A (código+tests) → rerun limpio desde worktree detached →
Commit B (JSON+docs)**, y cada JSON declara `run_id`, `run_scope`, `publishable`,
denominadores, `B`, `seed` y procedencia.

| etapa | artefacto | qué dejó |
|---|---|---|
| **R1** | `memoria_nivel_nulo_correcto.json` | memoria de nivel **no sobrevive** al nulo corregido: p mediana **0,1796** |
| **R2** | `r2_matchability_es.json` | **el emparejamiento descarta las zonas anchas** (SMD del ancho **−1,067**) |
| **R3** | `r3_inferencia_cruce_es.json` | **equivalencia** +0,583, IC90 dentro de ±7,91 |
| **Atlas F1** | `atlas_hft_es.json` + `data/atlas/atlas_hft_es_full.parquet` | 370.631 filas, 3 poblaciones, 39 columnas, cero POST |
| **CTX-2** | `h_es_ctx2_condicionado.json` | sin efecto en ningún contexto |

Protocolos congelados: `R3_INFERENCIA_CLUSTERIZADA_PROTOCOLO.md`,
`H-ES-CTX-2_PREREGISTRO.md`. `H-ES-CTX-1_PREREGISTRO.md` quedó `SUPERSEDED` con sus seis
defectos listados.

## 4. Los cinco errores propios que se encontraron y corrigieron

Están documentados porque son la parte reutilizable.

1. **Control espejo degenerado.** Se construía «a la misma distancia del precio de
   creación, del otro lado» — pero la zona *es* el rango del barrido, que termina adentro.
   Distancia mediana 1 tick, **39 % en cero**: el espejo caía encima de la zona. Invalidó
   el control de las mediciones 2 y 3.
2. **Diferencia de medianas en vez de contraste pareado.** Daba +113 ticks donde lo
   pareado daba +0,0.
3. **Denominador heterogéneo.** «El control cruza 78,7 %» era dividir por todas las zonas
   en vez de por las emparejadas. Real: 96,4 % contra 96,6 %.
4. **Redondeo asimétrico.** `np.round(mid)` colapsaba medios ticks en el observado pero no
   en el nulo → el «71 % de sesiones significativas» era artefacto. Real: 31 %.
5. **Estimador `count/B`.** Publicaba `p = 0,0` en 5 de 59 sesiones, imposible con B=400.
   Corregido a `(1+c)/(B+1)`; `0,1775` quedó `RETRACTED_INVALID_ESTIMATOR_COUNT_OVER_B`.

**Ninguno lo habría cazado un gate**: los cinco producen números plausibles.

## 5. Incidente operativo cerrado

`docs/incidents/INCIDENTE_JUNCTION_WORKTREE_2026-08-21.md`

`git worktree remove --force` **siguió una junction de directorio** y vació
`data/nt8/ES_parquet/` — 4.004.759.221 bytes. **Restaurado y verificado byte a byte**
contra mediciones previas al borrado; pérdida definitiva ninguna.

**Regla permanente**: nunca una junction ni symlink de directorio dentro de una worktree
temporal; sólo hardlinks de archivo. Mejor aún: **no enlazar** — los scripts nuevos
aceptan `--snapshot` y `--parquet`.

## 6. Estado del código

```
edgelab/bridge/kernels/hftzones_es_pure_v2_flat.py   puerto NT8->Python, paridad 99,95%
diag/tasa_senales/r2_matchability_es.py              auditoría de emparejamiento
diag/tasa_senales/r3_inferencia_cruce_es.py          bootstrap clusterizado + TOST
diag/tasa_senales/atlas_hft_es.py                    atlas target-free
diag/tasa_senales/h_es_ctx2_condicionado.py          medición condicionada
diag/tasa_senales/memoria_nivel_nulo_correcto.py     nulo de memoria de nivel
tests/research/test_{memoria_nivel_r1,r2_matchability,r3_inferencia,atlas_hft,ctx2_condicionado}.py
```

**Suite: 88 tests nuevos, todos en verde.** Un ERROR preexistente y ajeno:
`test_prerange_sweep_formal.py::test_placebos_and_gates` (YM prerange).

El puerto corre sobre **ticks crudos**: el `.cs` declara `AddDataSeries(Tick, 1)`, así que
el gráfico de 25 Tick era sólo dibujo. **Ya no hace falta NT8 para reproducir el indicador.**

## 7. Qué sigue — dos frentes que no compiten

### Frente A — captura de L2 (pedido a Nico, en curso)

La literatura señala que la señal más fuerte está en el libro de órdenes, y **no lo
tenemos**. Es un techo duro que ningún análisis sobre ticks levanta.

**Lo pedido**: `ES 03-26`, **2026-02-09 a 2026-02-20** (10 sesiones), con
`trades` + `BBO con bid_size/ask_size`, **exportado del mismo NT8 que graba el L2**.

**El problema a resolver primero**: los ticks actuales vienen de Lucid y el L2 vendría de
NT8. **Son feeds distintos y no se pueden unir por timestamp** — ya medimos 182 ticks en
un mismo milisegundo. Por eso la primera tarea es un **test de unión de feeds**, no un
análisis.

Primer uso, si los feeds cuadran: **auditar el lado agresor**, que hoy se *infiere* con
la regla del tick y está metido en todo lo medido.

### Frente B — la familia HFT

Dos salidas, y la decisión es de Nico:

- **Cerrarla**: aceptar «sin efecto detectado» y mover el esfuerzo. Es lo que yo
  recomiendo: cinco mediciones, ninguna positiva.
- **Completar el cierre**: pedir más sesiones de oráculo para dar potencia a los terciles
  `bajo` y `alto`. Cuesta una exportación NT8 y sólo sirve para poder decir «cerrada» con
  todas las letras.

### Frente C — diseñado, no ejecutado

`H-ES-HFT-BT2-ATLAS-1` (HFT × BigTrap2 multiescala) está **diseñado en detalle** dentro
del embudo del playbook, y **bloqueado**: la paridad de BigTrap2 **sobre ES no existe**
(sólo está medida sobre 6E). Ver `docs/research_funnel_playbook.md`.

**Y el atlas ya descartó un control que ese diseño daba por bueno**: `S1_1MIN` tiene
**9 ticks de ancho mediano contra 3 de la zona** y la mitad de volatilidad previa. Usarlo
sin emparejar repetiría el error que R2 midió.

## 8. Lo que NO está medido — leer antes de proponer nada

`docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md` es el registro vivo. Los frentes
abiertos, resumidos:

1. **Ejecutabilidad: cero.** No hay reglas de entrada/salida, sizing, fricción para ES ni
   fills. La cadena `geometría → información → P&L bruto → edge neto` está frenada en el
   primer eslabón.
2. **El estimando sobre soporte completo.** El control sólo existe para el 81,7 %, sesgado
   a zonas angostas. Tres salidas posibles, ninguna elegida.
3. **Otros instrumentos.** Todo es ES 03-26. **Nada** se transporta.
4. **Barrido de parámetros del indicador**: no hecho.
5. **Co-ocurrencia con otros indicadores**: no medida.
6. **`aVolCellPOI2`**: paridad en FAIL (P-42), aparcada.

## 9. Reglas que esta sesión dejó como práctica

Están formalizadas en `docs/research_funnel_playbook.md` (ATJ-01…ATJ-16). Las que más
costaron:

- **ATJ-14** sellado en dos commits: código → rerun limpio → resultados. Prohibido que un
  commit corrija la fórmula y deje el JSON viejo citado como nuevo.
- **ATJ-15** lineage de denominadores: universo, seleccionadas, disponibles, procesadas,
  elegibles, `missing_items[]`, `excluded_items[]`, `B`, `seed`, `run_id`. Las exclusiones
  se **computan**, no se hardcodean en un comentario.
- **ATJ-16** etiqueta epistémica: `MEASURED_COMMITTED`, `INFERRED_NOT_VERIFIED`,
  `RETRACTED`… Una inferencia nunca se redacta como procedencia verificada.
- **Publicar el MDE antes de mirar el punto.** Es lo único que impidió leer
  `bajo +3,5` y `alto +4,5` como un hallazgo.

## 10. Reproducir cualquier resultado

```bash
.venv\Scripts\python tools\estado.py
.venv\Scripts\python -m pytest tests/research -q
```

Cada script acepta `--max-sesiones N --out <ruta>` para una prueba rápida; una corrida
truncada **aborta** si intenta sobrescribir el artefacto canónico, y se marca
`run_scope=truncated_probe, publishable=false`.

Datos: snapshot `runs/oraculo_espurev2flat_ES_snapshot.sqlite`
(sha256 `a7dec2ee382c32ea…`), parquet `data/nt8/ES_parquet/ES_03-26_ticks.parquet`
(sha256 `948067cf…`, 991.106.327 bytes). Los dos gitignorados; los hashes están en los
artefactos.
