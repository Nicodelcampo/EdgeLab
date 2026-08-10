# REGISTRO DE LO NO MEDIDO — qué se exploró y qué no, explícito

**Fecha** 2026-08-10 · **NORTH_STAR** sha256 `21bb3b01a33e2b37…`
**Motivo** El 2026-08-10 se descubrió que todo el corpus sobre BigTrap2 medía una
sola familia de entradas por herencia (`SESGO_DE_DISENO_2026-08-10_…`). La
lección fue que **lo único que nadie audita es lo que nadie escribió**. Este
documento existe para que eso deje de poder pasar en silencio.

**Regla que lo hace vinculante** — `CLAUDE.md`, «Reglas permanentes»: ninguna
población se congela sin enumerar antes, por escrito, el espacio de eventos y
estados del que se la extrae.

> **Cómo leer este documento.** «No medido» **no** significa «descartado». La
> mayoría de estas dimensiones nunca fueron evaluadas ni rechazadas: quedaron
> fijas porque el primer módulo que las tocó eligió un valor y los siguientes lo
> heredaron. Ninguna tiene una justificación escrita de por qué ese valor y no
> otro.

---

## 1. MEDIDO — inventario de lo que sí existe

| # | qué | resultado | artefacto |
|---|---|---|---|
| M1 | Paridad NT8↔Python de 5 indicadores | 47/47 oráculos, 0 FALTA, 0 DIFIERE | `docs/oraculos_manifiesto.json` |
| M2 | Censo de primeros toques post `sep_min` | 15.577 toques / 201 sesiones | `censo_primeros_toques.json` |
| M3 | Curva de excursión sobre primeros toques | `T` vs eventos; T=34 elegido | `curva_excursion_ticks.json` |
| M4 | `f` con ambos filtros, órdenes A y B | 755 con excursión → 424 orden B | `f_ambos_filtros.json` |
| M5 | **H1**: expectativa neta, T=34, entrada al toque | **MUERTA** −2,4685 ticks, IC contiene 0 | `inferencia_H1__e8fd2b74ba47.json` |
| M6 | Desagregado de H1 por motivo de salida | close_through 394 (**0 ganadores**) · fin sesión 30 (29 ganan) | `ACTA_MUERTE_H1_2026-08-09.md` |
| M7 | Potencia del diseño de H1 | SE(HAC) 1,0903 · *design effect* 1,14 · MDE **6,58 ticks brutos** | ídem |
| M8 | **F0.2** censo completo de zonas | 15.947 zonas · 97,9 % tocadas · **altura mediana 1 tick** · vida 7 barras | `censo_zonas_completo__21b7f3512158.json` |
| M9 | Eventos de toque totales | **48.768**; H1 midió 32 % | ídem |
| M10 | **F2** barrido `ticks_per_row` × `imbalance_ratio` × `min_trap_volume` | tasa de ruptura **invariante**: 95,8–96,9 % en las 12 celdas | `barrido_F2_altura.json` |
| M11 | **F1.2** supervivencia con riesgos competitivos | CIF ruptura 0,9628 · vida mediana ~6 barras · estratificado por altura/volumen/toques | `F1_superv_depletion__b107bf368c08.json` |
| M12 | **F1.3** depleción por índice de toque | 30,3 % (toque 1) → 16,7 % (>10); plano en 1–4 (77 % de la masa) | ídem |
| M13 | **F1.1** nulo contra zonas aleatorias, dos diseños (posición libre / desplazamiento local) | **tocar: real 97,9 % vs nulo-B 51,4 % — 201/201 sesiones.** Romper: casi igual (0,8 pp) | `F1_nulo_zonas_aleatorias__ac9d001dc815.json` |
| M14 | **F0.3** features de estado (`materialize_features`, primer uso en research) | cobertura 99,3 % · `inside_zone` 7,95 % · pico intradía 11-13h CT | `F0.3_features_estado__37db8426120d.json` |
| M15 | **YM** ingesta y habilitación en el bridge (5 contratos, 23,2M ticks) | 0 líneas no parseadas, 0 desorden; huso horario verificado por gap de fin de semana | `data/nt8/YM_parquet/`, `YM_INGESTA_Y_HABILITACION_2026-08-10.md` |

---

## 2. NO MEDIDO — dimensiones congeladas por herencia

### 2.1 ⚠️ Resolución de barra (`bar_spec`) — **la más grande sin explorar**

**Valor único usado: `time:1` (M1).** `build_time_bars(tk, 1)` está
**hardcodeado** en siete módulos de research: `censo_primeros_toques.py:88`,
`curva_excursion.py:148`, `curva_excursion_ticks.py:383`,
`f_ambos_filtros.py:107`, `concordancia_lado_bigtrap2.py:129`,
`censo_zonas_completo.py:257`, `F1_supervivencia_y_depletion.py:173`.

**`build_tick_bars` existe** (`bars.py:94`) **y research jamás lo usó.** Sólo
`medir_tasa.py:70` acepta un `bar_spec` parametrizable, y no se usó para esto.

**Por qué es la dimensión más grande:** BigTrap2 es *bar-driven* + footprint.
Cambiar la barra cambia **toda la agregación del footprint**, o sea el imbalance,
el volumen atrapado, la geometría y el ciclo de vida. Produce zonas
**completamente distintas** — un efecto mayor que el de cualquier parámetro del
indicador.

**Riesgo conocido y no resuelto:** `curva_excursion_ticks.py:103` documenta el
peligro de comparar un `created_bar` de otra `bar_spec` contra `bar_end` de M1.
Alguien vio el riesgo; la respuesta fue **fijar M1**, no explorarlo. Barrer esta
dimensión exige que cada corrida use su propio `bar_end`, que es justamente lo
que ese comentario advierte.

> **No hay ninguna justificación escrita de por qué M1 y no tick-bars, ni M5, ni
> volumen-bars.**

### 2.2 Familias de entrada distintas del toque

Enumeradas en `PLAN_ANALISIS_v2` §2 y **ninguna evaluada**:

| | familia | estado |
|---|---|---|
| E1 | creación de zona | censada (`post_sepmin.py`), **degradada a diagnóstico** el 2026-08-04, nunca evaluada |
| E3 | toque n-ésimo (2º, 3º…) | **33.160 eventos (68 % del total) nunca medidos** hasta F1.3 |
| E4 | invalidación / close-through | **el desenlace del 96 %**, nunca estudiado por derecho propio |
| E5 | expiración por edad | 585 casos, nunca analizado |
| E6 | aproximación sin toque | no medido |
| E7 | confluencia / apilamiento de zonas | no medido |

### 2.3 La zona como ESTADO continuo — ✅ MEDIDO (F0.3)

`materialize_features()` (`features.py`, **2026-07-24**) expone `inside_zone`,
`distance_to_nearest_zone`, `active_zone_count`, `zone_age`,
`nearest_zone_side`. Hasta hoy: cero código de research la usaba. **F0.3 la
corrió por primera vez**, sobre 254.323 barras: cobertura de zona activa
99,3 %, `inside_zone` 7,95 %, patrón intradía coherente con liquidez real
(pico 11-13h CT). Ver `F0.3_FEATURES_ESTADO_RESULTADO_2026-08-10.md`. Deja
un artefacto propio documentado: `zone_age` de la más cercana tiene sesgo de
longitud (mediana 54 barras, muy por encima de la vida mediana de una zona
cualquiera, ~7) — no leer esa mediana como "la zona típica".

### 2.4 Parámetros del indicador nunca variados

De los 12 de `PARAM_SPEC`, el barrido F2 movió **tres** —
`ticks_per_row`/`imbalance_ratio`/`min_trap_volume`— y **la tasa de ruptura no
se movió con ninguno de los tres**: 95,8–96,9 % en las 12 celdas
(`F2_BARRIDO_ALTURA_RESULTADO_2026-08-10.md`). Nunca se varió ninguno de:

`imbalance_mode` (Diagonal/SameLevel) · `trap_volume_source`
(AggressiveSide/TotalLevel) · `use_wick_filter` · `wick_zone_pct` ·
`min_delta_filter` · `min_export_volume` · `invalidation_mode`
(CloseThrough/FirstTouch) · `max_age_bars` · `max_touches`

`invalidation_mode` y `max_touches` merecen nota: **son los que gobiernan cuándo
muere la zona**, o sea la salida — que el acta de muerte identificó como el lugar
donde H1 perdía, y que F1.2 confirmó como propiedad casi universal del objeto
(96,3 % de ruptura, invariante a altura/volumen/toques). Siguen sin tocarse, y
ahora con más motivo: son los únicos parámetros de los 12 con posibilidad
mecánica de cambiar **qué cuenta como ruptura**, no cuántas zonas hay.

### 2.5 Instrumentos — investigado, sigue bloqueado, y ahora se sabe por qué

Sólo **6E** (4 contratos, 201 sesiones) entra a los análisis de research. Se
verificó el estado real de ES, NQ **y ahora YM**: **los parquets canónicos ya
existen para los tres** (`data/nt8/ES_parquet/`, `data/nt8/NQ_parquet/`,
`data/nt8/YM_parquet/` — este último ingerido y habilitado en el catálogo del
bridge hoy mismo, ver `YM_INGESTA_Y_HABILITACION_2026-08-10.md`) — no es un
problema de datos faltantes. **El bloqueo es que `dias_research()` lee el
calendario de estudio desde un archivo de universo que enumera exclusivamente
nombres de contrato 6E** (`post_sepmin.py:109-113`, `cargar_dias_de_estudio`).
Extender el calendario a ES/NQ/YM es, por la regla nueva de `CLAUDE.md`
§Reglas permanentes, una decisión de población que **se enumera y justifica
por escrito antes de tomarse** — no algo para resolver al margen de otra
tarea. Los tres esperan en la misma cola, con el bloqueo identificado y no
sólo nombrado.

Es F3, y sigue siendo la mejora de potencia más barata disponible una vez
habilitada: `SE ∝ 1/√n`.

### 2.6 Reglas de trade nunca variadas (fuera del alcance target-free)

Entrada al **cierre** de la barra (por DEFECTO 001) · salida al close-through o
fin de sesión · **sin take-profit ni stop** · dirección **nativa** ·
`sep_min = 120` · sizing fijo 1 contrato · fricción fija 2,768 ticks.

Ninguna se varió. `sep_min=120` en particular **nunca se justificó ni se barrió**:
descarta el 43,8 % de los eventos con excursión válida.

### 2.7 Ventana temporal

Research 2025-2026 hasta **2026-06-30**. Holdout 2026-07-01 → 12-31 **sellado, no
mirado**. Sin análisis por régimen, ni por hora del día, ni por día de la semana,
ni por volatilidad.

---

## 3. NO EXPLORADO — preguntas que nadie formuló

1. **¿La zona aporta algo sobre una línea horizontal al azar?** **Contestado
   por F1.1: sí, y grande** — en tocar (97,9 % vs 51,4 %), no en romper. Deja
   tres sub-preguntas nuevas, sin urgencia para el plan pero registradas:
   - **¿Es distancia pura o algo más?** La tasa de toque del nulo-B no se
     estratificó por su propia distancia real al precio de creación —no quedó
     ligada zona-a-zona en el artefacto—. Contestaría si alcanza con "estar
     cerca" o si el nivel de imbalance específico aporta algo más.
   - **¿La atracción es inmediata o acumulada?** Se midió con horizonte de
     2.000 barras (~33 h); no se probó con horizontes cortos (20–60 barras).
   - **¿Es imbalance o es simplemente nodo de volumen?** Un nulo anclado
     también en volumen comparable —no sólo en tiempo— aislaría lo que
     BigTrap2 aporta de lo que aporta cualquier zona de alto volumen (fenómeno
     de microestructura ya documentado y distinto).
2. **¿La distribución de retornos cambia dado el estado de zonas?** El test de
   información condicional (F4). Máxima potencia, una sola hipótesis. Requiere
   STOP.
3. **¿Hay algo observable al momento del toque que separe rompe de aguanta?** F1.2
   lo ataca por el lado del ciclo de vida; nunca se atacó por el lado del flujo
   (OFI normalizado por profundidad, Cont-Kukanov-Stoikov).
4. **¿Cuánto de la fricción de 2,768 ticks es evitable?** El número se tomó como
   dado. Nunca se descompuso en spread, comisión y slippage, ni se evaluó entrada
   pasiva.
5. **¿El indicador funciona distinto según el régimen?** **Parcial** — F0.3
   midió estacionalidad intradía (pico de densidad 11-13h CT, coherente con
   solape Londres-NY) pero nada de eso se cruzó todavía con ruptura ni con
   toque. Sin condicionamiento por volatilidad, tendencia ni día de la semana.
6. **¿Los otros 4 indicadores?** F9 está PAUSADA por decisión sellada, y los
   4 existentes distintos de BigTrap2 no se investigaron como generadores de
   hipótesis.

---

## 4. LO QUE SE MIDIÓ MAL Y SE CORRIGIÓ — para que quede el rastro

| qué | corrección |
|---|---|
| MDE «no reproducible» | usaba `SD/√n` en vez del SE bootstrap medido; la derivación estaba en `docs/`, no en `diag/` |
| RSS «sin origen» | `1.925` era separador de miles: 1925 MiB. Retractado |
| Manifiestos se angostaban | `--emitir` reescribía entero; una máquina parcial borró ES/NQ. Fusiona y hay guardia |
| Artefacto declaró `outcomes_accessed` sin leer precios | bandera derivada de la fase pedida y no del hecho. En cuarentena, no borrado |
| `CONTROL_EVENTOS = 755` | 755 es pre-descongestión; orden B es 424 |
| **Hipótesis del denominador** (F0.2) | escribí que la mayoría de las zonas no se tocaba. **Es al revés: 97,9 % se toca.** Corregido con el original a la vista |
| **«El primer toque selecciona rupturas»** (acta de muerte §4) | F1.2 midió que **todas** las zonas rompen eventualmente (96,3 %) — la población de H1 (92,9 % rota) está **por debajo** de la tasa base, no por encima. Corregido en `F1_SUPERVIVENCIA_DEPLECION_RESULTADO_2026-08-10.md` §2 |
| **Hipótesis mecánica «la altura domina el hazard»** (`PLAN_ANALISIS_v2` §F1.2) | pre-declarada, **refutada por F2**: 4× altura, misma tasa de ruptura (95,8–96,9 %) |

---

## 5. Mantenimiento

Este documento se actualiza **en el mismo commit** que cualquier medición nueva.
Una dimensión que se mide pasa de §2 a §1; una que se descarta pasa a §2 **con
justificación escrita**, no por silencio.

---

## Aporte al referente

Hace explícito el tamaño real del espacio no explorado —empezando por
`bar_spec`, que nunca se varió y que para un indicador de footprint pesa más que
cualquier parámetro— y convierte «no lo medimos» en un ítem con fecha y renglón
en vez de un supuesto invisible. Es la contramedida directa al modo de falla que
costó todo el corpus de H1: mediciones correctas sobre la pregunta equivocada,
con la trazabilidad en orden.
