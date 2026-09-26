# H-ASIA-1 — ¿un desplazamiento fuerte «descarga» el último precio de Asia?

- **Registrada:** 2026-08-19 · **Estado:** `PROTOCOL_WRITTEN_NOT_RUN`
- **Familia nueva.** No hereda población, costos, oráculos ni presupuesto de
  multiplicidad de BigTrap2, H-Z2A, LUX-IMB ni YM-PRERANGE.
- **Origen:** observación de Nico, 2026-08-19 (textual abajo).
- **Antecedente obligatorio:** `docs/research/CENSO_RANGO_ASIA_2026-08-19.md`

---

## 1. La observación, textual

> «quiero medir si cuanto más rompió el precio en los 3 sentidos que especifiqué, el
> "camino" a través del último precio comerciado en la sesión asiática ofrece menos
> resistencia»

Los tres sentidos de «cuánto rompió», también textuales: **cuando rompió por x
tiempo**, **o hizo x volumen**, **o se alejó x ticks** del extremo de la sesión
asiática.

## 2. Traducción a objeto medible

- **El nivel:** `asia_close` = último precio comerciado dentro de la ventana de Asia
  (18:00–03:00 NY). Un número por sesión, en ticks enteros.
- **El disparador:** después de las 03:00, el precio rompe un extremo del rango
  asiático (medido: ocurre en el **99,5 %** de las sesiones de 6E y el **100 %** de
  YM — o sea, el disparador solo no filtra nada; lo que filtra es su **magnitud**).
- **La geometría implícita:** si rompe el **máximo**, `asia_close` queda **abajo**.
  «Atravesar `asia_close`» significa **volver** y cruzar el rango. La hipótesis dice
  que un desplazamiento fuerte **descarga** ese nivel: cuando el precio vuelve, pasa
  de largo en vez de frenarse.

### Las tres magnitudes de ruptura (predictores), medidas ANTES del retorno

| # | nombre | definición |
|---|---|---|
| **M1** | `tiempo_fuera` | minutos con el precio más allá del extremo, antes del primer retorno al rango |
| **M2** | `volumen_fuera` | volumen operado más allá del extremo, en ese mismo tramo |
| **M3** | `excursion_ticks` | máxima distancia en ticks más allá del extremo, en ese mismo tramo |

## 3. «Resistencia»: qué se mide y qué NO

Se define **costo de pasaje** por una banda `[asia_close ± k]` ticks, con `k` como
parámetro de grilla.

**Se mide (target-free, sin dirección):**

| medida | qué es |
|---|---|
| `dwell_minutos` | minutos con el precio dentro de la banda |
| `dwell_volumen` | volumen operado dentro de la banda |
| `n_reentradas` | veces que reentra a la banda antes de resolverse |
| `llega` | si el precio llega a la banda (booleano de alcance, no de resultado) |

Menos resistencia = **menos minutos, menos volumen, menos reentradas**.

**NO se mide acá — cruza el STOP:**

- si el precio **atraviesa o rebota** (eso es dirección: es la pregunta de reversión con
  otro nombre)
- MFE / MAE / retornos / P&L posteriores
- cualquier cosa que ocurra después de que la banda se resuelve

> El costo de estar en un nivel es microestructura. Lo que pasa después es resultado.
> La línea va exactamente ahí.

## 4. EL CONFUNDIDOR, escrito ANTES de medir

**Casi seguro el resultado crudo va a dar «menos resistencia», y casi seguro no va a
significar nada.**

Las tres magnitudes de ruptura están correlacionadas con **volatilidad**. Y la
volatilidad **reduce mecánicamente el dwell en CUALQUIER nivel**: si el precio se mueve
rápido, pasa poco tiempo en toda banda de `2k` ticks, tenga o no algo especial adentro.

Entonces «rompió fuerte → cruzó rápido `asia_close`» es la predicción de **un modelo sin
ninguna hipótesis**: rompió fuerte porque hay volatilidad, y con volatilidad todo se
cruza rápido.

**Esto no es una objeción menor: es la hipótesis nula que hay que vencer**, y sin
control la medición no puede distinguirla de la hipótesis de Nico.

## 5. Los controles, que son el diseño

Aprendido a la mala en F2.7–F2.9, donde el control **sin zona** con la misma geometría
dio casi lo mismo y el contraste cruzó cero. Cada sesión mide el mismo costo de pasaje
en tres niveles:

| nivel | qué controla |
|---|---|
| **`asia_close`** | el candidato |
| **espejo** | `asia_close` reflejado sobre el punto medio del rango — misma distancia al extremo roto, precio distinto |
| **placebo emparejado** | nivel a la misma distancia del extremo pero desplazado, sin significado |

**El estimando es el CONTRASTE** `asia_close − control`, no el valor absoluto. Si el
dwell baja igual en los tres, lo que se midió fue volatilidad.

## 6. Población: el espacio de eventos enumerado antes de congelar

Regla del proyecto: ninguna población se congela sin enumerar antes las alternativas.

| eje | opciones | elegida |
|---|---|---|
| lado roto | máximo · mínimo · el primero que ocurra · ambos por separado | **el primero**, con el lado registrado |
| cuál ruptura | primera · n-ésima · la de mayor excursión | **la primera** |
| el nivel | `asia_close` · punto medio · VWAP de Asia · el extremo mismo | **`asia_close`** (es lo que preguntó Nico) |
| llegada a la banda | primera · todas | **la primera** |
| si nunca llega | descartar · contar como censurada | **censurada y reportada** |

Las no elegidas **no se miden en esta campaña**. Medirlas después es otra campaña con
su propio presupuesto.

## 7. Potencia, antes de correr

`Δ ≈ 0,10 · √(403 / n_sesiones)` (P-53):

| instrumento | sesiones usables | MDE |
|---|---|---|
| 6E | 210 | 13,9 pp |
| YM | 226 | 13,4 pp |
| 6J | por medir | — |

Y **estratificar por magnitud de ruptura divide ese N**. Con terciles quedan ~70–75
sesiones por celda → **MDE ≈ 23 pp**. Es la restricción real (P-53), y hay que decirla
antes de ver el resultado, no después.

## 8. Cómo se refutaría

- El contraste `asia_close − control` **cruza cero** → el nivel no tiene nada especial;
  lo medido fue volatilidad.
- El dwell no varía monótonamente con M1/M2/M3 → «cuanto más rompió» no ordena nada.
- El efecto aparece sólo en un `k` → es ruido de grilla, no una propiedad del nivel.
- Las tres magnitudes están tan correlacionadas que no se distinguen → hay **una** sola
  variable (volatilidad) disfrazada de tres.

## 9. Lo que hace falta antes de correr la parte con dirección

Lo de §3 «se mide» **corre bajo target-free**. Lo de §3 «NO se mide» exige manifiesto de
campaña con `N_eff`, costos (**≈ 3,9 ticks RT** en 6E), MDE declarado, y el **OK
explícito de Nico**.
