# Corrección — el MDE de 1,14 **sí reproduce**. El que estaba mal era mi script

**Fecha:** 2026-08-07 · **Corrige:** una afirmación mía, publicada el 2026-08-06
**Reproducible:** `.venv\Scripts\python diag\multiplicidad\reconstruir_mde.py`
(exit **0**; antes salía 1)

## Qué afirmé, y era falso

Publiqué que el **MDE de 1,14 ticks a `f=1`** —el número que sostiene toda la
discusión de factibilidad de EXPLORE-001— **no era reproducible** desde los
insumos documentados: que el cálculo daba **2,41**, un factor **2,11** sin
explicar, y listé tres hipótesis sin elegir ninguna.

Y le puse consecuencias fuertes: que si el MDE real fuera 2,41, a `f=1` no
habría nada detectable que además fuera operable, y el barrido de resolución no
entraría.

**El número publicado está bien. Los cuatro renglones reproducen:**

| f | N_eff | deflación | calculado | publicado | dif |
|---:|---:|---:|---:|---:|---:|
| 1 | 197 | 7,020 | 1,1447 | **1,14** | +0,0047 |
| 3 | 574 | 4,112 | 0,6706 | **0,67** | +0,0006 |
| 10 | 1.733 | 2,367 | 0,3859 | **0,39** | −0,0041 |
| 30 | 4.102 | 1,538 | 0,2508 | **0,25** | +0,0008 |

Diferencia máxima **0,0047 ticks**, dentro del redondeo con que están escritos.

## Qué hice mal

Calculé el error estándar como `SD / sqrt(N_eff)` con `SD = 8,77 ticks/trade`
—la mediana de las 40 geometrías—. El MDE no usa esa `SD`: usa un **`SE` medido
por bootstrap**, que el expediente publica explícitamente.

```
SD/sqrt(N_eff) = 8,77 / sqrt(9.707) = 0,0890 t/ancla   <- lo que usé
SE medida por bootstrap             = 0,0420 t/ancla   <- lo correcto
                          cociente  = 2,12
```

**Ese cociente es exactamente el «factor 2,11 inexplicado» que reporté.** No era
un misterio: era mi insumo.

No son la misma cantidad. `SD = 8,77` es dispersión **por trade** entre
geometrías; `SE = 0,0420` es el error estándar **por ancla** del estimando, con
la dependencia entre días ya adentro. Dividir la primera por `sqrt(n)` supone
independencia y supone que el estimando es la media de esa variable — ninguna de
las dos cosas vale acá.

Mi propia hipótesis nº 1 decía «`SD` no es 8,77 en las unidades del estimando».
Era la correcta. **No elegirla fue lo apropiado en ese momento** —no tenía
evidencia, y elegir la que cuadra es fabricar acuerdo—. El error no fue no
elegir: fue **no buscar la evidencia donde estaba**.

## Y ahí está la parte que importa

Escribí, y lo verifiqué con `grep`: «**ningún script del repo lo calcula**»,
buscando `norm.ppf`, `z_beta`, `potencia` y `0.8416` sobre todo `diag/`.

Era **cierto y completamente irrelevante**. La derivación no está en un script:
está en **`docs/spike_in/MDE_EXPLORE-001.md`**, un documento de 25 KB **cuyo
nombre es exactamente el número que yo estaba intentando reconstruir**.

Nunca busqué en `docs/`. Busqué donde esperaba que estuviera la respuesta, no la
encontré, y **publiqué la ausencia como hallazgo**. Es el mismo modo de falla que
este expediente persigue en todos lados —una afirmación cuya derivación nadie
puede reconstruir— con la carga invertida: acá la derivación existía y el que no
la reconstruyó fui yo.

Apareció recién cuando `tools/reportes.py` listó los 103 documentos de `docs/`
agrupados por carpeta. **No lo encontré razonando: lo encontré porque un índice
lo puso adelante.**

## Qué sigue abierto — esto no lo cierra todo

- **`N_eff(f)` está tabulado, no reconstruido.** Los valores 197 / 574 / 1.733 /
  4.102 salen de un bootstrap de bloques de día que `reconstruir_mde.py` **no
  vuelve a correr**. Que el MDE reproduzca dado ese insumo **no valida el
  insumo**.
- **El `197` de `f=1` son los días de research de entonces.** El universo hoy
  tiene **201 sesiones**. El MDE a `f=1` se mueve por `sqrt(197/201) = 0,990`:
  **−1,0 %**, o sea `1,133` en vez de `1,14`. Es despreciable para la decisión,
  pero el número publicado es de un universo que ya no es el vigente.

## Documentos que todavía llevan la afirmación vieja

No los edito —son registros fechados y reescribirlos sería borrar el error en
vez de corregirlo—, pero quedan listados para que se puedan encontrar:

| documento | línea |
|---|---|
| `docs/ESTADO_2026-08-06.md` | 39 y 52 |
| `docs/amendments/EXPLORE-001-2026-08-06_espacio_reglas_entrada.md` | 197 |
| `docs/research/ACTUALIZACION_PARA_AUDITOR_2026-08-06.md` | 167 |

En los tres, el ítem «resolver el MDE 1,14 no reproducible» figura como
**pendiente abierto**. **Queda cerrado por este documento**, con la salvedad de
`N_eff` de arriba.

## Aporte al referente

Devuelve al referente un insumo que yo había puesto en duda sin motivo: el MDE
es el que decide si una hipótesis es **detectable**, y con `2,41` la banda
«detectable y operable» a 1 trade/día quedaba vacía. Con `1,14` confirmado, el
margen contra la fricción de 2,704 ticks es **2,4×** y el régimen de baja
frecuencia vuelve a estar sobre la mesa.
