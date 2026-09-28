# Propuesta de unificación — visor, corredores y lo que está separado

> 2026-09-21 · rama `feat/unified-viewer-canonical-20260921` (parte del head del PR #48,
> `ba970b3`; **sin upstream a propósito**, para que un `git push` descuidado no pise al PR #48).
> Pedido de Nico: *«una única verdad, una única versión de cada cosa; usar la definición
> canónica certificada»*. Holdout `1782856800000000000` intacto; nada de esto abre outcomes.

## 0. Estado en una mirada

| | |
| :-- | :-- |
| **Hecho** | Copias de seguridad de todo lo sin commitear · fusión de las 3 variantes de `index.html` · 2 conflictos de política resueltos · 1 bug latente corregido · manifiesto corregido · 21 tests verdes |
| **Falta y necesita tu decisión** | Qué fórmula es *la* definición canónica de corredor (§3) — es la única decisión que bloquea el cableado |
| **No verificado** | Playwright/CI del repo · que el motor JS coincida con Python · el resto de los activos en el navegador (solo se abrió 6B 09-25) |

## 1. Qué había separado

### 1.1 Cuatro versiones vivas de `index.html`, ninguna contenía a las otras

| Hash | Dónde vivía | Contenido |
| :-- | :-- | :-- |
| `e7fed527` | `foundation` y otras 32 ramas | base |
| `ad78a77e` | PR #48 | base + flechas de señal causales (+176 líneas) |
| `2a3685f0` | **solo en disco**, checkout principal | inicio causal, abstención por `bar_key`, bordes exteriores |
| `bff07dab` | **solo en disco**, `E:/EdgeLab-multiasset` | lo anterior reimplementado + perfil de densidad + catálogo multiasset (+289/−48) |

Las dos variantes locales no estaban en ninguna rama. Quedan respaldadas (no destructivo,
índice temporal, solo local) en `backup/wip-main-checkout-20260921@fa5b3823` y
`backup/wip-multiasset-worktree-20260921@5c8e5e5e`; los `index.html` respaldados coinciden
byte a byte con los del disco. El respaldo de `multiasset` además contiene WIP que **no es
del visor** (`bigtrap2absorption.py`, `nt8_contract.py`, ~40 herramientas de auditoría) y que
sigue esperando dueño.

### 1.2 Lo de "25t para todos los activos" no es código

El visor es el mismo. Cambian los **datos**: 342 archivos / 12 GB / 147 entradas de
manifiesto en `multiasset`, contra 24 entradas / 625 MB en el checkout principal. No están en
git por la decisión `NO_UPLOAD_VIEWER_BUNDLES` (Tier 3, se generan bajo demanda). Los 155
bundles `*_25T_HFT` traen los campos causales (`available_ns`, `origin_ts_ns`, `end_ts_ns`,
`contract`, `session_id`) con **nombres distintos** a los que pide el motor certificado
(`available_ts`, `origin_ts`, `end_ts`, `lo`, `hi`, `direction`): es un renombrado, no una
invención de semántica.

### 1.3 Los corredores tienen al menos cinco implementaciones

| # | Dónde | Qué calcula | Certificación |
| :-- | :-- | :-- | :-- |
| 1 | `index.html` · `drawCorredoresDemo` | «muros vivos» + `hMin` + modo consumo | ninguna |
| 2 | `corridor_engine.js` | σ=2, peso `vol·0,5^(edad/12h)`, corredor = tramo bajo el percentil 25, 8–32 ticks | invarianza de viewport y causalidad; **solo lo usa `hft_corridor_certified.html`** |
| 3 | `edgelab/research/density_field.py` | HP-007 `D(p,t)`: σ=1,2, pesos configurables, `V_ref` causal, umbrales normalizados | 15 invariantes; el efecto HP-007 se midió con esto |
| 4 | `crosshair_density_profile.js` + `buildCrosshairDensityRanges` | misma gaussiana que (2), con rangos calculados en el HTML (corte de 48 h, rebanadas de consumo) | ninguna |
| 5 | `hft_corridor_preview.html` | campo inline con kernels/transformaciones | ninguna |

El manifiesto del PR #48 declaraba `hft_liquidity_corridors: INTEGRATED`, pero `index.html`
tiene **0 referencias** a `EdgeLabCorridorEngine`, y su test solo buscaba strings. Ahora
declara `NOT_UNIFIED_MULTIPLE_IMPLEMENTATIONS`.

## 2. Qué se hizo, con evidencia

1. **Respaldo** de ambos árboles antes de tocar nada (§1.1).
2. **Fusión a tres bandas** de `index.html` (base `e7fed527`, PR #48, WT multiasset): dos
   conflictos, ambos adiciones independientes que competían por el mismo punto de inserción.
   *Los fines de línea (CRLF) producían un falso conflicto que abarcaba todo el archivo.*
3. **Choque de políticas nº 1 — `bar_key`.** El WT tenía un `return` (una corrida solo se
   dibuja sobre su serie) *antes* del bloque de flechas causales del PR #48, que solo corre
   cuando la serie difiere: las flechas quedaban como código muerto. Ahora, en desajuste, se
   suprimen las **cajas** (retrospectivas) y se conservan las **flechas** (causales).
4. **Choque de políticas nº 2 — disponibilidad.** `test_scientific_zones_have_no_t0_fallback`
   exige que las zonas científicas no caigan a `t0`; el WT las mostraba con una insignia
   «EXPLORATORY». No se tocó el test (el repo prohíbe relajar gates). La política estricta es
   el default; lo exploratorio es una casilla opt-in, y las zonas ocultas se **avisan**
   («N zonas ocultas: sin available_ts explícito»), no se ocultan en silencio.
5. **Bug latente encontrado por la propia unificación.** El WT declaraba `densityTsSec` y
   `zoneAvailabilityInfo` **dos veces** en el mismo alcance; en JS la segunda (sin `quality`)
   pisa a la primera, así que la insignia EXPLORATORY era **inalcanzable**. Su test no lo
   veía porque evalúa solo la primera definición. Corregido y clavado en
   `tests/research/test_unified_viewer_invariants.py` (que además **falla** contra la variante
   original del WT).
6. **Verificación en navegador real** (Chrome del panel, sin errores de consola): 147 activos
   en el catálogo; con disponibilidad → 0 ocultas; quitándola en memoria → **3.239/3.239
   ocultas con aviso**; con el modo exploratorio → 0 ocultas; al restaurar → 0.
7. Tests: `test_unified_viewer_manifest` · `_invariants` (5, nuevos) · `_viewer_causal_zone_start`
   · `_viewer_zone_outer_borders_only` · `_crosshair_density_profile_js` · `_corridor_engine_js`
   · `_density_profile_availability_semantics` → **21 passed**. Los dos tests de «parche» se
   adaptaron **solo** para aceptar `ALREADY_APPLIED` (el parche ya está en el archivo); todas
   sus aserciones sobre el resultado quedaron idénticas.

## 3. La decisión que bloquea el cableado: ¿cuál es «la definición canónica certificada»?

No es una sola cosa. Hay **dos certificaciones sobre dos fórmulas distintas**, y nunca se
validaron entre sí (el único test cruzado Python↔JS, `test_density_field_cross_validation.js`,
valida una tercera implementación que vive dentro del propio test, solo para el baseline
`FIELD_RAW_STATIC`).

| | A · `corridor_engine.js` | B · `density_field.py` (HP-007) |
| :-- | :-- | :-- |
| Kernel | gaussiano σ=2 ticks | gaussiano σ=1,2 ticks |
| Peso | `vol · 0,5^(edad/12 h)` | 1,0 (baseline) o bimodal: `f_vol·f_mat·f_decay·f_wear·pen` con `V_ref` causal |
| Corredor | tramo contiguo bajo el **percentil 25** de la densidad, 8–32 ticks | `D ≤ umbral` normalizado en [0,1], ≥ 7 ticks |
| Qué certifica | invarianza de viewport, causalidad, holdout, sin volumen por nivel | 15 invariantes; **es el objeto con el que se midió HP-007** (3,03× de velocidad) |

**Recomendación.** B como *definición* (es lo que la investigación midió; mostrar otra cosa
sería dibujar un objeto que nadie evaluó) y los *gates* de A como *contrato* que toda
implementación debe cumplir. Concretamente: reescribir `corridor_engine.js` como un **puerto
fiel** de `compute_field` + `detect_density_intervals`, con vectores dorados generados desde
Python y una prueba de igualdad ≤ 1e-9, y volver a correr la auditoría de `hft_corridor_certified`.
Es la misma regla que ya rige el repo (`tools/visor_server.py`: no puede haber un segundo
implementador del mismo objeto; el que diverge sería el que se mira).

**Si preferís A**, el cableado es más corto pero el visor pasa a mostrar corredores cuya
definición no es la de HP-007, y eso debería quedar rotulado en pantalla.

Consecuencias de usar *cualquiera* de los dos como única verdad:
- Los «muros vivos» de `drawCorredoresDemo` y el **modo de consumo por volumen para
  corredores desaparecen**: el motor certificado declara `volume_by_level: UNAVAILABLE_FAIL_CLOSED`
  y prohíbe repartir volumen uniformemente. (El dibujo de consumo de las *zonas* individuales
  no se toca.)
- Solo se computan corredores para zonas con esquema causal completo. Los bundles `_25T_HFT`
  entran vía renombrado; el bundle legacy de BigTrap2 (6E, sin `available_ts`) **se abstiene**.
- `crosshair_density_profile.js` se elimina: el perfil del crosshair es `field.density`
  as-of la hora del cursor, del mismo módulo.

## 4. Plan por fases (cada una con su gate)

| Fase | Contenido | Gate |
| :-- | :-- | :-- |
| **F1 — hecha** | Un solo `index.html`, sin funciones duplicadas, políticas reconciliadas | 21 tests + navegador |
| **F2** | Capa adaptadora (renombrado de claves, sin fabricar campos) + cablear `index.html` a **un** módulo; borrar `drawCorredoresDemo` y `buildCrosshairDensityRanges` | el `economicHash` del visor = el de la página certificada (`9339e80c` a σ2/h8/32/12h/tref650‰) |
| **F3** (si B) | Puerto de `density_field.py` a JS + vectores dorados | igualdad ≤ 1e-9; auditoría re-corrida |
| **F4** | Retirar duplicados (§5) | ninguna referencia viva; `git grep` limpio |
| **F5** | Un solo constructor de bundles y un solo esquema de manifiesto; regenerar `_CONT` con `available_ts` desde Tier 1/2 en Kaggle | `verify` de hashes fuente |
| **F6** | Integrar: esta rama reemplaza al PR #48; CI verde antes | orden del mapa del agente A |

## 5. Otras cosas separadas (fuera del visor)

- **Indicadores NT8 de clusters: divergieron otra vez.** En la máquina, `HFTClusterZonesNQ`
  es v2.0.0 (129 KB) y `HFTClusterZonesNQDx` v1.7.0 (183 KB), con **932 líneas de diferencia**
  entre ellos; el repo tiene v1.1.0 (98 KB) y 115 KB. De nuevo, lo que corre ≠ lo registrado.
  Propuesta: dejar **uno** (`HFTClusterZonesNQ`), versionarlo desde la máquina y retirar `Dx`.
- **Páginas del visor a retirar/archivar:** `hft_corridor_preview.html` (+ `hft_nq_bundle.js`,
  `tools/build_hft_corridor_bundle.py`), `viewer/hz2a` + `tools/visor_server.py` (agosto, hoy en
  `.claude/launch.json` y ausentes de `specialized_noncanonical_pages`), las herramientas
  `tools/apply_viewer_*` y sus tests de parche (su trabajo ya está en el archivo), y las 3 copias
  `index.before-*.html` que carga el WT (**no se trajeron**).
- **Python:** dos módulos de densidad (`density_field.py`, `corridor_campaign_v2.py::directional_field`)
  más `liqheat.py`. Definir cuál es referencia y hacer que los otros la importen.
- **Documentos rectores desactualizados:** `AGENTS.md`/`PROJECT_INDEX.md` (2026-09-02),
  `docs/CURRENT.md` (2026-09-17). La gobernanza de Kaggle está inconsistente entre documentos
  históricos y el último handoff; el estado vigente (análisis en Kaggle, acceso de escritura
  verificado el 2026-09-21, `NO_UPLOAD_VIEWER_BUNDLES` vigente) debería quedar en un solo lugar.
- **Ramas:** ~130 refs y ~30 worktrees. No se borra nada sin tu orden; tras F6 propongo una
  lista de ramas absorbidas para que la apruebes.

## 6. Decisiones que necesito

1. **Fórmula canónica del corredor:** A (`corridor_engine.js`) o B (`density_field.py`).
   *Recomiendo B como definición + puerto verificado, con los gates de A.*
2. **Política de disponibilidad por defecto:** estricta (implementada) o exploratoria visible
   como en el WT. *Efecto de la estricta:* el bundle legacy de 6E muestra 0 zonas con aviso hasta
   regenerarlo con `available_ts`.
3. **Retirar el modo consumo por volumen para corredores** (lo exige el motor certificado).
4. **Archivar** `hft_corridor_preview.html`, `hz2a`/`visor_server.py` y los parches `apply_*`.
5. **Un solo indicador NT8 de clusters** y cuál (recomiendo `HFTClusterZonesNQ`).
6. **Integración:** esta rama como reemplazo del PR #48, con CI verde antes.

## 7. Riesgos y límites

- No se corrió Playwright ni el CI completo; los 21 tests son unitarios/estructurales más una
  prueba manual en el navegador.
- La política estricta cambia lo que se ve por defecto en bundles legacy.
- `E:/EdgeLab-unified-viewer/viewer/nt8_bridge/bundles` es un *junction* al de `multiasset`
  (ignorado por git); si se borra ese árbol, el visor unificado pierde sus datos.

**Aporte al referente:** reduce a una sola las cuatro versiones del visor, corrige un defecto que
ocultaba una advertencia causal, y deja explícito —antes de cablear nada— que la «definición
certificada» de corredor son dos fórmulas distintas, para que el visor no muestre un objeto que
la investigación no midió.
