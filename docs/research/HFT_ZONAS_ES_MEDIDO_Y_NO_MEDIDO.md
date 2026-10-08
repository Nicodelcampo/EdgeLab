# Zonas HFT sobre ES — qué está medido y qué NO

> Pedido de Nico, 2026-08-20: *«hay que dejar bien claro y registrado lo que NO probamos,
> para no confundirnos y darlo por probado».*
>
> Este archivo se actualiza **en el mismo commit** que cualquier medición nueva sobre esta
> familia. Un resultado que no aparece acá no está medido, por más que alguien lo recuerde.

**Población de referencia**: oráculo `HFTZonesESPureV2Flat`, ES 03-26, 62 sesiones
pre-firewall (2025-12-22 → 2026-03-19), 9.486 zonas, 51,8 % bajistas / 48,2 % alcistas.
Snapshot congelado `runs/oraculo_espurev2flat_ES_snapshot.sqlite`, sha256 `a7dec2ee382c32ea`.

---

## MEDIDO — y muerto

| qué | resultado | alcance exacto |
|---|---|---|
| **Soporte / resistencia** | ~96 % de ruptura, invariante a los 12 parámetros | 6E, no ES |
| **Imán de zona / revisita** | cerrado en F2.7–F2.10 | 6E, 201 sesiones, 15.947 zonas |
| **Retorno a la zona** | pasa el 99,7 % de las veces; **control inválido** | ES Flat — ver retractación |
| **Tasa de volumen dentro → excursión** | ρ ≈ 0 dentro de sesión, terciles sin ordenar | ES V2 (población sesgada) |
| **Costo de cruce borde a borde** | **EQUIVALENCIA DECLARADA** por R3: +0,583 `ticks/ancho`, IC95 [0,000 · 6,250], IC90 dentro de ±7,91 | ES Flat, 7.058 pares, 62 sesiones. **Alcance: sólo el soporte común** — no cubre zonas anchas ni Asia/Europa (R2) |

### Retractación vigente (2026-08-20)
El control **«espejo»** de *retorno a la zona* y de *tasa de volumen* está **degenerado**.
Se construía a la misma distancia del precio de creación, del otro lado — pero la zona
*es* el rango del barrido que la crea, y el barrido termina adentro. Esa distancia tiene
mediana **1 tick** y el **39 %** de las zonas la tiene en **cero**: el espejo cae encima de
la zona. 630 de 1.601 pares daban valores idénticos.

**El «contraste ≈ 0» de esas dos mediciones no es evidencia de ausencia de efecto.**
Está garantizado por construcción. Ambas quedan **retractadas, no muertas**: hay que
re-medirlas con el control casi-zona.

Lo que **no** se retracta: el ρ ≈ 0 de la tasa de volumen se sostiene sobre la zona misma;
y el hallazgo de que una ventana de outcome de largo variable fabrica correlación con
cualquier variable de tendencia intradiaria no dependía del control.

### Retractación adicional — memoria de nivel (commit 59a9f28)
El «p<0,05 en el 71 % de las sesiones» del censo de contextos (`be21d35`) fue causado por
un bug de redondeo asimétrico: `np.round(mid)` colapsaba medios ticks sobre enteros en el
observado pero no en el nulo. Con el nulo corregido (`memoria_nivel_nulo_correcto`), la
fracción baja a **31 %** (18/59 sesiones). **El 71 % se retracta.**
Ver `docs/research/memoria_nivel_nulo_correcto.json`.

### Segunda retractación, del estimador — `RETRACTED_INVALID_ESTIMATOR_COUNT_OVER_B`
Entre `59a9f28` y el sellado de R1 circuló **p mediana 0,1775**. Ese número salía del
nulo corregido pero con el estimador `p = count/B`, que publica **p = 0,0 en 5 de 59
sesiones** — imposible con B remuestreos, donde el mínimo es `1/(B+1) = 0,00249`. Con
`(1 + count)/(B + 1)` (North et al. 2002) el valor sellado es **0,1796**. El 0,1775 se
conserva acá porque llegó a citarse en docs; **no se usa**.

---

## MEDIDO — e inconcluso

| qué | resultado | alcance exacto |
|---|---|---|
| **Memoria de nivel** `MEASURED_COMMITTED` | **p mediana 0,1796**, p<0,05 en **31 %** de las sesiones (18/59), contra el 5 % esperado. Enriquecimiento 6×, pero **sin estadístico global ni distribución nula conjunta**. **Pendiente: ni efecto ni nulo.** | ES Flat. Universo 62 → procesadas 62 → **elegibles 59** (3 excluidas: 20260216, 20260317, 20260319, todas con <10 zonas de ancho > 0). B=400, seed 20260820, `run_id 0e16a11b81dcb865`, código `056618f`, rerun limpio desde worktree detached |

**Denominadores, separados (ATJ-15).** El estadístico de números redondos usa las **62**
sesiones procesadas; el de memoria usa las **59** elegibles. No son el mismo denominador y
el artefacto ya no los colapsa en un único `n_sesiones`.

**Números redondos en ES** `MEASURED_COMMITTED`: por resto módulo 4, 0,2579 / 0,2465 /
0,2484 / 0,2473. El punto entero se lleva 25,79 % contra 25,00 % de la uniforme — exceso de
**0,79 pp**. El clustering masivo que la literatura documenta para otros índices **no está en
ES**, así que no es confundidor de la memoria de nivel. Verificado sobre el dato, no citado.

---

## R2 — el emparejamiento no es neutral `MEASURED_COMMITTED`

`docs/research/r2_matchability_es.json` · 9.235 zonas, 334.924 casi-zonas, 62 sesiones,
`run_id` en el artefacto. **Target-free: no mira outcomes.**

**El 18,3 % que no consigue control no es una muestra al azar.** Es sistemáticamente
distinto, y en la dimensión que más importa:

| covariable | matched | unmatched | SMD | KS |
|---|---|---|---|---|
| **ancho (ticks)** | 3,28 | **7,76** | **−1,067** | 0,546 |
| pasos | 181,5 | 298,0 | −0,841 | 0,392 |
| valid_steps | 176,4 | 289,1 | −0,837 | 0,388 |
| volumen total | 342,1 | 514,7 | −0,553 | 0,301 |
| ticks previos 5 min | 18.965 | 12.913 | +0,507 | 0,274 |

**13 de 17 covariables quedan fuera de |SMD| < 0,10.** El emparejamiento por ancho exacto
descarta preferentemente las zonas **anchas, largas y de mucho volumen**, porque una zona
ancha tiene pocas casi-zonas de su mismo ancho (1.020 candidatos de mediana contra 34).

**Y eso se proyecta sobre la fase**, porque en Asia/Europa las zonas son anchas:

| fase | cobertura | peso en matched | peso en unmatched |
|---|---|---|---|
| **asia** | **0,448** | 0,018 | **0,100** |
| **europa** | **0,531** | 0,026 | **0,102** |
| premarket | 0,719 | 0,037 | 0,065 |
| cierre | 0,736 | 0,045 | 0,073 |
| rth_pm | 0,849 | 0,496 | 0,394 |
| rth_am | 0,863 | 0,377 | 0,267 |

Asia pierde **más de la mitad** de sus zonas y pesa 5,5× más entre las descartadas.

### Tres propiedades del emparejamiento, medidas en vez de asumidas

| propiedad | resultado |
|---|---|
| **inestabilidad del greedy** | invirtiendo el orden cambia el **38,1 %** de las asignaciones; con permutación aleatoria, el **27,1 %** |
| **controles del futuro** | el **60,9 %** de los controles es POSTERIOR a su zona (el criterio usa \|Δt\|) |
| **sin reemplazo** | cuesta 525 pares (8.068 → 7.543); reutilización máxima 11 |

Separación temporal: p50 16,6 s · p95 **17,2 min** · máximo 30 min (el tope).
Sin candidato de su ancho: 215 zonas (2,3 %).

### Consecuencia, y no es menor

**El nulo agregado de H-ES-CRUCE-1 no representa a las zonas anchas ni a Asia/Europa.**
No demuestra que ahí haya efecto — obliga a **redefinir el soporte o limitar el estimando**.

Y golpea de lleno al borrador `H-ES-CTX-1`: su contexto primario `C1: RTH vs FUERA` se
justificaba porque fuera de RTH las zonas son más anchas. **Es exactamente la celda donde
el emparejamiento falla más, y falla por ancho.** Medir esa celda con este control sería
medir su cola angosta. `H-ES-CTX-1` sigue en `DRAFT_NOT_FROZEN`; esto agrega una razón
independiente a las cinco de la auditoría.

---

## R3 — el costo de cruce queda cerrado por equivalencia `MEASURED_COMMITTED`

`docs/research/r3_inferencia_cruce_es.json` · protocolo congelado **antes** de correr
(`R3_INFERENCIA_CLUSTERIZADA_PROTOCOLO.md`). Bootstrap de **sesiones completas**,
B = 10.000, seed 20260821, 7.058 pares en 62 sesiones.

| | valor |
|---|---|
| punto (`ticks_por_ancho`) | **+0,583** |
| IC 95 % | [+0,000 · +6,250] — **cruza cero** |
| sesión-ponderada | +1,650 — **mismo signo** |
| margen declarado | ±7,91 (5 % de la mediana del control) |
| IC 90 % | [+0,000 · +5,500] |
| **TOST** | ✅ **equivalencia** — el IC entra entero |

Es la primera vez en esta familia que un nulo se afirma **con margen** en vez de por
ausencia de significancia. Secundarias, todas cruzando cero: `ticks` +1,00 [0 · 14],
`ms` +0,00 [0 · 106], `volumen` +4,50 [0 · 22], `vol_por_ancho` +2,00 [0 · 11].

### Las cuatro sensibilidades, y la que hay que mirar

| variante | punto | IC 95 % | n |
|---|---|---|---|
| S1 orden inverso | +0,000 | [+0,000 · +4,550] | 7.083 |
| S1 permutado | +0,000 | [+0,000 · +5,167] | 7.063 |
| **S2 sólo controles anteriores** | +0,000 | **[−4,000 · +0,000]** | **2.778** |
| S3 con reemplazo | +0,000 | [+0,000 · +3,535] | 7.524 |
| S4 separación ≤ 5 min | +0,000 | [+0,000 · +3,500] | 6.043 |

**S2 es la que merece atención.** Restringir a controles **causales** —anteriores a su
zona— deja sólo 2.778 pares, porque el 60,9 % de los controles venía del futuro, y el
intervalo se **da vuelta**: pasa de [0 · +6,25] a [−4,00 · 0]. Los dos contienen cero y
los dos puntos son 0, así que el signo no cambia formalmente — pero la asimetría es
real y queda registrada. **Si alguna vez se quiere una versión live-compatible de esta
medición, S2 es la única admisible**, y sobre ella la evidencia es más débil.

### Tres límites que viajan con el resultado

1. **El soporte.** Sólo zonas con control: 81,7 %, ancho mediano 3,28 contra 7,76 de las
   excluidas. **No dice nada sobre zonas anchas ni sobre Asia/Europa.**
2. **El margen no es económico.** `ticks_por_ancho` cuenta operaciones por unidad de
   ancho, no dinero. Es relevancia práctica, no rentabilidad. Un margen económico exige
   reglas de entrada/salida, sizing, fricción estimada **para ES** y fills — nada existe.
3. **Procedencia.** El artefacto declara `arbol_limpio: false` con 20 archivos sucios:
   son **`.md` ajenos con diferencias sólo de fin de línea** (CRLF↔LF), verificado con
   `--ignore-cr-at-eol`. **Ningún `.py` entre ellos.** Se publica el hecho en vez de
   maquillarlo.

---

## Atlas F1 — construido `MEASURED_COMMITTED`

`docs/research/atlas_hft_es.json` · parquet `data/atlas/atlas_hft_es_full.parquet`,
22,3 MB, sha256 `fc5451704dee58e3…` (gitignorado: es dato, el hash lo hace trazable).

**370.631 filas, tres poblaciones con las mismas 39 columnas**, todas `PRE` o
`AT_EVENT`. Ninguna `POST`: no hay excursión, retorno, cruce, MAE/MFE ni P&L.

| grupo | n | ancho mediano | RV previa | dist. VWAP |
|---|---|---|---|---|
| ZONA | 9.231 | 3 | 36,1 | 68,1 |
| CASI | 334.915 | 1 | 32,4 | 62,8 |
| **S1_1MIN** | 26.485 | **9** | **20,7** | 47,9 |

**Observación que hay que registrar antes de usar S1 como control**: `S1_1MIN` es
estructuralmente distinto — **9 ticks de ancho mediano contra 3 de la zona**, y RV
previa **casi la mitad**. O sea que aparece en condiciones más calmas y con geometría
más grande. Usarlo como control sin emparejar repetiría el error que R2 acaba de medir
en el control casi-zona. **El emparejamiento de S1 es trabajo pendiente, no resuelto.**

Percentiles **expansivos** (bucket de 15 min, sólo historia previa, sin incluirse a sí
mismos): disponibles en el 99,7 % / 99,6 % / 98,2 % de las filas.

Declarado como no implementado, en vez de inventado: `scheduled_news`
**NOT_AVAILABLE** (falta calendario oficial), spread/depth/OFI y queue imbalance
**DEFERRED** (requieren BBO/L2), columnas BigTrap **BLOCKED** (no hay paridad sobre ES).

---

## H-ES-CTX-2 — el contexto no rescata la familia, y dos celdas quedan sin potencia

`docs/research/h_es_ctx2_condicionado.json` · `run_id fe483af4ad20e31a` ·
pre-registro congelado **antes** de correr. 7.057 pares, 62 sesiones, B = 10.000.

| celda | n | ses | punto | IC 95 % | **MDE** | p (Holm) | equivalencia |
|---|---|---|---|---|---|---|---|
| `pct_rv` bajo | 883 | 57 | +3,500 | [0,000 · +20,250] | **14,47** | 1,00 | ❌ sin potencia |
| `pct_rv` medio | 1.807 | 56 | +0,000 | [−2,667 · +0,667] | 2,38 | 1,00 | ✅ |
| `pct_rv` alto | 3.561 | 58 | +4,500 | [0,000 · +13,400] | **9,58** | 1,00 | ❌ sin potencia |
| primera 5 s | 4.767 | 62 | +2,500 | [0,000 · +9,750] | 6,97 | — | ❌ sin potencia |
| no primera | 2.290 | 59 | +0,000 | [0,000 · +5,000] | 3,57 | — | ✅ |
| TODAS | 7.057 | 62 | +0,667 | [0,000 · +6,250] | 4,47 | — | ✅ |

**Ningún contexto muestra efecto**: `p` de Holm = 1,00 en los tres terciles.

### Lo que el MDE evitó

Sin el MDE publicado antes, `bajo +3,500` y `alto +4,500` se leerían como *«hay algo
en los extremos»* y arrancaría una cacería. El MDE dice lo contrario: en esas celdas
**no se puede ver nada menor a 14,5 y 9,6**, contra un margen de 7,91. Los puntos no
son un hallazgo — son ruido dentro de un intervalo demasiado ancho.

La causa no es sólo el n: `alto` tiene 3.561 pares y aun así MDE 9,58. **Es
dispersión**: cuando el mercado está agitado, el costo de cruzar varía mucho más.

### La condición de cierre NO se cumplió

El pre-registro decía: *«los tres terciles dan equivalencia dentro de ±7,91 → el
contexto no separa nada y la familia queda cerrada»*. **Sólo uno de tres la alcanzó.**

Entonces, en estricto rigor: **la familia no cierra formalmente.** Tampoco muestra
nada. El estado correcto es **«sin efecto detectado, con dos celdas sin potencia
suficiente para afirmar equivalencia»**.

Cerrarla del todo exigiría **más sesiones** — es decir, otra exportación de oráculo
desde NT8. Es la restricción que P-53 ya había nombrado: **el límite es N, no el
modelo.**

---

## MEDIDO — y vivo
- **HFT-REV-EXP cortes (MNQ 09-25, 2026-09-26, exploratorio).** Exceso difuso de +1 a +3 pp en casi todos los cortes;
  ningún contexto concentra el efecto. **Replicado en 12-25 y 03-26:** los 9 cortes sostienen, pero son el exceso difuso de +1–3 pp, sin concentración.
  Ver `docs/research/HANDOFF_2026-09-26_HFT_REV_Y_ESPEJO.md`.
- **ESPEJO-SIM (MNQ 09-25, familia TBZX, exploratorio).** Con `minW` = 17, las vueltas parecidas al impulso completan el
  espejo +1,5 a +4,9 pp más que las poco parecidas (FDR de grilla). **Replicado en MNQ 12-25 y 03-26 (43/52; commit
  `079d2bd`, corrección 28/09: esta línea decía «sin replicar»).** El contraste parecidas − poco parecidas no depende del
  nulo; el «exceso sobre f» (+1–3 pp) sí, y f está sesgado +1 a +5 pp (Entrada 057): ese exceso no se sostiene. No operable en esa escala
  (costo/W ≈ 14 pp). Nulo al extremo de la vela sesgado: se usa el del cierre (enmienda 1).

- **HFT-REV-EXP (MNQ 09-25, otra familia, no ES — registrado acá por visibilidad, 2026-09-26).** Primer retorno a zonas
  `HFTZonesNQPureV4` `SCALED_FUNNEL_V1`: 29.635 zonas, 36 sesiones. Revierte 40 t el 26 % de las que vuelven, contra 25 %
  de la caminata aleatoria. Exceso sobre el control de nivel de +1 a +2,5 pp (IC excluye 0 en D ≥ 20; MDE ≈ 1,5 pp).
  Penetración mediana 6 t (≈ 50 % de W). Exploratorio, sin P&L. `docs/research/HFT_REVERSION_EXPLORATORIA_MNQ_20260926.md`.

| qué | resultado |
|---|---|
| **Paridad NT8 → Python** | 9.481/9.486 zonas EXACT (**99,95 %**); el residual son claves `start_ts` en ms degeneradas dentro de ráfagas de hasta 182 ticks en el mismo milisegundo |
| **El bug `isDown`-first** | confirmado y corregido: 8,1 % → 48,2 % de zonas alcistas |
| **El algoritmo corre sobre 1 tick** | `AddDataSeries(Tick, 1)`; el gráfico de 25 Tick es sólo dibujo |

---

## NO MEDIDO — y por qué importa decirlo

### Cosas que suenan medidas pero no lo están

1. **El estimando del costo de cruce sobre soporte completo.** R2 midió que el control sólo
   existe para el 81,7 %, sesgado a zonas angostas. Falta decidir entre: (a) restringir el
   estimando al soporte común y declararlo, (b) emparejar por ancho con tolerancia, o
   (c) usar un control distinto para zonas anchas. **No medido.**
2. **Retorno y costo de cruce CONDICIONADOS a contexto.** Todo lo medido es agregado sobre
   la población entera. La dispersión pareada del costo de cruce es enorme (p25 −704 /
   p75 +881 ticks) con mediana cero: la firma que P-55 describe como *dos efectos opuestos
   cancelándose*. **Un nulo agregado no es un nulo condicional.** El costo de cruce agregado
   es nulo sobre 7.542 pares, pero sin CI ni test formal de equivalencia. Pendiente:
   CI cluster-bootstrap con sesión como unidad y margen de equivalencia declarado.
3. **Cualquier cosa direccional sobre la población V2 original.** El 92 % bajista era el
   orden de dos `if`. Todo estadístico direccional calculado antes del parche mide eso.
4. **Los otros instrumentos.** Todo esto es ES 03-26. **Nada** se transporta a 6E, NQ o YM
   — ni el resultado, ni los costos, ni el presupuesto de multiplicidad.
5. **El holdout.** 2026-07-01 → 2026-12-31 intacto. Ninguna medición de esta familia lo tocó.

### Cosas que nadie intentó todavía

6. **Combinación con otros indicadores.** Hay catálogo (`aVolClusterPOI` con paridad
   medida, BigTrap2, TRAPs) pero **nunca se midió co-ocurrencia** con las zonas HFT.
   Distinción que hay que sostener: **co-ocurrencia** (¿pisan el mismo terreno?) es
   target-free y se puede medir ya; **«se complementan para atraer al precio»** es un
   outcome y va después, con contexto declarado.
7. **Zonas de otros parámetros.** Todo corre con los `SetDefaults` del `.cs`. No hay
   barrido de `MinPasos`, `MinSweepTicks`, `MaxPausaMs` ni ninguno de los otros.
8. **El lado de la zona.** Se mide la banda entera. Nunca se separó qué pasa al tocar el
   borde superior contra el inferior, ni contra la dirección del barrido que la creó.
9. **Ejecutabilidad.** Cero. No hay reglas de entrada/salida, ni sizing, ni fricción
   estimada para ES, ni fills. La cadena `geometría → información → P&L bruto → edge neto`
   está frenada en el primer eslabón.
10. **`aVolCellPOI2`**: paridad en FAIL (P-42), aparcada. No usar hasta resolverla.
11. **Zonas vivas al cruzar el firewall**: 0 en este oráculo, verificado. Pero si se
    regenera el oráculo con otra ventana, hay que volver a verificar.

### Cosas que el censo descriptivo SÍ está midiendo ahora (target-free, sin outcomes)

Tasa normalizada por actividad · fase de sesión con DST real · solapamiento ·
agrupamiento (Fano) · posición en el rango del día · régimen de volatilidad previo ·
distancia a VWAP/SMA20/SMA50/EMA9/EMA21 · persistencia entre sesiones.

**Memoria de nivel**: ya tiene resultado (inconcluso, ver «MEDIDO — e inconcluso» arriba).
No es target-free puro: el estadístico de concentración depende de la especificación del
nulo. La versión corregida (commit 59a9f28) condiciona por ancho y precios operados reales,
pero no por fase de sesión ni posición temporal.

**Ninguno de esos mira qué pasó después.** Ese es el punto: describir dónde la población
varía, para que los contextos se declaren informados y no a ciegas. En el momento en que
una de esas dimensiones se cruce con «y después el precio…», ese corte tiene que estar
**declarado antes**.

---

## Números que circulan y NO corresponden a esta población

Cuidado con estos, que vienen del censo sobre el oráculo **V2 original con el bug**
(23.863 zonas, 8,1 % alcistas) y **no describen** la población corregida:

- «202 zonas/sesión mediana»
- «54,4 % concentrado en 3 bloques horarios»
- «solape 1,6 %»
- «duración mediana 108 ms», «altura mediana 3 ticks»

La población Flat tiene **9.486 zonas en 62 sesiones**. Cualquier comparación contra
aquellos números compara dos poblaciones distintas.

## Anexo 2026-09-24: costo de ejecución condicionado al libro (EXEC-QI; no es HFTZones, se registra acá por la regla del mismo commit)

- **MEDIDO:** ahorro de orden pasiva frente a agresiva, por tercil de QI, T ∈ {5, 30, 120} s, en NQ, ES, GC y 6E L2 de julio y agosto, sobre una grilla uniforme de 1 s. Ver `MANIFIESTO_EJECUCION_QI_L2_20260924.md` §10.
- **NO MEDIDO:**
  - el ahorro en instantes de señal de una estrategia;
  - fills reales (sim de NT8);
  - liquidez oculta y cola real;
  - la confirmación en `P-NQL2-CONF` y en el holdout L2.

## Anexo 2026-09-24 (2): MM-QI y validación del agresor

- **MEDIDO:** provisión pasiva de liquidez con filtro de QI en NQ, GC, ES y 6E: **muerta** (24 variantes negativas, 0 % de sesiones positivas). Ver `MANIFIESTO_MM_QI_L2_20260924.md` §7.
- **MEDIDO:** agresor de `research-v2` contra el L2, en el solapamiento de junio. **NQ: 99 %** de acuerdo. **ES: 78–81 %**: no pasa el umbral del 90 %, porque la cotización pegada es posterior a que el trade consumiera el nivel. Ver `artifacts/aggressor_validation.json`.
- **NO MEDIDO:**
  - una corrección del agresor de ES que llegue al 90 % (se probaron la cotización del trade anterior y la anterior a la ráfaga; ninguna mejora);
  - market making con información adicional.

## Anexo 2026-09-25: TREND-MICRO

- **MEDIDO:** rupturas B1, B2 y B3 × filtros F0 y F3 (y F1/F2 en NQ) × 2R/4R, en ES y NQ, jul-2025 a mar-2026. **0 sugerencias.** Ver `MANIFIESTO_TREND_MICRO_20260924.md` §8.
- **MEDIDO:** la continuación de una expansión (B3) llega al target menos que un camino aleatorio (ES −3,4 pts, NQ −6,2 pts).
- **NO MEDIDO:** F1/F2 con muestra suficiente; ES con agresor válido; la pista NQ B2 F3 pre-registrada sola.

## Anexo 2026-09-25 (2): AGOT-EXT

- **MEDIDO:** divergencia de RSI (y de delta en NQ) en extremos de pivote, ES y NQ, 24 celdas: **0 sugerencias**. En la ruptura la divergencia **empeora** ir contra el extremo; en la confirmación no agrega nada. Ver `MANIFIESTO_AGOTAMIENTO_EN_EXTREMO_20260925.md` §10.
- **MEDIDO (lateral):** ir contra un extremo nuevo confirmado acierta menos que el azar en ES y NQ (persistencia a la escala del pivote).
- **NO MEDIDO:** la divergencia como salida o como filtro de otra familia; la pista "comprar el retroceso tras un máximo confirmado" pre-registrada sola.

## Anexo 2026-09-25 (3): TBZ-E2 en ES

- **MEDIDO:** la franja de expansión como área de patinaje (E0–E3 × 4 detecciones × target A/HVN; hacia B como secundaria) en ES, 181 sesiones: **0 sugerencias**. El acierto hacia A queda levemente **por debajo** de la geometría sola, y las franjas TBZ se revierten menos que un tramo común. Ver `TBZ_E2_PARAMETRIZACION_HOLISTICA_20260924.md` §8.
- **NO MEDIDO:** detectores por velocidad y volumen relativo como detección primaria; descriptores G2–G5 como filtros pre-registrados; L2 (G7); MES (en curso).

## Anexo 2026-09-25 (4): TBZX (impulsos por velas y distancia, afuera y reingreso) en ES

- **MEDIDO (exploración, 181 sesiones, 12 configuraciones, dos nulos):** el tiempo y el volumen afuera de la franja no se distinguen del nulo con la misma actividad previa (N-VOL). La excursión afuera, la penetración al reingresar, su velocidad y la llegada al borde opuesto A sí: en la configuración de Nico, 0,152 contra 0,094 llegan a A. Contra el fantasma a la misma hora el efecto era el doble: la mitad era volatilidad posterior al impulso. Más fuerte con estiramiento extremo respecto de las medias, poco volumen por tick y fuera de RTH (descriptivo). `docs/research/MANIFIESTO_TBZX_ESPEJO_20260925.md` §7.
- **NO MEDIDO:** nulo con el mismo estado de reversión; cortes emparejados por estiramiento; NQ; reserva abr–jun; ejecución.
- **MEDIDO (iteración 2, 25/09):** con los nulos N-REV (tramo del mismo tamaño que recién dio la vuelta) y N-VOLSTR (actividad y estiramiento) y la réplica en NQ. La llegada a A es robusta a la actividad en ES y NQ, y al estado de reversión sólo en ES (NQ: −0,007). El contexto de estiramiento no es propio de la franja (desaparece con el nulo emparejado). §9 del manifiesto.
- **NO MEDIDO:** selección de contrato canónica (`contract_regime`; difiere en 3 sesiones de ES y 2 de NQ); reserva abr–jun; ejecución.
- **MEDIDO (25/09, N-REVVOL, primario):** contra un tramo del mismo tamaño que recién dio la vuelta **y** con la misma actividad, la franja TBZX llega a A **menos** (−3,5 pts, sesiones positivas 26 %). El «espejo» era actividad más reversión. **Hipótesis muerta** en ES, exploración, con este detector.

## Anexo 2026-09-26: EVX (cruces EMA × VWAP) en MYM, YM, ES y NQ
- **MEDIDO:** E0 y E1. 0 de 448 celdas con información direccional frente al control de mismo estado (MDE ~0,5 ATR). El embudo se detiene en E1. `docs/research/MANIFIESTO_EVX_E0_E1_20260926.md` §6.
- **NO MEDIDO:** estado continuo «EMA de un lado» (en lugar del cruce); otras resoluciones (1 min); efectos menores que el MDE.
- **MEDIDO (26/09, VREV E1):** reversión al VWAP entrando en el **primer** alejamiento ≥ X ATR de vela de 25 ticks (X 2–6), con 4 confirmaciones y 2 stops, en MYM/YM/ES/NQ: llega al VWAP **menos** que el control de mismo estado (96/128 INFO−). **Alcance:** sólo esa variante. **NO MEDIDO:** reversión con alejamiento en escala diaria o por bandas σ, VWAP anclado, entrada tras agotamiento, confirmaciones de flujo/L2, velas de tiempo, filtros de régimen. Ver `MANIFIESTO_VREV_E1_20260926.md` §5–§6.
- **MEDIDO (26/09, VREV-A y VCONT E1):**
  - **Reversión al VWAP tras 4 disparos de agotamiento:** 0/96 INFO+.
  - **Continuación tras el primer alejamiento:** 8/96 INFO+, todas en el Dow (MYM/YM) con X = 6, pero con neto de costo negativo.
  - **Alcance por celda.**
- **NO MEDIDO:** agotamiento por flujo/L2, escala diaria, geometrías de más recorrido. `MANIFIESTO_VREVA_VCONT_E1_20260926.md` §6.
- **MEDIDO (26/09, AXF etapa A, NQ):** agotamiento por delta → barrido → reversión confirmada (256 detecciones × 3 filtros de tendencia × 2 horizontes). Rinde **menos** que el control de misma inercia (240 INFO− de 246 con evidencia; las 6 INFO+ son 50 eventos de una sola mitad). **NO MEDIDO:** absorción con eventos suficientes, L2, otras ventanas, ES y otros activos, salidas (etapa B no corrida por protocolo). `MANIFIESTO_AXF_NQ_20260926.md` §6.

## Anexo 2026-09-26 (2): IPC macro (acumulaciones de picos como imán) en ES 500t
- **MEDIDO:** etapa A, 28 celdas (alejamiento con momento temprano/tardío, regreso a zona virgen; k 2 y 4; dos detectores), contra C-SZ y C-SW. Reporte sha `59f9d855deff`, manifiesto `MANIFIESTO_IPC_MACRO_ES_500T_20260926.md`.
- **Estado:** 28/28 **SIN_POTENCIA** (519 eventos en 181 sesiones). Lo visible en las 5 celdas medibles: +0,09 contra nivel sin zona que se anula contra pico reciente; el regreso va en contra (−0,16 contra C-SW en la estricta). No hay candidato para B.
- **NO MEDIDO:** RTH vs ETH, otras escalas (2000t, tiempo), zonas entre sesiones, otros activos, primer pico.

## Anexo 2026-09-26 (3): IPC 25t (acumulaciones de picos como imán) en ES y NQ
- **MEDIDO:** etapa A, 144 celdas, contra C-SZ (nivel sin zona) y C-SW (pico reciente no superado, sin acumulación). Reporte sha `ff25451223b2`. Corrida anterior con fuga (`daa3b0f3bbd3`) invalidada.
- **Estado:** 32 INFO+, 23 pasan a B. El efecto sobrevive al pico reciente: ES k 4 último pico +0,155 [+0,12, +0,19] con n 1.335.
- **NO MEDIDO:** economía (B), estado continuo, banda completa, otros activos, holdout.

## Anexo 2026-09-28: IPC 25t, prueba de robustez (auditoría 046)
- **MEDIDO:** las 23 celdas de la etapa A + 5 D4 con zonas as-of, midquote, C-SW emparejado, volumen causal (reporte `f8e68b1a404b`). **0/23 sostienen: NO_ROBUSTO.** La corrección de controles con zonas futuras baja el efecto principal de +0,20 a +0,06; sobre midquote contra el pico reciente emparejado queda en −0,04.
- **NO MEDIDO (sigue abierto):** el resto del abanico IPC (otros eventos, objetivo sin barrera, penetración, estado continuo, escalas, IPC como componente o imán en espejos). Pista débil: ES k 8 último pico (+0,08 en midquote, no significativa).

### Anexo 28/09 — nulo del espejo y contextos L2 NQ
- **MEDIDO (sintético, target-free):** P(completar)=f **no** es el nulo correcto con velas 100t, toque por mecha y horizonte
  censurado: sesgo sobre resueltas de +1 a +25 pp (`tools/espejo_nulo_sintetico.py`). Nulo retirado del pre-registro
  ESPEJO-NICO-100T; su reemplazo es decisión de Nico. Entrada 057.
- **Corregido (integridad, no resultado):** extractor L2 NQ con 0 minutos elegibles por cruce transitorio intra-lote.
  20260626: 1021/1381 minutos elegibles tras el fix. **NO MEDIDO todavía:** los climas L2 NQ (extracción en curso).
- **Decisiones de Nico 28/09:** (1) nulo del espejo = simulado (enmienda N1, `edgelab/research/espejo_nulo.py`, 5 tests
  con probabilidades conocidas); **NO MEDIDO** sobre datos reales, el pre-registro sigue en STOP. (2) NT8 canónico
  prospectivo (`DECISION_PROVEEDOR_CANONICO_NT8_20260928.md`); lo medido con Lucid queda etiquetado Lucid.
  (3) libro L2: un cruce (preapertura CME) ya no vacía el libro; 20260626 pasa de 1021 a 1371/1381 minutos elegibles.
- **MEDIDO 28/09 — ESPEJO-NICO-100T descubrimiento (ES, 181 sesiones, 1.942 eventos, nulo N1, midquote):** 0/8 pruebas
  sobreviven; P2 negativa en 3/4 celdas; MDE 0,07–0,16. Sin replicación. `RESULTADO_ESPEJO_NICO_100T_DESCUBRIMIENTO_20260928.md`.
- **PROVISIONAL 28/09 — ESPEJO-VOLLIMP-100T (ES, 3.863 eventos, 24 pruebas):** 0/24 sobreviven BH; la de p menor (R-VL x=0,75
  otros, −0,12, p 0,038) va en contra. **Ambas corridas del espejo usaron un pool del nulo que incluía la vela del evento
  (auditoría 059)**: son descriptivas hasta re-correr con el pool corregido (decisión de Nico).
- **Re-corrida 28/09 con pool del nulo corregido (OK de Nico):** ESPEJO-NICO 0/8 (árbol limpio, cambios ≤ 0,002);
  VOLLIMP 0/24 (menor p: R-VL x=0,75 otros −0,12, p 0,042, en contra; árbol marcado dirty sólo por `tools/ipc_nivel.py`
  sin trackear, no importado). Las dos dejan de ser provisionales: **sin efecto detectado**, con el alcance de sus actas.
- **IPC-NIVEL v2 (target-free, 28/09):** ≥ 3 visitas separadas por salidas ≥ 14 t; **picos monótonos** (un piso no hace
  mínimos más bajos que el anterior, un techo no hace máximos más altos; los 10 grupos de Nico lo cumplen sin excepción);
  paso ≤ 2 t contra el pico anterior (3 t desde la 3.ª visita); zigzag fino R = 6 t; ≤ 200 velas entre picos; misma sesión.
  Cubre 9/10, precisión 18 % → tanda ✓/✗ en MES feb-2026. **NO MEDIDO:** ningún desenlace.
- **IPC-NIVEL v2 validada por juicio (28/09):** Nico juzgó 121 detecciones de MES feb-2026 (fuera de la muestra de
  ajuste): 99 ✓ / 22 ✗ = **82 % de acuerdo**. Los ✗ tienen menos picos (mediana 3 vs 4) y duran menos (110 vs 165 velas);
  salida y deriva no distinguen. Variante estricta **IPC-N4** (≥ 4 picos): 90 % (70 ✓ / 8 ✗), pierde 29 ✓.
  Definición congelada: v2 como principal, N4 como variante. **NO MEDIDO:** ningún desenlace.
- **MEDIDO 28/09 — IPC-NIVEL-MES descubrimiento (MES 25t, 171 sesiones, 3.381 zonas, árbol limpio):** 1/8 sobrevive y
  va **contra el imán**: el techo v2 se barre 6,2 pp menos que un pivote suelto emparejado (IC 90 % [−8,8; −3,5]).
  Pivotes sueltos se barren ~5 pp más que el azar; las zonas no. Candidato a confirmación abr–jun (Lucid) en ese sentido.
  `RESULTADO_IPC_NIVEL_MES_DESCUBRIMIENTO_20260928.md`.
- **MEDIDO 28/09 — IPC-NIVEL-REGRESO (MES, 2.214 regresos vírgenes):** 1/36 sobrevive (piso, cerca + poco volumen: −6,8 pp
  vs pivote suelto); techo igual −7,2 (p 0,008, no pasa BH). Lejos + mucho volumen: sin diferencia. No hay imán.
  `RESULTADO_IPC_NIVEL_REGRESO_MES_20260928.md`.
- **MEDIDO 28/09 — IPC-NIVEL × densidad HFT (MES):** 0/16; la cercanía/densidad de zonas HFTZonesNQPureV4 (sin paridad
  validada) no discrimina barrido vs resistencia del nivel. `RESULTADO_IPC_NIVEL_HFT_MES_20260928.md`.
  Con desgaste por comercio del visor (umbral 100; sensibilidad 35 y 500): también 0/16 en las tres.
  **Estado: exploratorio, diseño a revisar con Nico en el visor. No es una muerte del cruce IPC × HFT.**
- **MEDIDO 28/09 — PIVOTES-BARRIDO-MES (censo, 272.331 pivotes):** en la confirmación los pivotes se barren **como el azar**
  (techo −0,8 pp, piso +0,2). El +5 pp del control C-PIV del IPC-NIVEL era selección del evento de control. Sólo la
  distancia separa (+1,7 a +2,6 pp, sin relevancia económica). **Corrige LES-PIVOT-SWEPT-20260928.**
  `RESULTADO_PIVOTES_BARRIDO_MES_20260928.md`.
- **MEDIDO 28/09 — ESPEJO-CONT-100T ES (Kaggle, Lucid, nulo corregido):** 0/1.035 celdas; exceso ≈ 0 en todos los niveles.
  El R bruto negativo de la continuación es mecánica de entrada (toque por mecha), no reversión. Corrige la lectura de
  CONT-TPSL ES 25t. `RESULTADO_ESPEJO_CONT_100T_ES_20260928.md`.
- **MEDIDO 28/09 — ESPEJO-CONT-100T YM:** 7/1.050 sobreviven, todas TP/SL 0,25/0,25 W con VWAP/EMA a favor: exceso +1,2–1,7 % W,
  R bruto negativo (−0,025 W). Pista chica, no rentable. `RESULTADO_ESPEJO_CONT_100T_YM_20260928.md`.
- **MEDIDO 28/09 — ESPEJO-CONT-100T NQ:** 71/1.050 sobreviven, todas TP 0,25 W en casi cualquier filtro; R bruto negativo.
  Sospecha de residuo del nulo en TP chicos (también en YM): pendiente control empírico. `RESULTADO_ESPEJO_CONT_100T_NQ_20260928.md`.
- **MEDIDO 28/09 — ESPEJO-CONT-100T MES (NT8):** 4/1.020 sobreviven, todas negativas (nivel 5, VWAP en contra / ineficiente).
  Igual que ES: la continuación no supera al azar. `RESULTADO_ESPEJO_CONT_100T_MES_20260928.md`.
- **MEDIDO 28/09 — Contextos L2 NQ: PASS** (cobertura 100 %, semillas ≥ 0,958, sin concentración horaria; hora sola no
  predice el clima). Deriva en el roll a vigilar. Habilitados como filtro en jul–sep (desarrollo), confirmación oct+.
  `RESULTADO_CONTEXTOS_L2_NQ_20260928.md`.
- **MEDIDO 28/09 — ESPEJO-REV-100T ES:** el cruce hacia B llega MENOS que el azar (−1 a −4 pp), sobre todo con overshoot
  bajo; TP/SL de reversión R bruto negativo. Contrario a NQ parcial. `RESULTADO_ESPEJO_REV_100T_ES_20260928.md`.
- **MEDIDO 28/09 — ESPEJO-REV-100T GC (sin feb-2026):** cruce hacia B sin efecto; **TP/SL de reversión 2 W / 1 W: R bruto
  +0,026 W (≈ +3,6 t), exceso +0,106, sobrevive** (n 2.103). Primer R bruto positivo que sobrevive. Candidato a
  confirmación abr–jun con fricción GC propia. `RESULTADO_ESPEJO_REV_100T_GC_20260928.md`.
- **MEDIDO 28/09 — ESPEJO-CONT-100T MYM (NT8):** 41/1.050; TP 0,25 positivos en cualquier filtro (patrón sospechoso del nulo)
  y contra-tendencia negativa; R bruto negativo. `RESULTADO_ESPEJO_CONT_100T_MYM_20260928.md`.
- **MEDIDO 28/09 — ESPEJO-CONT-100T MNQ (NT8):** 1/1.050 (VWAP a favor, TP 0,25), R bruto negativo. **Continuación tras el
  espejo cerrada como edge en 6 instrumentos y 2 proveedores.** `RESULTADO_ESPEJO_CONT_100T_MNQ_20260928.md`.
- **MEDIDO 28/09 — ESPEJO-REV-100T YM:** 0 sobreviven; cruce y reversión en el azar. `RESULTADO_ESPEJO_REV_100T_YM_20260928.md`.
- **MEDIDO 28/09 — ESPEJO-REV-100T NQ, re-corrida con sesiones sorteadas (disjunta de la primera):** el primer 25 % del cruce
  hacia B vuelve a superar al azar (+2,2 a +2,9 pp; overshoot medio +3,7 a +4,6 pp); 75–100 % en el azar. Se repite en
  dos muestras sin sesiones en común. Opuesto a ES; nulo en GC y YM.
- **MEDIDO 28/09 — Control empírico GC reversión:** TP 2 W / SL 1 W, R espejo +0,023 vs R azar −0,055 → exceso empírico
  **+0,078 W [+0,042; +0,119]**. El candidato sobrevive; el nulo sobreestimaba (+0,101). Siguiente: fricción GC y confirmación.
- **MEDIDO 28/09 — Control empírico NQ continuación:** el nulo simulado está sesgado +1,2 % de W en TP 0,25 (también en velas
  al azar) y −2 % en TP amplios. Las celdas «sobrevivientes» de TP 0,25 en NQ/YM/MYM/MNQ son mayormente sesgo del nulo.
  El exceso se lee contra el control empírico.
- **MEDIDO 28/09 — Control empírico ES continuación:** exceso empírico ≈ 0 en todas las celdas (cierre confirmado); el nulo
  simulado sesgado hasta +0,108 W en TP 2/SL 1 en ES (−0,02 en NQ, +0,025 en GC): el sesgo depende del instrumento.
- **MEDIDO 29/09 — GC P1/P2:** control emparejado +0,080 W [+0,035; +0,123] pero **no sobrevive max-T de 30 celdas**
  (t 2,93 < 3,09); llenado tick a tick degrada −0,034 W por trade → R neto esperado ≈ −0,01 W. **No pasa a confirmación.**
  Bid/ask de Lucid en GC sospechoso (spread mediano 4 t). `RESULTADO_GC_P1_P2_20260929.md`.
- **MEDIDO 29/09 — NQ-CRUCE25-CLIMA (desarrollo A3, NT8 jul–sep, 35/40 sesiones de evaluación con velas):** cruce al 25 %
  con entrada al cierre de señal vs control del mismo clima: **0/12 celdas sobreviven max-T** (t crít 3,17). *calm* −1,7 pp
  (t ≈ −1,9), *toxic* +7 a +9 pp (MDE 0,125), global −1 a −2 pp: el +2–4,6 pp de Lucid no aparece con esta convención.
  **NO MEDIDO:** 10/09 y 15–18/09 (sin ticks NT8), deriva de roll (sólo 3 sesiones post-roll). `RESULTADO_NQ_CRUCE25_POR_CLIMA_L2_20260929.md`.
- **MEDIDO 29/09 — Contextos L2 ES (NT8 jul–sep, 16+32 sesiones):** **STOP** por inestabilidad de semillas (0,61 global;
  normal 0,21, volatile 0,05). Cobertura 100 %, no es sólo-hora. ES queda sin climas. Etiquetas de diagnóstico publicadas.
  `RESULTADO_CONTEXTOS_L2_ES_20260929.md`. **NO MEDIDO:** dos regímenes (calm/toxic) como hipótesis propia.


## Anexo 29/09 — IB→VWAP / PMH-PML en NQ (no HFTZones; registrado por visibilidad)

- **MEDIDO:** sandbox, NQ NT8 v1 Q3, 56 sesiones catalogadas, reglas congeladas sin L2. IB→VWAP: 5 trades, +0,7211 R después de 2 ticks, antes de comisión: **INCONCLUSA por muestra**. PMH/PML: 36 trades, −0,0687 R; media observada negativa, no significancia demostrada.
- **NO MEDIDO:** inferencia max-T conjunta (gate previo exige ≥30 trades en ambas y falla IB), fills/latencia/comisiones reales, confirmación, otras reglas y filtros. No decir “0/2 sobreviven”: no hubo test familiar calculado.
- Acta: `RESULTADO_IB_VWAP_PMH_PML_NQ_20260929.md`; código/preflight previo `01dd9a5…`, 41 ejecuciones auditadas independientemente contra raw ticks. Holdout intacto.
- **MEDIDO 29/09 — TOXIC-ES-1 (capa toxic de ES, target-free):** **FAIL por deriva** (13,3 % → 8,4 % entre mitades de
  evaluación, IC excluye 0; semana 37 al 4,5 %). Persistencia, hora, concentración y nivel vs entrenamiento: PASS.
  La capa no se usa. `RESULTADO_TOXIC_ES_1_20260929.md`. **NO MEDIDO:** si la caída es mercado o deriva del score.


## Anexo 29/09 — revisión ES/NQ L2 y nueva idea espejo × IPC (sin nuevos outcomes)

- **MEDIDO target-free:** auditoría de 1.509 intervalos ES; 48 sesiones, 65.134 minutos; evaluación 32 sesiones y 43.238 minutos, reconciliados contra gate report. Toxic: 402 rachas y 4.666 minutos en evaluación. Sin solapamientos; 7 huecos internos conservados.
- **AUDITADO en código:** la compuerta de semillas compara argmax HMM base, antes de sticky/overlay. Toxic es un overlay de estrés independiente de la semilla HMM. Su determinismo no prueba utilidad ni estabilidad temporal. El STOP ES cuatro climas NO se levanta; calm no equivale a no-toxic.
- **NO MEDIDO:** validación temporal del overlay aislado, costo/riesgo incremental, nuevos outcomes ES/NQ, espejo × IPC y veto imbalance. NQ 0/12 max-T conserva alcance de cruce25/entrada al cierre/control del mismo clima.
- **DISEÑO PARA NICO:** `INVESTIGACION_ES_NQ_L2_ESPEJO_IPC_20260929.md`; revisión anotable de la captura (sin precios/timestamps, no tanda ciega certificada) en plantilla `viewer/nt8_bridge/reviews/espejo_ipc_capture_review.html`. No sustituye al visor único; IPC antes de A, entradas parciales online, imbalance por definir.
- Evidencia reproducible: `artifacts/es_nq_ipc_review_20260929/evidence.json`, herramienta `tools/diagnose_es_context_intervals_20260929.py`. Holdout intacto.
- **MEDIDO 29/09 — CLIMA-NQ-EST-1 (estabilidad temporal de los climas L2 de NQ, target-free):** calm/normal/volatile
  **FAIL** (calm 15 % en W31 → 91 % en W39; normal y volatile colapsan); **toxic PASS** (9,9 % vs 9,5 % entre mitades).
  El modelo de 4 climas NQ no es usable; sólo el binario toxic/no-toxic. La lectura por calm/normal/volatile de
  NQ-CRUCE25-CLIMA queda sin sentido. `RESULTADO_CLIMAS_NQ_ESTABILIDAD_20260929.md`.


## Anexo 29/09 — IPC híbrido MNQ v0.1 (borrador geométrico; no HFTZones)

- **LEÍDO:** IPC NQ de `tools/ipc.py`/`peaks_rule.py` y familia IPC-NIVEL de `tools/ipc_nivel.py` (referencia MES; no confundir con calibración MNQ). Originales y parámetros congelados sin cambios.
- **IMPLEMENTADO, SIN CALIBRAR:** detector MNQ con evidencia `picos + 2*(visitas-1) >= 6`, al menos 3 picos: 6/1 densa, 4/2 mixta, 3/3 separada. IDs independientes; varias zonas pueden coexistir. `docs/research/IPC_MNQ_HYBRID_DRAFT_20260929.md` y JSON.
- **MEDIDO sólo en sintético:** 18/18 pruebas PASS en sandbox y disposición del repo; invariancia de eventos por prefijos, confirmación tardía, cortes de sesión/huecos, ancho limitado, simetría, dos niveles activos simultáneos, bundle intacto e índices fuente. `artifacts/ipc_mnq_hybrid_20260929/evidence.json`.
- **NO MEDIDO:** censo real MNQ y cantidad de zonas por sesión, acuerdo con Nico, sensibilidad, paridad visual causal, espejo × IPC, imbalance, imán y rentabilidad. No hay bundle canónico MNQ en este sandbox; no se reemplaza con NQ. Holdout intacto, outcomes_computed=false.
- **LÍMITE:** eventos CREATE/UPDATE/CLOSE registran disponibilidad causal; snapshot final de zonas sólo para revisar geometría. No usarlo para afirmar IPC antes de A. Replay causal del visor único pendiente; ejecución local target-free documentada para Antigravity.
- **NO MEDIDO 29/09 — IDEA IPC-DIRECCIÓN (MNQ híbrido v0.1):** la escalera de picos anticiparía la dirección de salida.
  Registrada, no ejecutada; requiere bajar densidad (≈ 700 zonas/sesión) y pre-registro. `IDEA_IPC_DIRECCION_ESCALERA_20260929.md`.
- **NO MEDIDO 29/09 — IDEA ES-ESCALONADAS (3–4 picos) + entrada en retroceso:** geometría de 45 marcas de Nico y
  detector ajustado (F1 0,49), pendiente de juicio ✓/✗. Sin outcomes causales. `IDEA_ES_ESCALONADAS_ENTRADA_RETROCESO_20260929.md`.


## Anexo 29/09 — ES-ESCALONADAS: auditoría de precongelamiento (sin retornos)

- **SNAPSHOT, NO CONGELAMIENTO OPERATIVO:** PLANAS/EMPINADAS v2 y confirmación por precio 2 ticks registrados con hash de parámetros y de `escalonadas_det.py`/`peaks_rule.py` en `ES_ESCALONADAS_SNAPSHOT_PRECONGELAMIENTO_20260929.json`; originales y visor intactos.
- **MEDIDO sólo sintético:** 128 caminos (64 semillas × 2 familias), 101 detecciones, 0 discrepancias de campos de detección frente a sus prefijos. Referencia AST sin JIT; no certifica CLI completo, precio intravela ni fills. `artifacts/es_escalonadas_audit_20260929/synthetic_evidence.json`.
- **BLOQUEOS:** `det_t` copia `candles.time` sin contrato de apertura/cierre ni timestamp del cruce; `det_precio` es umbral, no fill; geometría final no es estado al disparo. Faltan bundle/ticks fuente, proveedor, sesiones canónicas, versión por tanda de juicios y paridad detector/visor. `AUDITORIA_PRECONGELAMIENTO_ES_ESCALONADAS_20260929.md`.
- **NO MEDIDO:** retornos, costos, MDE/test familiar, réplica, defensa L2. Manifiesto + OK de Nico siguen obligatorios. No se publicaron capas ni resultados derivados de geometrías con proveedor sin verificar; sólo código/configuración existente y sintético. Holdout intacto.
- **MEDIDO 30/09 — ES-ESCALONADAS feb-2026 (32 celdas, replay tick a tick):** R neto y bruto negativos en las 32.
  Contra control: velas 0/16; precio 6/16 sobre max-T, atribuibles a la mecánica de entrada stop (el control entraba a
  mercado: falla de diseño). Sin edge; réplica de marzo no abierta. `RESULTADO_ES_ESCALONADAS_202602_20260930.md`.
  **NO MEDIDO:** control con misma mecánica stop; filtro de tendencia; defensa L2 (sólo jul–sep).
- **MEDIDO 30/09 — ES-ESCALONADAS v2 ene-2026 (180 celdas: stops amplios, V-shape, BE, tendencia; control misma
  mecánica):** **0/180 sobre max-T**; el filtro de tendencia empeora todo. **Familia cerrada en ES** con ese alcance.
  `RESULTADO_ES_ESCALONADAS_V2_202601_20260930.md`. **NO MEDIDO:** marzo (no abierto), defensa L2, otros activos.
- **MEDIDO 30/09 — MNQ escalonadas (ES ×4,5, confirmación por precio) · posición visual SL 5 t / TP 10R / BE 2R, feb-2026
  (1.720 zonas; caso elegido mirando el gráfico, sin control):** velas como el visor +0,487 R/op (réplica exacta del
  tablero); ticks sin costos +0,371; ticks con bid/ask sin comisión −0,226; con comisión 1,5 t −0,526; con 3 t −0,826.
  El spread solo se come ≈ 0,6 R con un stop de 5 ticks. `tools/escalonadas_posicion_visual.py`, `es_escalonadas/posicion_visual_MNQ_*`.
- **MEDIDO 30/09 — MNQ escalonadas a otras escalas (exploración, feb-2026, sin control, SL escalado del caso visual,
  TP 10R, BE 2R, comisión 3 t):** 150t (185 zonas, SL 14): velas +1,05 · ticks sin costos +0,88 · **con costos +0,25 R/op**
  (PF 1,29, DD 26 R). 500t (51 zonas, SL 26): +0,28 · +0,06 · **−0,37** (deslizamiento de entrada ≈ 3 ticks). Primera
  variante con neto > 0, pero elegida mirando febrero, n chico y sin control: **no es evidencia**; va a la grilla
  pre-registrada (descubrimiento enero, réplica marzo).
- **MEDIDO 30/09 — MNQ-ESCALONADAS-ESCALAS (648 celdas: 6 entradas × 3 escalas × SL/TP/BE; ago-2025..ene-2026, 175
  sesiones, tick a tick con costos y control):** **0/648 sobre max-T**. 25t negativo en todo; 150t ≈ 0 neto; 500t sin
  potencia. Marzo no abierto. `RESULTADO_MNQ_ESCALONADAS_ESCALAS_20260930.md`. **NO MEDIDO:** defensa L2 (jul–sep),
  marcas propias de MNQ, filtros.
- **MEDIDO 30/09 (exploratorio) — espejo × picos antes de A, ES ene-2026, 80 espejos juzgados a ciegas por Nico:**
  continuación más allá de A: «con picos» (25) peor que «sin picos» (55) en las 4 celdas (−0,20 a −0,83 R).
  `IDEA_ESPEJO_X_PICOS_ES_20260930.md`.
- **MEDIDO 30/09 — Contextos L2 MES y MNQ:** ambos **STOP** por semillas (MES 0,56; MNQ 0,71 con calm 0,98 y
  normal/volatile 0,45/0,31). Sin climas de 4 estados en ES, MES ni MNQ. `RESULTADO_CONTEXTOS_L2_MES_MNQ_20260930.md`.
  **NO MEDIDO:** estabilidad temporal de *toxic* en MES/MNQ.


### GC L2 a precio fijo — piloto P0, 30/09/2026 (R02 / I-3)

- **MEDIDO (mecánico, sin retornos):** dos ejemplos privados GC NT8 de Kaggle v2,
  cuatro parquet reconciliados. 863.066 caídas netas de tamaño a precio fijo; 39.020
  con prints compatibles previos; 14.100 recuperaciones observadas en ≤5 s y hasta
  ≥70 % del tamaño previo. Son episodios compatibles, **NO icebergs ni absorción
  confirmada**. Publicación causal al observar recuperación; no backdating.
- **MEDIDO (QA):** 12/12 unit tests del tracker; sin errores de grilla/filas/reloj
  relativo en los cuatro archivos. 34 grupos de inicialización inválidos excluidos
  antes del primer LAST del archivo corto. Conteos y censuras reconciliados.
- **NO MEDIDO:** utilidad como filtro, controles negativos emparejados, defensa
  efectiva, transferibilidad ES/MNQ, cola/fills, retornos y costos. MBP no proporciona
  IDs de orden; reloj absoluto de estos manifiestos sin certificar. No se rescatan
  climas STOP ni se modifica la validación MNQ en curso. Holdout intacto.
- Plan, código, evidencia y acta: `PLAN_GC_L2_PRECIO_FIJO_P0_20260930.md`,
  `tools/gc_l2_fixed_price_probe.py`,
  `artifacts/gc_l2_fixed_price_p0_20260930/evidence.json`,
  `RESULTADO_GC_L2_PRECIO_FIJO_P0_20260930.md`. Raw y episodios con precios quedan
  privados. Retornos requieren manifiesto/pre-registro + OK de Nico.


### GC L2 P1 — controles históricos y traspaso local, 30/09/2026

- **MEDIDO (descriptivo mecánico, continuación P0 R02/I-3):** controles históricos
  1:1 sin reemplazo ni selección por desenlace, mismo lado y bandas de profundidad,
  tamaño, caída y actividad. 3.992 y 31.577 pares;
  recuperación observada / todos los pares: 29,5 % vs
  37,0 % y 38,0 % vs
  45,5 % (positivos con prints vs control sin prints).
  **No mayor recuperación con prints**, no inferencia causal/predictiva, censuras incluidas.
- **MEDIDO (QA):** reproducción exacta P0; 12 tests nuevos, dos prefijos reales
  invariantes y balances independientes. Pérdida puntual de diez niveles visibles
  [10,5] cerró 15 episodios no positivos en 20260615, sin alterar los eventos P0.
- **MEDIDO (feature descriptiva):** recuperación previa al mismo precio en 60 s:
  127/1.282 y 3.347/12.818. No significa iceberg ni defensa efectiva.
- **NO MEDIDO:** persistencia/defensa incremental, utilidad en señales, ES/MNQ,
  retorno/fills/costos. Controles P0 antes pendientes quedan medidos aquí bajo
  este alcance; no confirmación independiente (mismos dos ejemplos).
- Acta `RESULTADO_GC_L2_CONTROLES_P1_20260930.md`; plan homónimo; código
  `tools/gc_l2_historical_controls.py`; evidencia `artifacts/gc_l2_controls_p1_20260930/`.
  Visor, datos y adapter propios ES/MNQ pendientes para Claude local:
  `HANDOFF_LOCAL_CLAUDE_GC_L2_P1_20260930.md`. No se lanzó otra sesión.
  Nada de retornos sin manifiesto + OK; nada de raw público; holdout intacto.


### MNQ escalonadas × L2 — preparación nube, 30/09/2026

- **PREPARADO / NO MEDIDO EN MNQ REAL:** emisor incremental de PLANAS150t,
  confirmación precio ES×12,42 (X25/max_step25/min_pull62), cierre de vela/grupo
  como disponibilidad conservadora; distinto del fill intrabar previo.
- **MEDIDO (QA técnica):** 19 tests, paridad geométrica por prefijos sintéticos;
  exporter smoke GC9.000 grupos, 7 velas150t y0 señales (NO evidencia MNQ).
  Schema nativo sin price, hashes, overlap/reset, features null y landmarks causales.
- **NO MEDIDO:** utilidad/filter support de MNQ, fills/costos/retornos, persistencia
  de defensa. Raw L2 MNQ no encontrado en Kaggle conectado; está en la PC.
  Exporter `tools/mnq_l2_prepare.py` + handoff de UN comando; no trabajo de diseño
  pendiente para Claude. Nuevo filtro2 recoveries10s es propuesta, no validado.
- **BORRADOR, requiere OK antes de outcomes:**
  `BORRADOR_MNQ_ESCALONADAS_L2_20260930.md`; preparación
  `PREPARACION_MNQ_ESCALONADAS_L2_20260930.md`;
  `HANDOFF_MNQ_L2_UN_COMANDO_LOCAL_20260930.md`. No hay runner financiero aprobado.
- **IDEA separada / NO MEDIDA:** segundo impulso B→A, landmark50 % con L2;
  helper `tools/mirror_landmark.py` no detecta A/B ni predice precio.
  Todos los intentos, no sólo espejos completos;
  `IDEA_ESPEJO_L2_LANDMARK_50_20260930.md`. Semántica por confirmar.
- Climas STOP no rescatados; visor/raw no modificados; nada de retornos ni holdout.


### MNQ primera sesión L2 + requisito de potencia + GC pendiente, 30/09/2026

- **MEDIDO (QA target-free MNQ real, 20260629):** procedencia adjunto/código CRLF exacta, 19.569 velas150 y31 señales reproducidas. Raw hashes sólo recibo local, no rehash independiente de raw en nube.
- **MEDIDO (soporte propuesto en decisión V1):** 26 nivel fuera top10, 3 visible false, 1 visible true, 1 libro no disponible =31. 27 máscaras null; NO false. Libro válido18.870/19.569 velas; 699 ausentes, causa por racha pendiente.
- **STOP V1 PUBLICACIÓN LIVE:** reconoce fin de grupo al observar fila siguiente pero etiqueta disponibilidad al grupo viejo. No seguir52 ni calcular fills/outcomes así. V1 congelado; V2 candidato separa snapshot/publicación/observación pre-pico y asociación posterior, requiere opt-in explícito.
- **MEDIDO QA V2:** 5 tests; smoke GC9.000 grupos/7velas/0señales, prefijo4velas publicadas idéntico. NO validación V2 MNQ ni adaptación GC.
- **NO MEDIDO:** persistencia útil, retorno/costos, potencia económica/MDE, soporte de V2 en MNQ. Nico exige suficientes señales OBSERVABLES e independientes; no ajustar por ganancias.
- **GC PENDIENTE:** Nico propone adaptar escalonadas por alta frecuencia visual. Falta identificar configuración elegida, paridad, frecuencia por sesión, soporte L2 y muestra propia. No copiar MNQ ni costos.
- Acta `RESULTADO_MNQ_ESCALONADAS_L2_PRIMERA_SESION_TARGETFREE_20260930.md`; evidencia agregada `artifacts/mnq_l2_first_session_20260930/`; handoff `HANDOFF_MNQ_L2_V2_DIAGNOSTICO_UNA_SESION_20260930.md`; plan `PLAN_MNQ_GC_ESCALONADAS_MUESTRA_Y_POTENCIA_20260930.md`. Nada de raw/precios público; sin outcomes nuevos; holdout oct+ intacto.


### Pedido a Claude: GC variantes + exact4 y MNQ V2, 30/09/2026

- **REGISTRADO / NO MEDIDO:** Nico solicita varias configs GC, incluida exactamente4 miembros por zona/disparo al4º. C0 actual local por capturar; defaults repo NO acreditan configuración elegida. C1exact4,C2densas,C3separadas,C4planas propuestas relativas a C0; números efectivos se congelan tras captura, antes del censo.
- **DISEÑO / NO IMPLEMENTADO:** `nmin4` no basta; sin backfill extra/crecimiento, bloques disjuntos, confirmación causal4º, no rescate al5º ni veto futuro. Tests y censo de soporte/frecuencia solicitados.
- MNQ V2: una sesión + tests + paquete para nube; no ampliar52 automáticamente. Configurar y hacer QA target-free no autoriza retornos/costos. Suficientes señales observables, clusters/MDE antes de economía. Holdout oct+ intacto.
- Traspaso canal: `docs/audits/ENTRADA_077_MNQ_L2_GC_ESCALONADAS_EXACT4_20260930.md`; propuestas `docs/research/GC_ESCALONADAS_CONFIGS_TARGETFREE_PROPUESTAS_20260930.json`. No nueva corrida ni resultados financieros en esta entrada.


### MNQ V2 auditado y GC exact4 preparado en nube, 30/09/2026

- **MEDIDO QA/target-free:** MNQV2 adjunto CRLF exacto,19.569velas/31señales igualesV1y replay; publicación separada en metadata. Rawreceipt idéntico, no rehashMNQraw aquí.26/17/4 observables antes-extremo/grupo-publicado/confirmación;6/1/1true regla compatible; no iceberg/edge.699velas sinlibro=685bootstrap+14incompletas.
- **CONTROL GC IDENTIFICADO POR REPORTE:** febrero25T_HFT capa__nq__n4__precio,escala3,51,w1/gap30/step49/pull25/conf28,nmin4.1459zonas no recontadas; bundle/hash privado pendientes. Corroboración numérica contra código, no paridad independiente.
- **IMPLEMENTADO QA:** exact4 causal disjunto congelado, resolver/capturador/censo;26tests+repo-layout PASS. Perfiles C0(30/49/25),C1igualexact4,C2(23/49/19),C3(45/49/38),C4(30/25/25);conf28común. C0original no reemplazado. GCsmoke mecánico fijo sobre92/616velas150 dio0/0eventos: no prueba emisión real positiva ni configuraciónactual, no se aflojaron umbrales.
- **NO MEDIDO:** utilidad de historiaL2, potencia/retornos/costos, frecuencia deexact4 sobreGCfeb25T, paridad/visorlocal, samplefull52. Diseñado no equivale a edge. Nada futuro/oct+niLucid/raw/preciosrepo.
- Actas `RESULTADO_MNQ_L2_V2_PRIMERA_SESION_TARGETFREE_20260930.md` y `PREPARACION_GC_ESCALONADAS_EXACT4_20260930.md`; entrada078 y `HANDOFF_LOCAL_GC_EXACT4_CODIGO_LISTO_20260930.md`; artifacts separados. Actualiza estado077, no borra historia.


## GC exact4 — censo febrero auditado y puente de visor (2026-09-30)

**MEDIDO target-free:** ZIP privado recontado C1 1.605 (784H/821L), C2 1.817 (893H/924L), C3 1.091 (545H/546L), C4 665 (359H/306L). 101.889 velas declaradas; 20 IDs de sesión con eventos, 21 listados con uno cero. Hash de captura/configs/código CRLF verificados. Cuatro miembros congelados, sin reutilización dentro de perfil/lado, conciliación completa de picos elegibles.

**NO MEDIDO / ABSTAIN:** no raw ni bundle original en ZIP; hash de barras/bundle sólo declarado. C0 1.459 reportado, no recontado. Cero PASS de publicación = todos los metadatos raw nulos: ABSTAIN, no FAIL ni certificación de ejecución. No retornos, MAE/MFE, TP/SL, fills, costos, potencia o ventaja. Los 5.178 registros de perfiles solapados no son muestra independiente.

**IMPLEMENTADO:** `tools/gc_exact4_review.py` + `viewer/nt8_bridge/gc_exact4_review_guard.js`, 13 tests Python/12 JS nuevos PASS además de los 26 del core. Exporta sólo con hash/paridad del bundle y crea copia `index_gc_exact4.html`, sin modificar índice original ni C0, sin posiciones; raw pendiente visible. QA sintético desktop/mobile; geometría febrero sin revisar. Cortina no certifica tanda ciega.

Acta: `docs/research/RESULTADO_GC_EXACT4_CENSO_TARGETFREE_20260930.md`. Handoff: `docs/research/HANDOFF_LOCAL_GC_EXACT4_REVIEW_20260930.md`. Evidencia agregada: `artifacts/gc_exact4_censo_audit_20260930/evidence_aggregate.json`. Material privado no se publica. STOP antes de outcomes sin manifiesto+OK de Nico.


## L2 as-of GC y preparación de espejo — 30/09/2026

**MEDIDO QA/target-free:** extractor neutral de presión/soporte y publicación en primera fila real posterior; registro A/B congelado de todos los intentos, sin backdate ni selección de espejos completos. 39 tests PASS; replay de 6.281.338 filas de los DOS ejemplos GC legacy ya expuestos; 1.619 paquetes contrastados con raw y fórmulas; 97 paquetes de prefijos reales idénticos. Gates concilian; EOF no publicado; ventana OFI incompleta null, precio fuera top-10 UNKNOWN. No son trades independientes ni datos nuevos de confirmación.

**NO MEDIDO:** eventos reales GC/MNQ/espejo enlazados (0), utilidad predictiva, labels/modelos/outcomes, retorno, fills/costos, potencia o ventaja. GC febrero/raw-publicación y calibración siguen pendientes. Climas STOP no se rescatan; no ampliar automáticamente 52 sesiones MNQ. Holdout octubre+ intacto; privados/precios/packets fuera del repo.

**IMPLEMENTADO / BORRADOR:** `tools/l2_asof_features.py`, `tools/mirror_l2_attempts.py`, smoke legacy y 39 tests. Pregunta propuesta B→A al50%, baseline precio vs precio+L2; instrumento/horizonte/invalidación/splits/potencia requieren manifest y OK separado. OFI externo contemporáneo y QI siguiente-mid no prueban un impulso entero. Mid ponderado y QI touch algebraicamente redundantes.

Acta: `RESULTADO_L2_ASOF_GC_Y_PREPARACION_ESPEJO_20260930.md`; plan, protocolo y handoff en docs/research. Evidencia agregada: `artifacts/l2_event_research_20260930/evidence.json`. Ejecución staging aislado con hashes exactos desde767e30b; no se afirma ejecutar un commit limpio posterior. Código/acta/registro se publican juntos.


## GC Kaggle ticks × L2 — identidad y barras target-free, 30/09/2026

**MEDIDO:** ticksGC08-26 KaggleV2 SHA7976fbe9… bitwiseverificado. May31: cinta COMPLETA de13.913trades idéntica por(timestamp+3h,precio,volumen) y orden.556barras25operaciones,546conlibro previoPASS/10bootstrap,545ventanaOFIcompleta;13tradesenbarra parcial.80barras deprefijo2000trades idénticas. Verificaciónindependiente de todas556barras y546fórmulas;4testsidentidadPASS. Libro publicado ESTRICTAMENTE ANTES deltimestamptick; jamás grupo simultáneo ni nearest-neighbor.

**ABSTAIN separado:** June15 precio/volumen secuencia completa coincide pero5timestampdifieren6,877–34,877ms. Sin reparar/redondear/rellenar. Correspondencia certificadaempíricamente sóloMay31/política previa, nootrasfechas/fills/latencia/interleavingMBO.

**NO MEDIDO:** zonas/espejosreales enlazados, predictibilidad/retornos/modelos/P&L/potencia/ventaja. No sustituyebarrasGCfeb niapruebacalibración detector. Holdout intacto. Datos/eventos/preciosprivados, acta/código/registro enmismocommit. Acta: `RESULTADO_GC_KAGGLE_TICKS_X_L2_TARGETFREE_20260930.md`; plan aparte; evidencia `artifacts/gc_tick_l2_join_20260930/evidence.json`.


## GC eventos × L2 con lógicas actuales — 30/09/2026

**MEDIDO target-free:** May31GC08-26,556barras25operaciones, fuenteKaggle y L2 verificada. C0min4/C1exact4/C2densas/C3separadas/C4planas=8/8/10/5/3eventos; libroestructuralprevioPASS en todos. Nivelvisible=1/1/1/0/0.34registros NOindependientes,18claves(barra,lado,nivel), no18trades iid. Parámetros sinajuste.

**Espejo:** `.detect`defaults(minW17,maxbars20,retr0.3), sinrun/procesar/estadosposteriores:161A/Bconfirmados y1sinconfirmarpor tiempo.161registrosL2PASS, Avisible17.50%:58prospectivosL2PASS/Avisible5;30tardíos enprimeraobservación,3Ayaalcanzado y70nuevoextremoBanteslandmark. Todosreceiptsconciliados. Noacierto/fracaso económico ni llegadasposteriores aA.

**QA:** 7tests yprefix200barrasPASS;286paquetesverificadoscontrafronterasraw/fórmulas/visibilidad. PublicaciónL2 estrictamenteanterior; eventoenprimerrawtimestampmayor al cierre. Edadmax zonas2880ms/registros3688ms/landmarks6904ms;freshnessoperativono ratificado.

**NO MEDIDO:** predicción/retornos/P&L/fills/costos/potencia; no selección deperfilporbeneficio ni ajusteparamétrico; noGCfeb,Jun15ABSTAIN,holdoutintacto. Acta `RESULTADO_GC_EVENTOS_L2_LOGICAS_ACTUALES_20260930.md`; código `tools/gc_current_logic_l2_census.py`; evidencia `artifacts/gc_events_l2_20260930/evidence.json`. Privados/eventos/preciosfuera repo. Código/acta/registroen mismocommit.

## GC presión C2 y espejo50 — 30/09/2026

**MEDIDO target-free:** C2 congelado w1/gap23/step49/pull19/conf28, cuatro exactos. Censo febrero1817zonas:20/21 IDs≥4;20260201=0 preservado, no garantía diaria. Captura May31:C2 10/10 primarias con book estrictamente previo/frescura≤1s; espejo50 53/58,5 stale. QI/OFI históricos sin score/modelo;101filas baseline auditadas/9testsPASS;161receipts conservados.

**NO MEDIDO:** predictibilidad del espejo, retorno/costos/potencia, frecuencia de L2 fresco en múltiples sesiones. Acta `RESULTADO_GC_PRESION_C2_20260930.md`; evidencia y config `artifacts/gc_pressure_c2_20260930/`; código `tools/gc_pressure_panel.py`. C0/visor intactos; holdout intacto; privado fuera repo.

## ES IPC y tick relativo — 30/09/2026

**MEDIDO target-free:** exportKaggle v2 ES03/GC04, febrero UTC. ES22.835.690prints/913.414barras25t. Familias originales conf2:PLANAS2706eventos,24/24fechas observadas≥4 (min5);EMPINADAS937,20/24≥4 (min1). Cuatro fechas calendario sin datos separadas, no cero inventado. Ancla UTC nueva: NO paridad con bundle del visor.15claves de evento compartidas no iid.

Quotes abiertas positivas, por registro:ES21.174.154/22.835.655=92,7240930904% de1tick;GC97.852/2.546.869=3,8420507690%. Proxy export, no tiempo ponderado ni costo ejecutable. Auditoría pandas independiente concilia raw;6tests/8prefijos/48paridades familia-fecha con detector original PASS; repetición igual.

**NO MEDIDO:** L2 ES, ventaja/predicción/fills/P&L/potencia independiente. Publicación raw ABSTAIN; climas ES STOP no rescatados. Acta `RESULTADO_ES_IPC_TICK_SUPPORT_20260930.md`; evidencia `artifacts/es_ipc_tick_support_20260930/evidence.json`; código `tools/es_ipc_tick_support.py`. Sin recalibración/visores/raw al repo.

## Continuación puente L2 GC / ES — 30/09/2026

**MEDIDO ingeniería target-free:** preflight instrument-neutral con custodia/manifiesto/grilla propia y tape ordenado sinnearest.14testsPASS, fixtureES sintética end-to-endPASS (NO L2ESreal). Semántica NT8 conserva L1 DAILY_VOLUME/otros no-trade y cola level10; solo LAST=2 al tape. GCMay31 13.913printsPASS;Jun15 92.515prints/5timestampsdistintos yprecio/volumenidénticos ABSTAIN. Raw sincorregir.

**NO MEDIDO:** bookESreal/másGC/replaynuevo/predicción/P&L/fills/costos/potencia. ListadoKaggleaccesible sólo2L2GC;noESrawexpuesto. Pedido mínimo local en `ENTREGA_LOCAL_L2_GC_ES_20260930.md`;borradormanifiesto50%vsbaseline precio NO aprobado/noejecutable. Acta `RESULTADO_L2_PAIRING_GC_ES_20260930.md`;evidencia `artifacts/l2_pairing_next_20260930/evidence.json`. Visores/C0/climasSTOP/holdoutintactos.

## GEX-1 — régimen de gamma de dealers (SqueezeMetrics, día previo) — 06/10/2026
Manifiesto `docs/research/GEX1_REGISTRO_Y_MANIFIESTO_20261006.md` (OK de Nico). Kaggle `edgelab-gex1-20261006`;
resultados `docs/research/GEX1_RESULTADOS_20261006.{json,md}`. Sólo información, sin P&L. Holdout intacto.
- MEDIDO: spot USA500 2023-01 → 2025-06 (757 sesiones; gex<0 = 39): **amplitud intradía mayor con gex<0** —
  rango RTH / media previa +0,54 (Holm 0,015, MDE 0,48); vol. realizada / media previa +0,59 (Holm 0,006, MDE 0,46).
  Control por volatilidad previa débil (sólo 2 quintiles con ambos grupos); allí la diferencia se mantiene.
- MEDIDO, NO DETECTADO: continuación de última media hora (I2) y autocorrelación intradía (I3), en spot y MES.
  MDE altos (I2n ≈ 1,9 sd; ac1 ≈ 0,08 spot): el efecto de Baltussen/Barbon-Buraschi no se replica a este poder.
- SIN POTENCIA: MES NT8 2025-09 → 2026-09 tiene **9** sesiones con gex<0 de 248 (año de gamma positivo casi
  continuo). Nada interpretable en futuros.
- NO MEDIDO: confusor "día posterior a caída fuerte" (gex<0 sigue a caídas; la volatilidad se agrupa) — falta
  controlar por |retorno| y retorno del día previo antes de atribuir la amplitud al gamma. Walls/flip como soporte,
  resistencia o imán: sin historia causal suficiente (SquawkFlow desde 2026-07-28).
- Bug corregido antes de interpretar: test con obs NaN recibía p≈0 (MES I2d); ahora p=1 y Holm recalculado.

## aVolClusterPOI v0.5 — paridad MNQ 12-26 50t — 05/10/2026
- MEDIDO: paridad NT8↔Python **PASS 934/934** (creación al ms, geometría, MaxAge), chart 2026-07-15 → 09-24, Do not
  merge. Acta `docs/parity/PARIDAD_AVOLCLUSTER_MNQ1226_50T_20261005.md`. Causas raíz: footprint de subserie 1-tick
  (empate de timestamp → barra siguiente; fuera de rango descartado), tick en pausa CME, ventana, MaxAge.
- NO MEDIDO: AT_PRICE, FIRST_TOUCH, invalidación CloseThrough/FirstTouch; otros instrumentos/bar_spec con esta regla.

## AVCL-VOL-1 MYM (exploratorio, sin paridad) — 06/10/2026 — REFERENCIA
- MEDIDO: información de volatilidad/expansión tras la creación de zonas (RTH, 12 pruebas, Holm). **AT H10 expansión de
  rango D +0,067 [0,027; 0,106], Holm 0,004** (MDE 0,070), la única que sobrevive. OFF H10 expansión +0,036 (Holm 0,12, no).
  A H200 hay compresión. Desglose OFF: el efecto H10 viene de las resistencias (+0,047), no de los soportes.
  Acta: `docs/research/AVCL_VOL1_RESULTADOS_MYM_20261006.md`. Queda como hipótesis de referencia para otros análisis.
- NO MEDIDO: paridad MYM; P&L; control de volumen alto sin zona; replicación en MNQ (en curso); lado pre-registrado.

## Exploración EdgeReplica MNQ + MGC 04:15 post-publicación — 06/10/2026
- MEDIDO (exploración, sin custodia de holdout por decisión de Nico): EdgeReplica MNQ 11-sep → 6-oct, 163 ops,
  −6,3 USD/op [−25; +13]. Paridad con NT8: el 5-oct coincide al centavo (+145,70). MGC 04:15 corto tras subida:
  12 ops, +16 USD/op [−2; +37]; sin condición rinde igual. Acta `docs/research/explo_edgereplica_mgc_20261006/RESULTADO.md`.
- NO MEDIDO: prueba limpia para estas familias (el holdout desde el 1-oct quedó visto); MGC con n suficiente.

## AVCL-VOL-1 MNQ (con paridad) — 06/10/2026 — REPLICA LA REFERENCIA
- MEDIDO: AT H10 expansión de rango +0,081 [0,072; 0,089], Holm 0,0006, MDE 0,012. Replica MYM (+0,067).
  También sobreviven OFF H10 `y_rg` +0,063, OFF H50 `y_rg` +0,012 y AT H10 `y_rv` +0,047. Después hay compresión
  (H50/H200 `y_rv` < 0, no testeada). Resistencias > soportes, igual que en MYM (descriptivo).
  Acta: `docs/research/AVCL_VOL1_RESULTADOS_MNQ_20261006.md`.
- NO MEDIDO: control de volumen alto sin zona; contexto pre-registrado; P&L; la diferencia de densidad de zonas
  MYM/MNQ (6 contra 77 por sesión).

## aVolClusterPOI — función de soporte/resistencia — NO MEDIDO (registro 06/10/2026)
- Nico observa en el chart que las zonas actúan como soporte/resistencia. **Nada de lo medido hasta ahora
  (AVCL-VOL-1/2, información de volatilidad) evalúa esa función.** Un nulo de VOL-2 no la toca.
- Necesita un protocolo propio: población de primer toque **y** estado continuo, nulo con zona espejo o desplazada
  (lección BigTrap2: F2.7–F2.9), MDE y los dos canales.
- El cache de VOL-2 (zonas con toques/MFE/MAE) se puede reutilizar.

## AVCL-VOL-2 A+B MNQ — 06/10/2026
- MEDIDO: la zona agrega información de expansión de rango **más allá del volumen y la intensidad**: AT `y_rg` A1
  +0,081, **A2 contra volumen alto sin zona +0,054 (Holm 2e-9)**; OFF A2 +0,072. Barra por barra, la volatilidad no
  difiere del volumen alto (AT `y_rv` A2 ≈ 0). Curva B: el rango por barra sólo sube en 1–3 barras, así que la
  expansión de 10 barras es **desplazamiento**, no barras más grandes. Acta `AVCL_VOL2_AB_RESULTADOS_20261006.md`.
- NO MEDIDO: dirección del desplazamiento (C); soporte/resistencia; curva B para volumen alto (muestra de 495,
  diseño restrictivo).

## AVCL-SR-DIR MNQ — 06/10/2026
- MEDIDO: sin efecto, con potencia alta. Dirección después de la creación (H10/H50, MDE 0,4/0,8 ticks) y respeto en el
  primer toque contra zona espejo (65,2 % contra 65,7 %, MDE 1,4 pp). El primer toque es **inmediato** (mediana de
  3 barras, 95 % de toque). Acta `AVCL_SR_DIR_RESULTADOS_20261006.md`.
- NO MEDIDO: **revisita** (el precio se aleja k ticks y vuelve), toque n-ésimo, confluencia y delta de la zona.
  Soporte/resistencia NO queda cerrado.

## AVCL-VOL-3 MNQ — 06/10/2026
- MEDIDO (8/8 Holm): dosis monótona (OFF Q1 0,027 → Q5 0,087); la zona angosta expande más (−0,07 por SD de ancho);
  compresión posterior confirmada (H50/H200 `y_rv` < 0); efecto en ETH; estable en los 6 contratos y en las franjas.
  Exceso de unos 2 ticks a H10, contra un costo de 5,8. Acta `AVCL_VOL3_RESULTADOS_20261006.md`.
- NO MEDIDO: **distribución/colas del desplazamiento con signo** (SR-DIR midió sólo la media; ver pedido de Nico);
  delta; sensibilidad de parámetros; 200t (paridad en curso).

## AVCL-DIST MNQ — 06/10/2026
- MEDIDO: distribución completa del desplazamiento. A H10 las **dos colas suben igual** (alejamiento +1,08 pp,
  regreso +1,11 pp, Holm <1e-4): la expansión es **bidireccional**, y la media ≈ 0 de SR-DIR no escondía dirección.
  En zonas angostas, ambas colas suben unos +3,4 pp (+40 % relativo). Q5 de anomalía: regreso > alejamiento
  (descriptivo). Acta `AVCL_DIST_RESULTADOS_20261006.md`.
- NO MEDIDO: la asimetría de regreso en alta anomalía como prueba pre-registrada; colas en 200t.

## VolTicksDef (familia VTD) — 06/10/2026
- MEDIDO: paridad NT8 PASS (MNQ 12-26 150t, 547/547, P² exacto). Expansión propia H10: 150t +0,052, 50t +0,037,
  sobrevive contra volumen alto (A2); cola sin signo +2,4 pp. Cara a cara 50t: AVCL sin VTD +0,065, VTD sin AVCL
  +0,038; casi no se solapan (5–13 %) → **complementarias**. Ancho al revés que AVCL (barra ancha → más expansión).
  Acta `VTD_VOL1_RESULTADOS_20261006.md`.
- NO MEDIDO: dirección por la vela marcada; señal combinada; toques/estado de las zonas VTD; ancho sin la barra en la
  ventana previa.

## AVCL-CIERRE MNQ — 06/10/2026
- MEDIDO:
  - el **delta no orienta** la expansión (media s_d ≈ 0, MDE 0,016–0,019; las colas significativas eran la expansión
    bidireccional, por un diseño de prueba mal planteado y corregido en el acta);
  - asimetría de regreso en Q5 de anomalía, +1,7 pp (Holm 0,041);
  - 200t replica el rango (AT A2 +0,065);
  - grilla: el efecto depende de k y W (k1,5/p98 más fuerte, k3,0 nulo, W20 anómalo por posible artefacto de ventana).
  Acta `AVCL_CIERRE_RESULTADOS_20261006.md`.
- NO MEDIDO: **`y_rg` con la ventana previa fuera del bloque creador** (verificación del artefacto, también para la
  base); otros instrumentos; contexto por estado.

## AVCL-EXIT MNQ — 06/10/2026
- MEDIDO: la primera salida de la banda (k 4/8/16) **no continúa más** que la de pseudo-zonas de igual geometría
  (c_10/c_50 ≈ 0, MDE 0,3–0,8 ticks). Después de la salida hay más rango para k chico, pero bidireccional (la cola de
  falla sube más que la de continuación). Las salidas son casi todas inmediatas (lag mediano 1–9 barras).
  Acta `AVCL_EXIT_RESULTADOS_20261006.md`.
- NO MEDIDO (candidata): **salida tras consolidar** (≥ 5 cierres dentro), c_10 +0,6 ticks, cola de continuación H50
  +2,3 pp; descriptivo, sin potencia. Requiere pre-registro y más datos.

## AVCL-PRE — 06/10/2026 — CORRIGE LAS ENTRADAS AVCL-VOL-1/2/3, DIST, CIERRE y EXIT (expansión)
- MEDIDO: con la ventana previa **fuera** del bloque creador, la "expansión" de aVolClusterPOI desaparece (AT +0,015,
  OFF −0,010; antes 0,081 / 0,055). **Era un artefacto**: el bloque creador está comprimido por construcción y era el
  denominador. La zona AVCL es un **marcador de compresión local** tras el cual el rango se normaliza. Las magnitudes de
  expansión, la dosis, el efecto del ancho y las colas de DIST/EXIT de las entradas anteriores quedan **reinterpretadas
  como rebote del rango**, no como expansión.
- VolTicksDef **sobrevive** (150t +0,049, 50t +0,019).
- Siguen en pie, porque no dependen del denominador: los nulos de dirección y la asimetría de regreso Q5.
  Acta `AVCL_PRE_RESULTADOS_20261006.md`.
- NO MEDIDO: candidatas restantes de AVCL (salida tras consolidar, regreso Q5) con métricas sin el bloque; VTD en
  profundidad (dirección por vela, combinación, otros instrumentos).

## VTD-DIR etapa 1 (lado del tramo largo en marcas VolTicksDef 150t) — 06/10/2026
- MEDIDO:
  - **EMA, 100 celdas (10 periodos × 5 distancias × 2 H): ruido** (51/100 positivas, max-T mínimo 0,56);
  - VWAP, desbalance, vela, momentum y extremos: ninguno pasa el descubrimiento (Holm);
  - etapa 0: la eficiencia (tendencia/rango) no persiste y la amplitud sí.
  Acta `VTD_DIR_E1_RESULTADOS_20261006.md`.
- NO MEDIDO (candidata): **la vela de la marca VTD como predictor del lado** (+0,044 descriptivo sobre los 6 contratos,
  después del fallo formal, sin controlar la deriva). Requiere pre-registro y prueba única en otros instrumentos.

## VTD-VELA — 06/10/2026
- MEDIDO (prueba única pre-registrada, ES/YM/RTY/MGC, 6.495 marcas): la vela de la marca VolTicksDef **no** anticipa el
  lado del tramo largo (−0,013, p 0,93, MDE 0,022; acierto 49,6 %). **Descartada.** Acta `VTD_VELA_RESULTADO_20261006.md`.

## VTD-BRACKET (P&L, OK de Nico) — 06/10/2026
- MEDIDO: bracket bilateral sobre marcas VTD 150t, MNQ y ES, 4 celdas: **pierde en todas** (MNQ ≈ −3 USD/trade,
  ES ≈ −38 USD/trade), y **las marcas no superan a barras al azar** (en ES rinden peor, z −3,8). Descartado en el
  descubrimiento; confirmación no corrida. Acta `VTD_BRACKET_RESULTADOS_20261006.md`.

## Régimen en escala mayor — ES M1 2015–2026 — 06/10/2026
- MEDIDO (target-free): ni la dirección ni la eficiencia persisten de 30 min a semanas; reversión leve a 3 h (−0,027)
  y día a día (−0,089); la amplitud es persistente incluso desestacionalizada. Acta `REGIMEN_ESCALA_ES_M1_20261006.md`.
- NO MEDIDO: otras clases de activo (falta el M1 de GC, 6E y ZB); reversión como hipótesis formal.

## AVCL-RACIMO — 06/10/2026
- MEDIDO: el racimo (burst ≥ 3) anticipa **menos rango que antes del racimo** a H50 (−0,06; denso −0,12; 50t y 25t), es
  decir, consolidación que continúa. Dirección en OFF: **regreso/ruptura** (s < 0): 50t H50 −0,039 (Holm 0,054),
  25t −0,057 (p 5e-9). Acta `AVCL_RACIMO_RESULTADOS_20261006.md`.
- NO MEDIDO: réplica en ES/YM/RTY/MGC (prueba única pre-registrada pendiente).

## AVCL-RACIMO-CONF — 06/10/2026 — PRIMERA DIRECCIÓN CONFIRMADA
- MEDIDO (prueba única pre-registrada, ES/YM/RTY/MGC 50t): en zonas OFF en racimo el precio **vuelve/atraviesa** más
  que en las aisladas: β s_50 = −0,038, p = 0,020. Los 4 instrumentos negativos; ES el más débil. La consolidación
  posterior también replica. Acta `AVCL_RACIMO_CONF_RESULTADO_20261006.md`.
- NO MEDIDO: P&L con fricción de una regla basada en esto.

## RETRACTACIÓN AVCL-RACIMO / RACIMO-CONF — 06/10/2026
- La "primera dirección confirmada" era un **artefacto de look-ahead** en la definición de "aislada" (usaba las 200
  barras posteriores). Con la aislada causal: MNQ −0,006, confirmación −0,007 (z ≈ −0,5). **Sin efecto direccional de
  los racimos.** La consolidación posterior queda en suspenso (misma comparación sesgada). Acta
  `AVCL_RACIMO_RETRACTACION_20261006.md`.

## HFTV4-RETORNO (MNQ, flecha de alejamiento) — 06/10/2026
- MEDIDO: después de alejarse 3 alturas sin recorrerla, el precio vuelve a la zona HFT el 77 % de las veces (≤ 200
  barras), contra el 75 % de una pseudo-zona con la misma regla. **+0,9 pp**: significativo, pero despreciable. El camino
  de vuelta es igual al del azar (mediana de 6 alturas de excursión en contra, 27 barras). Acta
  `HFTV4_RETORNO_RESULTADOS_20261006.md`.

## EMA-ALIGN (EMA 200/500/2000, 2t, MNQ y MGC) — 07/10/2026
- MEDIDO: 108 celdas (3 entradas × SL × R × BE × 2 instrumentos), P&L neto tick a tick: **todas negativas**
  (MNQ ≈ −2,6 a −3,2 USD/trade; MGC −3,6 a −5,7). Ninguna supera a la dirección al azar con max-T. Las entradas en el
  pullback a la EMA son peores que al azar. Confirmación no corrida. Acta `EMAALIGN_RESULTADOS_20261007.md`.

## EMA-SEP (contrarian, 3 EMAs separadas, 10t, MNQ/MGC) — 07/10/2026
- MEDIDO: 972 celdas (pct 90/95/99 × agotamiento × entrada × SL/TP/BE × 2 inst.): **0 pasan max-T**. La reversión
  supera levemente al azar (z máx 3,2, p max-T 0,16), pero en MNQ el neto es negativo (mediana −2,5 USD/trade). Acta
  `EMASEP_RESULTADOS_20261007.md`.
- EMASEP-MGC150 (07/10/2026): MGC 150t, 486 celdas. 0 pasan (mejor p max-T 0,53). Neto mediano +1,9 USD, pero con
  38–98 trades por celda: **no concluyente por N**. Acta `EMASEP_MGC150_RESULTADOS_20261007.md`.

## AVZP2-REBOTE (aVolZonePOI2 y aVolClusterPOI, MNQ 200t, primer regreso) — 07/10/2026
- MEDIDO: rebote de 2 alturas al primer regreso contra pseudo-zonas. AVZP2 todas −0,1 pp; azules −1,8 pp; AVCL
  +0,2 pp: **ninguna rebota más que el azar**, y AVZP2 = AVCL. Las rojas (OB) dan +5,8 pp en descubrimiento (Holm
  0,0001), pero +2,9 pp y p 0,097 en confirmación: **no confirma**.
- NO MEDIDO: un nulo apareado por la regla OB (el efecto rojo puede ser del "alejamiento limpio", no de la zona);
  confirmación con potencia; otros D/horizontes; P&L; toque n-ésimo; otras escalas e instrumentos; chart fusionado.
  Acta `AVZP2_REBOTE_RESULTADOS_20261007.md`.
- AVZP2 rojas contra un **nulo apareado OB** (08/10/2026): +2,5 pp, p 0,068, MDE 3,8 pp. **Más de la mitad del efecto
  era el alejamiento limpio**: sin efecto propio detectado. No se corre la confirmación.

## AVZP2-RACIMO (racimos de aVolZonePOI2, MNQ 25t, config de Nico) — 08/10/2026
- MEDIDO: contra pseudo-racimos apareados por ocupación previa, **compresión posterior confirmada**: −7 % de rango en
  200 velas después de la salida (desc. −0,077, Holm 0,0001; conf. −0,067, p 0,010). Sin dirección (O1), sin
  seguimiento de ruptura (O2: 14 % contra 19 %, n.s.) y sin rebote en el retest (O3b ≈ 46 %).
- NO MEDIDO: P&L de una lógica de rango; persistencia más allá de 200 velas; líneas en sesiones posteriores;
  sensibilidad a la configuración; otros instrumentos. Acta `AVZP2_RACIMO_RESULTADOS_20261008.md`.
- AVZP2-RACIMO-GRILLA (08/10/2026), 36 definiciones, 23 evaluables:
  - **Compresión: 23/23 en descubrimiento, 21/23 confirman** (−4 a −10 % de rango). Robusta a la definición.
  - **Salida a favor de la tendencia: real en ventanas largas** (1.000 velas, 30–45 ticks). +5 a +8 pp sobre una
    consolidación comparable, **controlando magnitud de tendencia y momentum**, y confirmada. Nula en 250–500/20–30
    (incluida la config de Nico).
  - Sin seguimiento ni rebote propios en ninguna celda.
  - NO MEDIDO: P&L; otros instrumentos; ventanas > 1.000.
  - Integridad: semilla `hash()` no determinista en scripts previos, corregida en la grilla.
  - Acta `AVZP2_RACIMO_GRILLA_RESULTADOS_20261008.md`.
