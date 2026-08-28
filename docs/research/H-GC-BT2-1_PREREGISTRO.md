# H-GC-BT2-1 — ¿las burbujas de BigTrap2 predicen con edge económico en GC 25 tick?

- **Congelado 2026-08-21** · estado `PREREGISTERED_READY_TO_RUN`
- **Cruza el STOP**: mide outcomes. Autorizado por Nico explícitamente.
- **Consume holdout**: los datos son 2026-08-11 → 2026-08-21, dentro de la ventana sellada.
  Se declara como gasto deliberado (**P-56**), no como descuido.
- Población: oráculo `BigTrap2` v2.5.2, GC 12-26, 25 tick, **20.488 TRAPs** en 10 sesiones.

---

## 1. La hipótesis, en las palabras de Nico

> «las burbujas bigtrap2 predicen la o las siguientes velas con edge económico en 25 tick
> del GC»

## 2. Las dos correcciones que Nico impuso, y por qué son correctas

### 2.1 Ticks crudos, no velas

**El edge puede ser intravela.** Medir el cierre de la vela siguiente lo destruiría.

Y hay una razón adicional, medida: en un gráfico de 25 ticks **el eje temporal no es
uniforme**. En la captura de la segunda pantalla, las primeras ~15 barras caen todas en
`09:32:35` — **7 segundos** — y las últimas tres abarcan casi un minuto cada una.
**«N velas después» no es un horizonte.**

Por eso el outcome es una **carrera de barreras sobre el flujo de ticks**, y el horizonte
se declara en ticks **y** en reloj, nunca en velas.

### 2.2 Contextos obligatorios

Se declaran abajo, antes de medir.

## 3. Lo que la captura de pantalla contiene, y lo que esconde

Nico mostró dos capturas. Medidas: movimientos de **+50 ticks** y **+25 ticks** después de
la burbuja.

Pero **en su propia segunda captura, una de las dos burbujas no funcionó**: la primera
flecha marca una burbuja a ~4636,0 y el precio siguió bajando dos puntos. Ya es 1 de 2 en
el ejemplo elegido para mostrar.

Y hay **selección**: dos capturas entre 20.488 burbujas. No como reproche — es inevitable
mirando un gráfico — pero por eso la medición usa **la población entera**, sin el filtro
de render (`TopPercentFilter`, `SizeScaling`), que elige qué burbujas se dibujan usando
propiedades de todo el gráfico.

## 4. Definiciones congeladas

### 4.1 Dirección

| lado del TRAP | hipótesis | posición implícita |
|---|---|---|
| `trapped_buyers` | compradores atrapados **arriba** del close → baja | **corto** |
| `trapped_sellers` | vendedores atrapados **abajo** del close → sube | **largo** |

### 4.2 Outcome — carrera de barreras simétricas

Desde el **primer tick posterior** al cierre de la barra que emite el TRAP: ¿toca
**+B** antes que **−B**, en la dirección de la hipótesis?

**Grilla de barreras declarada**, anclada al rango real de la barra
(mediana **9 ticks**, p25 7, p75 11):

`B ∈ {5, 9, 18, 30}` ticks.

`B = 9` es una barra mediana; `B = 30` es lo que sugieren las capturas.

### 4.3 Horizonte — en las dos escalas

| escala | valores |
|---|---|
| ticks | **25, 50, 100, 250** (≈ 1, 2, 4, 10 barras) |
| reloj | **5 s, 30 s, 120 s** |

Si las dos escalas discrepan, **el resultado es esa discrepancia**: significa que lo que
se ve es compresión temporal, no mercado. Si no se toca ninguna barrera dentro del
horizonte, el caso se cuenta como **sin resolver** y se publica su fracción.

## 5. El margen económico — la tasa de acierto requerida

GC: 1 tick = **0,10 puntos = 10 USD**. Fricción de ida y vuelta declarada: **1,5 ticks**
(≈ 1 tick de spread + comisión). Es una estimación **para GC**, no transportada.

Para una carrera simétrica de ±B con fricción F, el punto de equilibrio es
`p* = (B + F) / (2B)`:

| B (ticks) | ganancia neta | pérdida neta | **acierto requerido** |
|---|---|---|---|
| 5 | +3,5 | −6,5 | **65,0 %** |
| 9 | +7,5 | −10,5 | **58,3 %** |
| 18 | +16,5 | −19,5 | **54,2 %** |
| 30 | +28,5 | −31,5 | **52,5 %** |

**Esto es el estimando, no un adorno.** «Significativamente distinto de 50 %» no alcanza:
hay que superar `p*`. Una barrera chica exige una tasa de acierto altísima.

**Condición de éxito**: el IC inferior del 95 % de la tasa de acierto, clusterizado por
sesión, queda **por encima de `p*`**.

## 6. Controles

Sin control, «el precio se mueve después del TRAP» no dice nada: el precio siempre se
mueve.

| población | definición |
|---|---|
| **TRAP** | evento del oráculo |
| **BARRA** | barra **sin** TRAP, misma sesión, misma fase, rango de barra ±1 tick, más cercana en tiempo, ≤30 min, sin reemplazo |

A la barra de control se le asigna una dirección **al azar con semilla fija**, para que su
tasa de acierto sea comparable con la del TRAP.

El emparejamiento se audita con SMD sobre las covariables de emparejamiento, y se publica
la cobertura — la lección de R2, donde el emparejamiento descartaba sistemáticamente las
zonas anchas.

## 7. Contextos, declarados antes

| | |
|---|---|
| **C1** fase de sesión | asia / europa / premarket / rth_am / rth_pm / cierre |
| **C2** régimen de volatilidad | terciles de `pct_rv`, percentil **expansivo** por bucket de 15 min |
| **C3** fuerza del evento | terciles de `max_ratio` y de `vol` |

`C1` es primario porque el censo del atlas mostró que la distribución es muy nocturna
(asia 4.530 contra rth_pm 8.725), lo que no esperaba para el oro.

## 8. Inferencia y potencia

Unidad: **la sesión**. Bootstrap de sesiones completas, **B = 10.000**, seed **20260821**.

**Son 10 sesiones.** El MDE va a ser grande y se publica **antes** de leer el punto. Con
tan pocas sesiones esto sirve para **descartar efectos grandes**, no para confirmar
efectos chicos.

Multiplicidad: 4 barreras × 4 horizontes de tick = **16 celdas primarias**, corregidas por
Holm. Los horizontes de reloj y los contextos son **secundarios**, rotulados como tales.

## 9. Cómo se refutaría

- La tasa de acierto no supera `p*` en ninguna celda → **no hay edge económico**, aunque
  hubiera señal estadística.
- El TRAP no se distingue de la barra de control → el efecto es «hubo una barra», no el
  indicador.
- El resultado aparece en la escala de ticks pero no en la de reloj → compresión temporal.
- El efecto aparece sólo en `B = 30` y no en las barreras chicas → es deriva de mercado
  capturada por una barrera lejana, no reacción al evento.

## 10. Lo que este estudio NO decide

No hay reglas de entrada ni salida más allá de la barrera, ni sizing, ni gestión de
riesgo, ni slippage modelado, ni fills. Un resultado positivo acá **no es una estrategia**:
es evidencia de que vale la pena construir una.

Y **consume holdout**. Si sale positivo, la confirmación necesita datos nuevos —
idealmente el contrato `GC 08-26` en junio, que es **pre-holdout**.
