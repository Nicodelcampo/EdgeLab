# H-ES-VOL-1 — ¿el volumen por tiempo dentro de la zona predice cuánto se aleja el precio?

- **Registrada 2026-08-20** · estado `PROTOCOL_WRITTEN`
- **Familia nueva.** No hereda población, costos ni presupuesto de H-Z2A, H-ASIA-1 ni
  HFTZonesRange.
- **Cruza el STOP**: el outcome es una excursión posterior. Este documento es la
  pre-registración que el STOP exige, escrita **antes** de medir.

---

## 1. La observación

> «si hay diferencia según la cantidad de volumen por tiempo que hizo el precio luego de
> crearla. Para x tiempo, x volumen comerciado dentro de la zona, que predice el retorno
> del precio a x distancia alejada.» — Nico

## 2. Las tres incógnitas, fijadas antes de medir

| | definición congelada |
|---|---|
| **predictor** | `tasa = vol_dentro / t_dentro`, con `vol_dentro` y `t_dentro` acumulados **sólo mientras el precio está en `[lower, upper]`**, desde el fin del barrido que crea la zona hasta la separación |
| **corte** | el predictor **termina** cuando el precio alcanza `R` ticks del borde. Ahí empieza el outcome. Sin solape: ni un tick se cuenta en los dos |
| **outcome** | excursión máxima desde el borde, **en ticks**, alcanzada después de la separación y dentro de la misma sesión |

`R ∈ {2, 5, 10}` — grilla declarada, no un número elegido.

## 3. Los dos canales (regla del proyecto)

- **no direccional**: `|excursión|` máxima, a cualquier lado
- **direccional**: excursión con signo, hacia dónde

La población tiene **92 % de zonas bajistas por el `isDown`-first**, así que **el canal
direccional no se interpreta** hasta regenerar el oráculo con `HFTZonesESPureV2Flat`. Se
mide y se guarda; no se lee.

## 4. El confundidor, escrito antes

**Volatilidad de sesión.** Una sesión activa tiene **a la vez** más volumen por unidad
de tiempo y excursiones más grandes. Una correlación positiva agregando todas las zonas
sería la predicción de un modelo **sin ninguna hipótesis**.

Por eso:

1. la relación se mide **dentro de cada sesión** (rango del predictor entre las zonas de
   esa misma sesión), nunca agregando todas las zonas de todas las sesiones;
2. se publica también la versión agregada, **para mostrar la diferencia** entre las dos
   lecturas;
3. se mide lo mismo en la **banda espejo** —misma altura, misma distancia al precio de
   creación, del otro lado—. Si el espejo muestra la misma relación, no es de la zona.

## 5. Unidad y potencia

La unidad es la **sesión**, no la zona. 120 sesiones → MDE heurístico **18,3 pp**
(`Δ ≈ 0,10·√(403/n)`, P-47). Es una heurística de proporciones trasladada, **no** la
potencia real de un test de tendencia: la potencia verdadera depende de la correlación
intra-sesión, que este mismo estudio estima.

**Esto es un piloto.** Sirve para estimar efecto, ICC y varianza, y con eso calcular el
N que haría falta para una prueba confirmatoria. No es la prueba confirmatoria.

## 6. Cómo se refutaría

- El coeficiente **dentro de sesión** cruza cero, aunque el agregado no → la relación era
  volatilidad de sesión.
- El **espejo** muestra la misma relación → no es de la zona, es de la geometría.
- La relación aparece sólo en un `R` → ruido de grilla.
- El predictor está tan correlacionado con el rango de la sesión que no se distinguen →
  hay una sola variable disfrazada de dos.

## 7. Costos

ES: 1 tick = 0,25 pts = 12,50 USD. La fricción round-trip realista está en el orden de
**1–1,5 ticks**. Cualquier excursión predicha por debajo de eso **no paga**, por más
significativa que sea la relación.

## 8. Lo que NO se hace acá

No se elige un umbral de `tasa` mirando el resultado. No se parte la población después
de ver el ruido (P-55: los contextos se escriben antes). No se toca el holdout.
