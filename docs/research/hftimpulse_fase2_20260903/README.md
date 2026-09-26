# FASE 2 — resultado. Carrera 1:1 con retroceso de entrada

Fecha: 2026-09-03 · Pre-registro sellado **antes** de correr: `PREREGISTRO.md`.
Población: `hftimpulse_NQ0626_20260903.csv` sha256 `856d235f…702b`, 6.043 señales,
29 sesiones, NQ 06-26 5t, pre-holdout. Holdout intacto.

## Veredicto: NO PROMOVIBLE

> **0 de 70 celdas** tienen el IC inferior por encima de cero.
> **0 de 70 celdas** son siquiera positivas netas de costos.
> La mejor celda neta pierde **1,38 ticks por trade**.

## Landscape completo — expectativa BRUTA por trade (ticks), política pesimista

| R \ SL=TP | 4 | 6 | 8 | 12 | 16 | 20 | 24 | 32 | 40 | 48 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **0** | +0,08 | +0,05 | −0,04 | −0,05 | −0,03 | −0,05 | **+0,12** | −0,11 | −0,19 | −0,38 |
| 2 | −0,61 | −0,76 | −0,94 | −0,79 | −0,81 | −0,77 | −0,86 | −0,86 | −0,85 | −1,18 |
| 4 | −0,43 | −0,64 | −0,62 | −0,50 | −0,32 | −0,35 | −0,54 | −0,79 | −0,85 | −1,16 |
| 6 | −0,52 | −0,55 | −0,58 | −0,45 | −0,20 | −0,13 | −0,41 | −0,97 | −0,68 | −1,35 |
| 8 | −0,57 | −0,52 | −0,54 | −0,39 | −0,18 | −0,14 | −0,25 | −0,78 | −0,77 | −1,02 |
| 12 | −0,51 | −0,48 | −0,48 | −0,40 | −0,30 | −0,32 | −0,14 | −0,37 | −0,70 | −0,78 |
| 16 | −0,65 | −0,55 | −0,54 | −0,63 | −0,33 | −0,12 | −0,23 | −0,36 | −1,02 | −1,05 |

Netas de 1,5 ticks de costo, **las 70 quedan entre −1,38 y −2,85**.

## Los tres números que cierran la pregunta

1. **Sin retroceso el bruto es cero.** La fila `R=0` oscila entre −0,38 y +0,12
   ticks. La tasa de acierto de la mejor celda es **50,24 %**, y su IC bootstrap
   clusterizado del bruto es **[−0,41, +0,61]**: incluye cero. Es una moneda.
2. **El mejor caso imaginable no paga el peaje.** Con la política optimista —que
   regala todas las ambigüedades— el mejor bruto de las 70 celdas es **+0,216
   ticks**. El costo round-turn de NQ es ~1,5 ticks. **El edge tendría que ser
   siete veces mayor sólo para empatar.**
3. **La tasa de acierto media de las 70 celdas es 47,95 %**, por debajo de una
   moneda.

## El hallazgo que sí sirve: el retroceso destruye valor

Esperar un retroceso empeora el resultado **en los 60 casos**, sin excepción. La
fila `R=0` promedia −0,06 ticks brutos; `R=2` promedia −0,84.

La lectura mecánica es directa: **las señales que retroceden son las que fallan**.
Filtrar por retroceso selecciona sistemáticamente las peores. El eje que se iba a
barrer con siete valores queda no sólo descartado sino **invertido respecto de la
intuición** que lo motivaba.

Tasa de llenado, por si se quisiera reconsiderar: R=2 → 92,8 %, R=8 → 78,5 %,
R=16 → 59,6 %. No es que falten trades; es que los que hay son peores.

## Coherencia con la Fase 1

La Fase 1 midió que las excursiones máximas son simétricas, con el canal
direccional levemente negativo (−0,035 desvíos). Dejó abierto que el **orden**
pudiera favorecer a la señal aunque las magnitudes empataran.

**No lo hace.** Con SL = TP la carrera es 50/50 y el bruto es cero. Las dos fases
miden cosas distintas y dan lo mismo, que es la forma en que un resultado negativo
se vuelve creíble.

## MDE, porque un nulo sin MDE no dice nada

Celda de mejor bruto: n = 6.043 fills, IC clusterizado de semiancho 0,51 ticks =
**0,021 desvíos**. Con 70 celdas y corrección por multiplicidad el umbral sube,
pero es irrelevante acá: **no hay ninguna celda positiva que corregir**.

La medición tenía potencia de sobra para detectar el 0,02–0,10 que rinde un
sistema real. No encontró nada porque no hay nada, no por falta de precisión.

## Criterio de decisión, aplicado tal como se fijó

El pre-registro exigía una **región contigua** con IC inferior > 0 neto. No hay
ninguna celda que cumpla, así que no hay región. **NO PROMOVIBLE**, sin
interpretación posible en otro sentido.

## Alcance preciso de esta muerte

Queda refutado: **la señal de racha de `HFTImpulseZones_P`, con entrada a mercado
o por retroceso y salida simétrica SL = TP, sobre NQ 06-26 en 5 ticks/barra, con
los parámetros por defecto del indicador**, no tiene expectativa positiva neta.

**No** queda refutado, y no se ensancha la muerte sin evidencia propia:

- otros parámetros del indicador (ventana, umbrales de impulso, definición de
  racha) — no se barrieron;
- otras resoluciones de barra;
- otros instrumentos — la fricción de NQ no se transporta;
- salidas asimétricas, break-even, o filtros por EMA y horario;
- la hipótesis inversa (agotamiento en vez de continuación), que además no se
  puede probar sobre estos mismos datos sin presupuesto propio.

## Aporte al referente

Un candidato quedó descartado con evidencia propia, pre-registro sellado antes de
correr y el landscape completo publicado — sin que ninguna celda sobreviviera por
azar, porque no se buscó la ganadora. Y deja un dato reutilizable: **filtrar por
retroceso selecciona las señales que fallan**, lo que aplica a cualquier familia
futura que quiera usar ese eje.
