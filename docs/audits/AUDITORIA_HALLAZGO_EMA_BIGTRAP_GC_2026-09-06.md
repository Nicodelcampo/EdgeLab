# Auditoría del hallazgo `RESEARCH-GC-EMA-REVERT-20260906`

> **Auditado:** commit `e50bbf3`, rama `work/bt2a-gate2-p2a-freeze-20260826`.
> **Fuente de los números de esta auditoría:** `docs/research/bigtrap_gc_ema_25tick_results.json`
> y `..._150tick_results.json` del propio commit. No se corrió nada nuevo: todo lo
> que sigue sale de recalcular los datos que el hallazgo publica.
> **Veredicto:** la dirección sobrevive; la magnitud no. **No promover a optimización todavía.**
> **Actualización 2026-09-06:** re-corrido cobrando el tick de entrada (§8). A 25
> ticks quedan 4 celdas positivas In-Sample de 44, con PF 1.01–1.04; a 150 ticks,
> ninguna. El contraste `REVERT − TREND` queda intacto porque un costo constante
> por trade se cancela en la diferencia.

---

## 1. Lo que se verificó y está bien

1. **El holdout está intacto.** `tools/optimize_bigtrap_gc_ema.py:367-368` carga
   exactamente `GC 12-25`, `GC 02-26`, `GC 04-26`, `GC 06-26`. `GC 08-26` no
   aparece en el código. La afirmación es correcta, no sólo declarada.
2. **La simulación es causal.** La entrada es el cierre de la barra de creación de
   la zona y las trayectorias arrancan en `entry_tick_idx + 1`; los ticks son de la
   sesión, sin cruce entre sesiones. El SL se evalúa **antes** que el TP dentro del
   mismo tick, que es el orden conservador.
3. **Hay un contraste real a 25 ticks.** Medido dentro de cada período —que es el
   contraste correcto— `REVERT − TREND` por trade da el mismo signo en In-Sample y
   Out-of-Sample en **18 de 20 celdas**. Eso no es trivial y es lo que hay que
   conservar del trabajo.

---

## 2. Defecto 1 — el efecto grande no es del filtro, es del período

El control **sin filtro** se comporta así:

| Barras 25t, perfil | Control IS | Control OOS |
| :-- | --: | --: |
| Asimétrica | −$962 (PF 0.99) | **+$30.230 (PF 1.41)** |
| Equilibrada | −$3.152 (PF 0.98) | +$15.390 (PF 1.18) |
| Alto Win Rate | −$3.902 (PF 0.97) | +$13.550 (PF 1.18) |
| Con BE | −$9.202 (PF 0.93) | +$12.290 (PF 1.18) |

**Todas** las configuraciones, filtradas o no, pasan de plano/negativo en
In-Sample a fuertemente positivo en Out-of-Sample. Si operar BigTrap en Oro
**sin ningún filtro** rinde +$30.230 OOS y −$962 IS, la diferencia entre los dos
períodos no la explica la EMA. La explica el régimen de `GC 04-26` + `GC 06-26`.

Por eso el titular «PF OOS 1.98» no mide el filtro: mide el filtro **más** un
período favorable. El aporte del filtro es el contraste dentro del período, y en
In-Sample es entre 4 y 7 veces más chico que en Out-of-Sample.

## 3. Defecto 2 — el Out-of-Sample ya había sido usado para seleccionar

`docs/research/INFORME_OPTIMIZACION_EJECUCION_GC.md`, del mismo día, titula su
tabla: **«Top 5 Configuraciones Validadas Out-of-Sample (25-Tick Bars)»**, y
descarta las barras de 5 ticks porque su **PF OOS** es 0.51.

Los cuatro perfiles de ejecución que usa el estudio de EMA son esos, y su
Out-of-Sample son **los mismos dos contratos**. Es decir: la resolución de barra y
el par SL/TP se eligieron mirando `GC 04-26` + `GC 06-26`, y después se reportó el
resultado del filtro sobre ese mismo conjunto llamándolo fuera de muestra.

No es fraude ni un error de cálculo: es reutilización de la muestra de test. Pero
significa que **el proyecto ya no tiene un out-of-sample para Oro** fuera del
holdout sellado.

## 4. Defecto 3 — la falsación de la hipótesis tendencial se apoya en la muestra de test

El acta declara falsada la hipótesis del usuario citando `TREND_EMA_200` en 150
ticks: **−$50.008 OOS**. En el mismo JSON, esa misma celda da **+$24.688 IS
(PF 1.03)**.

Y a 150 ticks el contraste `REVERT − TREND` **se da vuelta en 14 de 20 celdas**:
in-sample gana la tendencia, out-of-sample gana la reversión. En esa resolución el
efecto no tiene signo estable, así que ni la hipótesis tendencial está falsada ni
la de reversión está confirmada: **está sin decidir**.

La conclusión correcta es más chica y más defendible: *a 25 ticks* el contraste es
estable; *a 150 ticks* no lo es.

## 5. Defecto 4 — falta el costo de entrada

`evaluate_single_trade` cobra $4.50 de comisión round-turn y 1 tick de slippage
**sólo en el stop**. La entrada se llena exactamente al cierre de la barra, sin
spread ni deslizamiento. En GC un tick son $10.

Efecto sobre la mejor celda (`REVERT_EMA_200`, 25t, asimétrica):

| | por trade | con 1 tick de entrada |
| :-- | --: | --: |
| In-Sample (783 tr) | +$10,83 | **+$0,83** |
| Out-of-Sample (279 tr) | +$78,19 | +$68,19 |

**Un solo tick de costo de entrada borra el edge in-sample casi por completo.** El
OOS aguanta, pero el OOS es el período favorable y ya está contaminado por
selección. Un resultado que depende de que la entrada sea gratis no está listo
para optimizarse.

## 6. Defecto 5 — no hay inferencia, y la multiplicidad no está declarada

- El espacio recorrido es **11 filtros × 4 perfiles × 2 resoluciones = 88 celdas**,
  más los barridos previos de ejecución sobre el mismo activo. El acta dice
  «5 períodos canónicos», que describe un eje de la grilla, no la grilla.
- No hay intervalo de confianza, ni bootstrap, ni MCPT, ni corrección por pruebas
  múltiples. El gate G2 del proyecto exige `PrimaryCI` con bootstrap estacionario
  **clusterizado por sesión** como inferencia primaria.
- Con win rate ~11%, los +$21.000 OOS los producen unos **30 trades ganadores**.
  Sin CI no se distingue eso de una racha.
- El barrido se corrió sin el **STOP** que `CLAUDE.md` exige antes de cualquier
  búsqueda sobre P&L (manifiesto + número efectivo de hipótesis + riesgos).

---

## 7. Qué queda en pie

**Sobrevive**, como regularidad condicional y sin tamaño confiable: *a 25 ticks,
las entradas de BigTrap tomadas contra la EMA rinden más por trade que las tomadas
a favor, con el mismo signo en los dos períodos.*

**No sobrevive**: PF 1.98, +$21.252, «duplica el profit factor», «reduce el
drawdown a la mitad», y la falsación de la hipótesis tendencial.

## 8. Re-corrida cobrando el tick de entrada (ejecutada 2026-09-06)

Se re-corrieron las 88 celdas con `ENTRY_SLIPPAGE_TICKS = 1`, con los niveles de
SL/TP anclados al precio pretendido — la misma convención que el código ya usaba
para el stop: el nivel no se mueve, el costo se paga. La trayectoria no cambia, así
que el conjunto de trades es idéntico.

**Verificación del parche antes de usarlo:** la misma corrida con
`ENTRY_SLIP_TICKS=0` reprodujo el JSON original del hallazgo en **440 campos con 0
diferencias**. Lo que sigue es el efecto del tick, no un cambio de simulador.

### Resultado

| | celdas | positivas IS | positivas OOS | contraste `REV−TRD` estable |
| :-- | --: | --: | --: | --: |
| 25 ticks | 44 | **4** | 33 | **18 / 20** |
| 150 ticks | 44 | **0** | 18 | 3 / 20 |

Celdas clave a 25 ticks, perfil asimétrico (antes → después):

| Filtro | IS | OOS |
| :-- | --: | --: |
| `SIN_FILTRO` | −$962 → **−$17.412** (PF 0.87) | +$30.230 → +$23.340 (PF 1.29) |
| `REVERT_EMA_100` | +$10.610 → **+$2.700** (PF 1.04) | +$20.996 → +$18.366 (PF 1.61) |
| `REVERT_EMA_200` | +$8.476 → **+$646** (PF 1.01) | +$21.814 → +$19.024 (PF 1.61) |
| `TREND_EMA_200` | −$9.439 → −$18.059 (PF 0.75) | +$8.415 → +$4.315 (PF 1.09) |

A 150 ticks el control pasa de +$42.652 a **−$8.478** en Out-of-Sample y **ninguna
de las 44 celdas** queda positiva In-Sample. Esa resolución queda descartada por
costo, sin necesidad de discutir el filtro.

### Lectura

1. **La rentabilidad absoluta no sobrevive.** De 44 celdas a 25 ticks, sólo 4
   quedan positivas In-Sample, y las tres mejores dan PF 1.01–1.04. La celda
   estrella del acta rinde **+$0,83 por trade** contra un tick de $10.
2. **El contraste condicional sí sobrevive, intacto.** Un costo constante por trade
   se cancela en la diferencia `REVERT − TREND`: sigue siendo +$21,78 por trade en
   `EMA 200`, y sigue teniendo el mismo signo en los dos períodos en 18 de 20
   celdas a 25 ticks. Esta prueba no lo tocaba y no lo tocó.
3. **Lo que esto significa.** La EMA separa entradas de BigTrap *menos malas* de
   *más malas*. No convierte a ninguna en buena: In-Sample, con costos realistas,
   las dos mitades pierden. La rentabilidad del acta venía del tick de entrada
   regalado y del régimen de `04-26`/`06-26`, no del filtro.

**Reproducción:** `tools/optimize_bigtrap_gc_ema.py` del commit `e50bbf3` con la
variable de entorno `ENTRY_SLIP_TICKS`, corrido en la worktree
`E:/EdgeLab_worktrees/ema-audit-20260906`. Salidas en
`data/nt8_oracles/ema_audit_{25t_slip0,25t_slip1,150t_slip1}.json`.

---

## 9. Antes de optimizar

1. ~~Cobrar 1 tick de slippage de entrada y volver a correr las 88 celdas.~~
   **HECHO** — ver §8. El contraste sobrevive; la rentabilidad absoluta no.
2. Estimar el contraste `REVERT − TREND` con **bootstrap clusterizado por sesión**
   y publicar el IC, no el PnL total.
3. **Congelar una sola configuración** (resolución, SL, TP, período de EMA) por
   argumento previo, no por ranking. Cada re-ranking sobre `04-26`/`06-26` gasta
   muestra que ya no se puede reponer.
4. Conseguir un out-of-sample **nuevo**: contratos de Oro anteriores a `GC 12-25`,
   que todavía no se tocaron. El holdout `GC 08-26` se abre una sola vez, al final.
5. Recién entonces, optimizar.
