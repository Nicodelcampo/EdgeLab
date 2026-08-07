# Especificación del test primario de EXPLORE-001

> ## SUPERSEDED — no usar aisladamente para ejecutar EXPLORE-001
>
> Para trabajo futuro este documento queda reemplazado por:
> **`docs/predictions/ESPEC_TEST_EXPLORE-001_v0.3.md`** (2026-08-07).
>
> **Se conserva como registro histórico.** Su contenido NO se reescribe: las
> decisiones que tomó, y las que después cambiaron, son parte del expediente.
> Toda decisión futura de EXPLORE-001 parte de v0.3; ningún borrador anterior
> —este incluido— puede invocarse para reemplazar una regla de v0.3.
>
> Motivo del reemplazo: editar cualquiera de las dos especificaciones
> existentes habría mezclado **registro histórico con reglas actuales**.
> Ver v0.3 §0.


**Escrita 2026-07-28, ANTES de calibrar y ANTES de elegir geometría.**
Estado: **BORRADOR** — no sellado, no ejecutado.

Este documento define **el procedimiento completo que decide**, no un
estadístico suelto. La distinción importa: lo que hay que calibrar es la tasa de
error del test entero, no la cobertura de un intervalo para una media.

---

## 0 · Correcciones de lenguaje (vigentes desde hoy)

Cinco formas de hablar que se usaron en reportes anteriores y que inducen error:

1. **AR(1) φ=0,8 es un escenario sintético de estrés, no un modelo demostrado
   de la serie real.** Que `b_opt` dé 13–18 evidencia dependencia relevante; no
   establece equivalencia con ningún AR concreto.
2. **`N_ef = N/b_opt` es una heurística comparativa**, no una cantidad de
   observaciones independientes ni un cálculo de potencia. La potencia se mide
   con el arnés sintético end-to-end (§ Tarea 2.5), no se deduce de N_ef.
3. **Las anclas cuyo horizonte cruza el mantenimiento son `HORIZONTE_NO_CONTINUO`,
   no "contaminadas".** *Contaminación* queda reservada para el holdout.
4. **El método vigente es `PPW 2009`.** No existe "PW2004 vs PPW2009" en el repo:
   hay una sola fórmula y ya es la corregida (`D_SB = 2·ĝ(0)²`, verificado línea
   por línea). La comparación real es **bloque fijo vs PPW 2009**.
5. **No existe "el lift de break-even".** Existe el lift **bajo un escenario de
   redistribución declarado**. Reportar un solo número sin decir de dónde sale la
   masa de probabilidad es reportar el caso favorable sin decirlo.

---

## 1 · El test primario, de punta a punta

### 1.1 Población de eventos

```
ZONAS ADMISIBLES:
  zona z entra si:
    z.creada_en_dia ∈ universo_del_estudio        (§1.2)
    z tiene al menos un evento ZONE_TOUCHED con touches == 1
    el primer toque NO ocurre en la barra que creó la zona   (anti look-ahead)

EVENTO:
  un (1) evento por zona = su PRIMER TOQUE.
  Los toques posteriores NO cuentan para el criterio primario.
  Motivo: una zona muy tocada pesaría como muchas zonas -> pseudo-replicación.
```

### 1.2 Universo

```
dias = cargar_dias_de_estudio(manifiesto,
                              tipos_de_dia = ["COMPLETO", "CIERRE_SEMANAL"],
                              incluir_holdout = False)      # puerta única
```

`APERTURA_SEMANAL` (domingos) queda **fuera**, y el nulo usa exactamente los
mismos tipos. Declarado en `CLAUSULAS_INFERENCIA_EXPLORE-001.md` §3.

### 1.3 Unidad de análisis y PESO DEL ESTIMADOR

**Ésta es la decisión que más cambia el estadístico y por eso se declara antes
de medir nada.**

```
UNIDAD: el DÍA.
PESO:   equal-weight POR DÍA, no por evento.

  p_dia(d)   = (# eventos del día d con resultado OBJETIVO) / (# eventos del día d)
  p_global   = mean_d p_dia(d)        sobre los días CON al menos un evento
```

**Por qué equal-weight por día y no por evento.** El *pooling* por evento
(`Σ aciertos / Σ eventos`) le da a un día con 20 zonas veinte veces el peso de un
día con 1. Los eventos del mismo día comparten régimen —volatilidad, tendencia,
noticias— así que ese peso extra **no es información extra**: es la misma
observación contada veinte veces. El pooling también hace que el estadístico
dependa de cuántas zonas produce el indicador cada día, que es una propiedad del
feature y no del efecto que se quiere medir.

**Consecuencia declarada**: días con pocas zonas pesan igual que días con muchas.
Es deliberado. Un efecto que sólo exista en días de muchas zonas **no** será
detectado por el primario; eso sería una hipótesis distinta, con su propio turno.

**Días con CERO zonas**: quedan **fuera del estadístico** (no aportan `p_dia`)
pero **entran al conteo del universo** y se reportan. No se imputan.

### 1.4 Resultado por evento

```
resultado(evento) =
    barrido SECUENCIAL en ticks enteros desde t0 hasta t0 + H:
      si dirección·(px_i − px_0) >=  target_ticks  -> OBJETIVO, valor = +target
      si dirección·(px_i − px_0) <= -stop_ticks    -> STOP,     valor = -stop
    si no se tocó ninguna barrera al llegar a t0+H:
      -> TIMEOUT, valor = dirección·(px_fin − px_0)      # A MERCADO, nunca 0

dirección: trapped_buyers -> -1 ; trapped_sellers -> +1     (§Tarea 5.2)
```

El barrido es secuencial porque importa **cuál se toca primero**, y eso no se
deduce del máximo y el mínimo por separado.

### 1.5 Línea base nula y emparejamiento de estratos

```
NULO: anclas placebo del atlas, MISMOS días, MISMOS tipos de día,
      MISMA geometría (target, stop, H), MISMA política temporal.

EMPAREJAMIENTO: por los 12 estratos (4 franjas horarias × 3 terciles de
      volatilidad rezagada), calculados con la MISMA definición en ambos lados.
```

### 1.6 MCPT — qué se permuta

```
PERMUTACIÓN ESTRATIFICADA POR DÍA:
  para cada día d:
     k_d = # eventos reales de ese día
     se reasignan al azar k_d de los instantes CANDIDATOS del día d
     (los candidatos son las anclas placebo del atlas de ese mismo día)
  se recalcula p_global con el MISMO peso equal-weight por día
  p_valor = (# permutaciones con estadístico >= observado + 1) / (reps + 1)

  reps = 10.000 · seed declarada
```

Cada permutación **preserva la identidad del día y su tasa base**, así que la
dependencia entre días es idéntica en todas y no puede inflar la significancia.
Permutar bloques de días dejaría ~12 unidades y un p-valor mínimo de 0,083.

**Nota sobre el pool nulo vs. los controles sorteados.** El atlas genera por día
un pool de anclas placebo (`n_pool_null(d) ≈ 120`). La MCPT no usa el pool completo
como muestra: para cada día sortea `k_d = n_eventos(d)` anclas de ese pool y las
trata como la realización nula del día. Por lo tanto:

  - `n_pool_null(d)` ≈ 120 son las anclas placebo disponibles; **nunca entra
    directamente al estimador diario**;
  - `k_d = n_eventos(d)` es la cantidad de eventos reales del día;
  - `n_null_selected(d) = k_d` en cada realización MCPT.

En la **muestra real**, `n_eventos(d)` es la cantidad de eventos reales del día.
En una **realización MCPT**, `n_eventos(d) = k_d = n_null_selected(d)` es la
cantidad de controles sorteados ese día. El estimador diario usa la **misma
interfaz** en ambas muestras y no necesita conocer su procedencia.

`sum_objetivo(d)` es un **conteo entero** de eventos cuyo outcome fue OBJETIVO.
No se admiten outcomes ponderados, probabilidades ni fracciones: el Diseño B
estima una proporción de outcomes binarios.

La construcción de la MCPT impone **simetría de conteos**: `k_d` debe ser igual
a `n_eventos_real(d)`. Esa igualdad es una restricción del diseño, no una
propiedad accidental de los datos. Si un día no tiene controles válidos
suficientes para satisfacerla, la realización **falla explícitamente**; no se
reduce `k_d` en silencio.

El estimador diario (`edgelab.stats.estimando_diario`) recibe una **única**
muestra de eventos por ejecución —la observada real o una realización concreta
de la MCPT— con conteos `n_eventos(d)` y `sum_objetivo(d)`. Nunca recibe el pool
completo junto con los eventos reales; la construcción de la distribución nula
vive fuera de ese módulo.

Las fechas `d` son **fechas de sesión en `America/Chicago`**. El universo se
arma a partir de `cargar_dias_de_estudio`, que es la puerta única para decidir
qué días son elegibles (mantenimiento, feriados, domingos, etc.).

**Costo declarado**: no detecta efectos puramente *entre* días. La hipótesis es
que el toque marca un **momento**, no un día.

### 1.7 Bootstrap — qué estima y para qué

```
El bootstrap NO produce el p-valor. Produce el INTERVALO del tamaño de efecto.
  bootstrap estacionario (Politis–Romano) con b por PPW 2009,
  estimado en tiempo de corrida sobre los estadísticos PLACEBO diarios
  de la geometría elegida — nunca sobre resultados de zonas reales.
```

Son dos preguntas distintas: la permutación contesta *"¿es distinguible del
azar?"*; el bootstrap contesta *"¿de qué tamaño es y con qué precisión?"*.

### 1.8 Los 12 estratos — DESCRIPTIVOS

> **Regla dura, escrita textual para el pre-registro:**
> **Ningún estrato puede rescatar un global negativo.** Los 12 estratos son
> **descriptivos**: se reportan, no deciden. Si el criterio global no se cumple,
> el veredicto es MUERTA con independencia de lo que muestre cualquier estrato.
> Un estrato llamativo con el global negativo genera, como mucho, una hipótesis
> NUEVA que gasta su propio turno en la cola.

Como los estratos **no deciden**, no entran al control de familia. Si en algún
momento se quisiera que decidan, ese cambio **exige control de FWER** y una
enmienda explícita del pre-registro.

### 1.9 Reglas de éxito y de muerte

```
ÉXITO (confirmatorio, global, único):
  p_valor_MCPT <= 0,05    Y
  p_global observado por encima del percentil 95 del nulo

MUERTE:
  p_global dentro del intervalo del nulo en el GLOBAL
  -> MUERTA, sin apelación, sin importar los estratos

Re-tunear geometría, dirección o política después de ver resultados NO es
rescate: es una hipótesis nueva que gasta su propio turno.
```

### 1.10 Confirmatorio vs exploratorio

| parte | naturaleza |
|---|---|
| `p_global` vs nulo + MCPT | **CONFIRMATORIA** — decide |
| IC del tamaño de efecto (bootstrap) | confirmatoria de magnitud |
| Evaluación económica neta | **secundaria declarada** — no decide detección |
| Los 12 estratos | **descriptivos** — no deciden |
| Dosis-respuesta (toques previos) | exploratorio |
| Muerte de zona (decaimiento) | exploratorio |

---

## 2 · Criterios de adopción del método inferencial

**Congelados antes de correr la calibración.** Copiados del pedido de Nico del
2026-07-28 y no negociables después de ver resultados:

- falso positivo global del **test completo** ≤ 5 % en todos los escenarios;
- límite superior del IC95 binomial de esa tasa ≤ 7 %;
- FWER ≤ 5 % **si algún estrato decide** (hoy no deciden);
- cobertura IC95 en [0,93 ; 0,97] bajo IID;
- cobertura IC95 ≥ 0,90 bajo dependencia fuerte;
- el criterio de muerte no falla en matar ruido más del 5 % de las veces;
- reproducibilidad exacta con la misma semilla.

**Si ningún método pasa, EXPLORE-001 queda BLOQUEADO.** Prohibido inventar un
percentil ad hoc, inflar por un factor observado, o usar `2·b_opt` sin que eso
mismo haya pasado la batería como método predeclarado.

---

## 3 · Grados de libertad — estado

| parámetro | estado | resuelto por |
|---|---|---|
| `tick_bar_size` | **RETIRADO** | regla de paridad certificada (§Tarea 5.1) |
| `merge_gap_ticks` | **NO APLICA** | pertenece a `aVolCellPOI2`, no a BigTrap2 |
| `direccion_por_side` | **DERIVADO** | semántica de `BigTrap2.cs:30-31` |
| peso del estimador | **DECLARADO** | equal-weight por día (§1.3) |
| rol de los estratos | **DECLARADO** | descriptivos (§1.8) |
| política temporal | **PENDIENTE — decisión de Nico** | Tarea 3 |
| método inferencial | **BLOQUEADO** | no hay método calibrado |
| `target_ticks`, `stop_ticks`, `horizon_minutes` | **PENDIENTE** | tras calibrar |
