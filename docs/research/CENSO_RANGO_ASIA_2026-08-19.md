# Censo target-free del rango de Asia — 6E, 210 sesiones

- **Fecha:** 2026-08-19 · **Instrumento:** 6E · **Firewall:** holdout intacto
- **Artefacto:** `docs/research/censo_rango_asia_2026-08-19.json`
- **Runner:** `diag/tasa_senales/censo_rango_asia.py`
- **Origen:** pregunta de Nico — *«el precio suele revertir al tomar un lado de Asia»*

> **Esto NO contesta la pregunta de reversión.** Medir reversión es medir un resultado
> direccional y cae bajo el STOP. Lo que hay acá es **capa 1**: población y geometría.

## La ventana

18:00 → 17:00 hora de Nueva York, la sesión CME completa del trade date, partida por
índice de minuto: **Asia = 18:00–03:00** (apertura CME → apertura Londres), **posterior
= 03:00–17:00**. Una sola llamada a `minute_window_matrices`, para que Asia y su
posterior sean la misma fila.

**Reloj declarado:** Nueva York, anclado a la sesión CME y al firewall. Consecuencia:
respecto de Tokio la ventana se corre **una hora en cada cambio de DST**. La
alternativa —fijar en `Asia/Tokyo`— mantiene fija la sesión japonesa y mueve el borde
respecto de la CME.

`calendar_complete = False` (no existe calendario de research): **diagnóstico, no
denominador formal**.

## Resultados

**210 días usables de 229** (19 descartados por menos de 120 barras M1 en Asia).

| medida | valor | IC 95 % |
|---|---|---|
| **rompe algún extremo** | **209 / 210 = 99,5 %** | [98,6 – 100] |
| toca **ambos** extremos | 78 / 210 = 37,1 % | [30,6 – 43,7] |
| el **bajo** primero | 117 / 209 = 56,0 % | [49,3 – 62,7] |

Rango de Asia, en ticks: p25 **42** · mediana **55** · p75 **80** · máx **267**.

Minutos hasta la primera ruptura (desde las 03:00 NY): p25 **9** · mediana **47** ·
p75 **143**.

## Lectura

### 1. Romper un extremo de Asia no es un evento: es el estado por defecto

**99,5 %.** Un solo día de 210 no rompió ningún lado. Y es rápido: en el **primer
cuarto de hora** ya rompió el 25 % de las sesiones; la mediana son 47 minutos.

Condicionar en «rompió un extremo de Asia» es condicionar en **casi todo**. La
información que aporta ese filtro es prácticamente cero, y cualquier tasa condicional
que se mida sobre él va a ser la tasa incondicional disfrazada.

Tiene sentido geométrico: la mediana del rango es **55 ticks** y la ventana posterior
son **14 horas** que incluyen la sesión americana entera. Un rango nocturno chico
contra una sesión completa se rompe casi siempre.

**Es la misma familia de resultado que ya mató a BigTrap2 como soporte/resistencia
(~96 % de ruptura).** Un nivel que se rompe casi siempre no es un nivel.

### 2. «Ambos extremos» no sostiene la reversión — y tampoco la refuta

**37,1 %** de las sesiones tocan los dos lados. Es **menos de la mitad**.

Pero esta cifra **no se puede leer sola**, en ninguna dirección. El nulo de un paseo
aleatorio que acaba de tocar un borde **no es 50 %**: es alto por reflexión.
`H-SWEEP-1` midió esa trampa en otra ventana y dejó escrito **54–76 %**. Ese número
**no se transporta** —otra ventana, otro instrumento, otro estimand— pero la lección
sí: sin el nulo construido para *esta* geometría, 37 % no dice nada.

Lo que sí se puede decir: **si la reversión fuera fuerte, el número debería estar por
encima del nulo, no por debajo de la moneda.** No es aliento.

### 3. El «bajo primero» no es significativo

56,0 %, IC 95 % **[49,3 – 62,7]**, cruza el 50 %. Sobre 6E en un período con
tendencia, es exactamente lo que se espera de la deriva del propio instrumento. **No
es un hallazgo.**

## Consecuencia para la hipótesis

La versión literal —«el precio revierte al tomar un lado de Asia»— **no tiene
población que la haga medible**: el condicionante ocurre el 99,5 % de las veces.

Para que sea testeable hay que agregar condiciones que **reduzcan la población**, y
esas condiciones hay que **escribirlas antes de mirar** (regla de población). Candidatas
naturales, ninguna elegida acá:

- **tamaño del rango** — sólo rangos angostos, o sólo anchos (p25 = 42 vs p75 = 80
  ticks es un factor 2)
- **momento de la ruptura** — la mediana son 47 min; el p25 son 9. Romper a los 5
  minutos y romper a las 3 horas no son el mismo evento
- **magnitud de la penetración** — romper por 1 tick y romper por 20 no son lo mismo
- **qué había detrás** — la idea de Nico sobre el precio previo entra acá
- **primera ruptura vs segunda**

**El MDE con 210 sesiones es 13,9 pp** (`Δ ≈ 0,10·√(403/n)`). Cualquier subpoblación
tiene **menos** sesiones y **peor** MDE. Ésa es la restricción real, y es P-53.

## Lo que haría falta para medir la reversión

Manifiesto de campaña con: población condicionada y **pre-registrada** · estimand con
**etiqueta de barrera** (`+X` / `−Y` con horizonte, no «se movió X ticks») · el **nulo
de reflexión construido para esta geometría** · costos (**≈ 3,9 ticks RT** en 6E) ·
`N_eff` y su presupuesto · MDE declarado. Y el **OK explícito de Nico**.

**Ninguna de esas piezas se puede sacar de este censo**, y ése es justamente el punto
de haberlo corrido primero.
