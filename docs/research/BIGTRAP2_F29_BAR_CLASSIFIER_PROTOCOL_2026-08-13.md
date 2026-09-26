# F2.9 — BigTrap2 como clasificador de barra creadora (2026-08-13)

Estado: `PREREGISTERED_NOT_RUN`
Spec: `specs/bigtrap2_f29_bar_classifier_v0.json`
Hereda: F2.7 v2 + auditoría de F2.8. Mismas 201 sesiones. Mismos Parquet canónicos. Mismo `r_i`.

## 0. Por qué esta familia y no la cola

F2.8 mostró tres hechos que hay que leer juntos:

1. El Δ de F2.7 **no muere** lejos del ancla. En `d ≥ 6` incluso se agranda.
2. Un control de barra **sin** zona, con el mismo `(d, ancho, lado)`, produce casi el mismo Δ. En la cola el control ya vale `+0.064` contra `+0.077` de BigTrap2.
3. El contraste BT2 − control cruza cero. `OPEN_FAR_ZONE_FAMILY` **no enciende**: la spec exigía `ci95_lower > 0` en ese contraste.

La lectura honesta no es “las zonas lejanas son un imán más puro”. Es: **la barra que puede hospedar esa geometría ya trae la carrera**. BigTrap2 señala esa barra. El intervalo del kernel es, hasta nuevo aviso, una etiqueta de la barra, no un objeto que atrae al precio.

Eso no es un fracaso. Es el objeto nuevo. Un detector de barras se puede combinar con aVol. Un atlas de zonas-imán, no.

## 1. Pregunta

> ¿La barra que dispara BigTrap2 queda marcada, frente a barras de la misma sesión, por una carrera de primer pasaje de un intervalo canónico a distancia 2 y ancho 1, incluso cuando ese intervalo no es la zona del kernel? Si sí, ¿una regla barata de OHLC/volumen recupera esa marca, o hace falta el footprint, o todavía queda un residual de la zona?

## 2. Por qué el probe es canónico y no “la zona”

La zona del kernel no se puede poner en una barra que no creó zona. Si el único brazo es la zona real, F2.9 se reduce a F2.8.

El probe `P_mode` se puede computar en **cualquier** barra:

```text
d = 2, width = 1
lado = mecha superior ≥ mecha inferior → intervalo por encima del close
     = si no → intervalo por debajo del close
bull: [close+2, close+2]
bear: [close-2, close-2]
```

Esos números no se eligen mirando F2.9. La moda de `d` en F2.7/F2.8 es 2. El ancho mediano es 1. El filtro de mecha del kernel es 30% del rango. `range ≥ 3` es el mínimo para hospedar `d=2` y un tick de ancho.

Real y espejo del probe corren con el lifecycle reflejado de F2.7. `r_i` es el mismo. Los ceros **entran** al promedio por sesión. El contraste primario es **pareado por sesión**, no la suma de SE independientes.

## 3. Escalera. No hay producto cartesiano

### A — Retrato de la barra, sin carrera

Qué distingue a una creadora: rango, cuerpo, mechas, `close_loc`, volumen y su rango dentro de la sesión. Contraste HAC, peso igual por sesión. Sin pescar deciles después.

Si las creadoras no se distinguen ni en OHLC, el objeto no es “una barra rara”. Es ruido de footprint o un defecto de matching.

### B — Escalera del probe `P_mode`

| Peldaño | Quién entra | Qué pregunta |
|---|---|---|
| `K0` | barras que sí crearon zona | referencia BigTrap2 |
| `S0` | OHLC: `range≥3` y mecha dominante ≥30% | ¿basta la forma de la vela? |
| `S1` | `S0` y volumen ≥ mediana de la sesión | ¿hace falta tamaño? |
| `S2` | `S1` y close no en el 20% central | ¿hace falta close extremo? |
| `N0` | no-creadoras emparejadas por sesión, quintil de rango, close y volumen, más cercanas en tiempo | nulo de barra parecida |

Contrastes obligatorios: `K0 − N0` y `K0 − S1`, pareados.

`S0/S1/S2` **no** usan imbalance de footprint. Eso reescribiría el kernel y fingiría una regla simple.

### C — Residual de zona, barra fijada

Sólo en creadoras. Brazo 1: zona del kernel vs su espejo. Brazo 2: `P_mode` vs su espejo en **la misma** barra. Si C es compatible con cero, la geometría del kernel no agrega nada dado el sello de la barra. Si C es positivo, recién ahí existe un residual de zona que más tarde podría cruzarse con aVol.

### D — Persistencia

`P_mode` en `t−2, t−1, t+1, t+2` respecto de la creadora. Si `t+1` o `t+2` conservan la carrera, el producto es una ventana corta. Si sólo `t` la tiene, es un sello de una barra.

### E — Casi-kernel

`F0`: barras que emitirían `TRAP` aunque no lleguen a `min_trap_volume`. Un solo peldaño, no un barrido.

- `S1 ≪ F0 ≈ K0` → el objeto es footprint en la mecha, no OHLC.
- `F0 ≈ K0` → el piso de 30 de volumen es cosmética.
- `K0 > F0` → la geometría multi-fila del trap todavía suma.

Ese peldaño es el puente honesto hacia aVol: aVol habla el idioma del volumen local, no el de “zona mágica”.

## 4. Etiquetas. Pueden convivir

```text
OPEN_SIMPLE_BAR_RULE     S1 vive y K0 no le gana
OPEN_FOOTPRINT_OBJECT    F0 vive y OHLC no alcanza
OPEN_ZONE_RESIDUAL       C positivo: la zona aún suma dada la barra
OPEN_REGIME_WINDOW       t+1 o t+2 viven
OPEN_SINGLE_BAR_STAMP    sólo t vive
KEEP_BT2_AS_DETECTOR     K0 gana a S1 y a N0: conservar el kernel como selector
CLOSE_BAR_OBJECT         ningún peldaño vive
CONTINUE_AMBIGUOUS       interesante pero sin poder
```

Cualquier `OPEN_*` abre **una** spec. No Z2. No 17 frames. No cruce BigTrap2 × aVol salvo que `OPEN_ZONE_RESIDUAL` o `OPEN_FOOTPRINT_OBJECT` estén encendidos.

## 5. Qué se desbloquea, si algo se desbloquea

- Regla simple → aVol se puede condicionar a un sello OHLC barato.
- Objeto footprint → la combinación natural es imbalance-en-mecha × aVol, no zona × aVol.
- Residual de zona → recién ahí una interacción BigTrap2 × aVol es elegible.
- Ventana de régimen → producto de timing de 1–2 barras, todavía target-free.
- Conservar BT2 como detector → no reemplazar el kernel por `S1`.

## 6. Cerrado

Kernel, holdout, P&L, dirección, `tick:25`, barrido de parámetros, campaña de cola lejana, Kaggle conjunto, tirar los `r_i = 0`, y vender como primario un IC de SE independientes.

## 7. Sello de F2.8, aparte

F2.9 no re-ejecuta F2.8. Si se sella F2.8, es un prompt corto: incluir ceros, no mezclar empates con doble censura, contraste pareado, commitear un solo JSON formal. Sin reinterpretar labels.
