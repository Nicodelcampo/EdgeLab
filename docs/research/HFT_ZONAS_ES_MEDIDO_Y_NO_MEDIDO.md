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

## MEDIDO — y vivo

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
