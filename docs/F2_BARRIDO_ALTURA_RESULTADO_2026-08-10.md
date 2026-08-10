# F2 — barrido target-free de altura de zona · RESULTADO

**Fecha** 2026-08-10 · **Artefacto** `diag/tasa_senales/barrido_F2_altura.json`
**Grilla** `diag/tasa_senales/grilla_F2_altura.json` — 12 celdas
**Outcomes** `false` · **Multiplicidad gastada** cero (target-free)
**NORTH_STAR** sha256 `21bb3b01a33e2b37…`

---

## 1. Lo que se barrió

```
ticks_per_row     1, 2, 4        <- la altura de zona
imbalance_ratio   2.0, 3.0       <- cuantas filas califican
min_trap_volume   30, 50         <- selectividad por volumen
```

12 celdas × 4 contratos × 201 sesiones. Todo con `bar_spec = time:1`, que **no se
varió** — ver `REGISTRO_NO_MEDIDO_2026-08-10.md` §2.1.

---

## 2. El paisaje

| celda | zonas | /sesión | **% rota** | alt med | alt p90 | vida med | toques med |
|---|---|---|---|---|---|---|---|
| tpr1_ir2.0_mtv30 | 24.198 | 120,4 | 96,2 % | 1,00 | 2,00 | 6,9 | 2,00 |
| tpr1_ir2.0_mtv50 | 13.527 | 67,3 | 96,0 % | 1,00 | 2,00 | 7,0 | 2,00 |
| tpr1_ir3.0_mtv30 | 15.947 | 79,3 | 96,1 % | 1,00 | 2,00 | 7,3 | 2,00 |
| tpr1_ir3.0_mtv50 | 9.007 | 44,8 | 95,8 % | 1,00 | 2,00 | 7,3 | 2,00 |
| tpr2_ir2.0_mtv30 | 38.254 | 190,3 | 96,7 % | 2,00 | 2,00 | 6,7 | 3,00 |
| tpr2_ir2.0_mtv50 | 22.980 | 114,3 | 96,6 % | 2,00 | 2,00 | 6,4 | 3,00 |
| tpr2_ir3.0_mtv30 | 27.252 | 135,6 | 96,9 % | 2,00 | 2,00 | 6,1 | 3,00 |
| tpr2_ir3.0_mtv50 | 16.247 | 80,8 | 96,8 % | 2,00 | 2,00 | 6,1 | 3,00 |
| tpr4_ir2.0_mtv30 | 54.490 | 271,1 | 95,8 % | 4,00 | 4,00 | 11,4 | 6,07 |
| tpr4_ir2.0_mtv50 | 33.162 | 165,0 | 95,8 % | 4,00 | 4,00 | 10,8 | 5,70 |
| tpr4_ir3.0_mtv30 | 45.253 | 225,1 | 95,9 % | 4,00 | 4,00 | 11,1 | 6,07 |
| tpr4_ir3.0_mtv50 | 27.066 | 134,7 | 96,0 % | 4,00 | 4,00 | 10,8 | 5,71 |

---

## 3. Mi hipótesis mecánica está REFUTADA

Declarada en `PLAN_ANALISIS_v2` §F1.2, **antes** de correr esto:

> *«Hipótesis mecánica pre-declarada: **la altura domina**, porque close-through
> exige cerrar más allá del borde lejano — una zona más alta es más difícil de
> romper **por construcción, no por correlación**.»*

**Medido: cuadruplicar la altura no mueve la tasa de ruptura.**

```
altura 1 tick   ->  96,0 % rota
altura 2 ticks  ->  96,8 % rota
altura 4 ticks  ->  95,9 % rota
```

En **toda** la grilla la tasa vive en **95,8 % – 96,9 %** — un rango de **1,1
puntos porcentuales** mientras el conteo de zonas varía **6×** (9.007 → 54.490).
La hipótesis era falsable y se falsó. No se rescata ni se reformula.

### Por qué falló, que es más útil que el hecho de que falló

La altura **sí** compra algo, pero no inmunidad:

```
tpr 1 -> 4     vida mediana   7  ->  11 barras   (1,6x)
               toques mediana 2  ->   6          (3,0x)
               tasa de ruptura   96,1% -> 95,9%  (sin cambio)
```

**La altura compra tiempo, no supervivencia.** Una zona más alta aguanta más
toques y vive más, y termina rota igual. El close-through no es un evento que la
geometría pueda evitar: es el estado terminal del objeto.

---

## 4. El hallazgo: el 96 % es una propiedad del objeto, no un parámetro

```
rota (close_through + gap)   95,8 % – 96,9 %     en las 12 celdas
expirada por max_age          2,9 % –  4,0 %
```

**No existe, en esta grilla, una celda donde las zonas aguanten.** La invariancia
es el resultado, y es más informativa que cualquier óptimo que hubiera aparecido:

> Toda estrategia que dependa de que la zona **aguante** pelea contra una tasa
> base del 96 % que **los parámetros del indicador no mueven.**

Eso cierra por adelantado una familia entera de hipótesis —«encontrar la
configuración donde el nivel resiste»— sin gastar un solo outcome ni un solo
grado de libertad de multiplicidad.

### Y `imbalance_ratio` / `min_trap_volume` no son perillas de comportamiento

Mueven el **conteo** (9.007 → 54.490, 6×) y **nada más**: altura idéntica, vida
casi idéntica, tasa de ruptura idéntica. Son filtros de selectividad, no de
naturaleza. Quien busque comportamiento en esos ejes está barriendo el volumen
de la muestra creyendo barrer el fenómeno.

---

## 5. Lectura de meseta (GT-Score) — y su lado incómodo

La regla dice preferir **meseta estable sobre pico aislado**. Acá el paisaje es
**plano en todos lados**: sin picos que sobreajustar, y sin señal en estos ejes.

Es la lectura honesta: un paisaje plano protege del sobreajuste **porque no hay
nada que ajustar.** No es una buena noticia disfrazada.

---

## 6. Consecuencias sobre el plan

1. **`ticks_per_row` deja de ser el primer eje.** Lo era por mi hipótesis de
   altura; la hipótesis murió.
2. **Sube `bar_spec`** al primer lugar de lo no explorado
   (`REGISTRO_NO_MEDIDO` §2.1). Es la única dimensión que cambia *toda* la
   agregación del footprint, y jamás se varió: 7 módulos con
   `build_time_bars(tk, 1)` hardcodeado y `build_tick_bars` sin usar.
3. **Sube E4 (la ruptura como evento).** Si el 96 % de las zonas termina rota
   pase lo que pase, la ruptura no es el fracaso del objeto: **es el objeto**.
   Estudiarla por derecho propio deja de ser una opción y pasa a ser lo obvio.
4. **F1.1 (nulo vs zonas aleatorias) gana urgencia.** Con un paisaje tan plano,
   la pregunta de si estas zonas se distinguen del azar es más apremiante, no
   menos.

---

## Aporte al referente

Se cerró una familia entera de hipótesis —«ajustar parámetros hasta que el nivel
resista»— a costo cero de multiplicidad y sin tocar un outcome, y se refutó una
hipótesis mecánica propia que estaba pre-registrada. La distancia al edge se
reduce por descarte barato: se sabe ahora que el 96 % de ruptura no es un
artefacto de configuración sino una propiedad del objeto, y que el presupuesto
de investigación no debe gastarse en los tres ejes barridos.
