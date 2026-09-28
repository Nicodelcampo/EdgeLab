# Manifiesto: provisión pasiva de liquidez filtrada por QI (familia MM-QI), NQ · GC · ES · 6E L2, 2026-09-24

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** PROPUESTO. Es una **búsqueda sobre P&L**: **STOP, necesita el OK de Nico.**
**Ledger:** `artifacts/hippocampus/mm_qi_20260924.jsonl` (familia nueva). No hereda presupuesto de EXEC-QI, ABS-CTX ni de las demás.

## 1. Por qué es la tarea más importante ahora

| Candidata | Cercanía a un edge neto | Probabilidad | Originalidad | Potencia | Nota |
|---|---|---|---|---|---|
| **MM-QI: entrar pasivo, salir pasivo y cobrar el spread, con filtro de QI** | **Directa**: es una estrategia completa con P&L neto | Media-baja: el retail compite contra HFT por la cola | Alta en este proyecto: usa el modelo de costo recién construido | Muy alta (miles de intentos por sesión) | Riesgo principal: el modelo de fill |
| Volatilidad por disputa de nivel (V-VIRGEN y V-GASTADA) | Indirecta: tamaño y stops | Media | Alta | Media | Sin P&L propio |
| Re-auditar la familia A y el atlas de GC | Nula | Alta | Baja | — | Higiene; se puede hacer en paralelo |
| Momentum intradía (literatura) | Directa | Media | Baja | Baja (~250 días) | La potencia no alcanza |
| Órdenes reales (etapa 3 de EXEC-QI) | Valida el costo | — | — | — | Cuesta plata: decisión de Nico |

**Por qué MM-QI.** En NQ y GC el spread mediano es de 4 a 5 ticks (validado 20/20 contra Tradovate). La orden pasiva se llena el 79 % de las veces en 30 s incluso con cola pesimista, y la selección adversa medida es de −1,7 ticks a 60 s. Una ida y vuelta pasiva cobra el spread (~5 ticks) y paga dos veces la selección adversa. La cuenta gruesa da positivo, **pero nadie la midió**. Es la pregunta de P&L más directa que las herramientas de hoy permiten contestar.

**Justificación económica.** Un spread ancho es una prima que el mercado paga por proveer liquidez. El QI filtra los momentos en que proveer liquidez de un lado sufre menos selección adversa (Cartea, Jaimungal y Penalva, *Algorithmic and High-Frequency Trading*, cap. de *market making* con imbalance; Stoikov 2018, *microprice*).

**Cómo podría refutarse.** Que el P&L neto por intento, después de comisiones y del cruce forzado de los que no salen, tenga el IC por debajo de 0 o incluyendo 0 en todas las variantes. O que sólo sea positivo con cola optimista o latencia cero (dependencia del modelo).

## 2. Regla (fija, sin optimizar)

- **Instantes de decisión:** grilla de 1 s, **una posición a la vez**. Después de salir se espera al segundo siguiente.
- **Filtro de entrada:** se calcula d·QI para los dos lados (d = +1 compra en el bid, d = −1 venta en el ask). La **variante** fija qué tercil de d·QI habilita el lado: "contra" (el precio viene hacia la orden), "neutral" o "a favor". Si los dos lados califican, gana el de |QI| mayor. Si ninguno califica, no hay orden.
- **Entrada:** límite en el mejor precio propio, puesta en t + 250 ms, con la cola pesimista de `exec_qi.simulate_passive`. Si no se llena en **30 s, se cancela** (MM no persigue) y no hay trade.
- **Salida:** apenas se llena, límite en el mejor precio **contrario** vigente en ese instante, con la misma cola pesimista. Si no se llena en **T_out** ∈ {30, 120} s, se cruza a mercado al precio contrario.
- **Comisiones y fees, conservadores, por lado:** USD 2,50, que equivalen a NQ 0,5 t, GC 0,25 t, ES 0,2 t y 6E 0,4 t.
- **Variantes:** 3 terciles × 2 valores de T_out = **6 por instrumento, 24 en total**.

## 3. Métricas

- P&L neto por **intento** y por **operación ejecutada**, en ticks y en USD.
- P&L por sesión.
- Fracción de salidas pasivas contra cruzadas.
- Distribución completa (p5, p50, p95) y peor sesión.

IC por sesión (bootstrap, 2.000 réplicas).

**Sensibilidad obligatoria** (no decide; si cambia el signo, invalida):
- latencia de 1 s en lugar de 250 ms;
- cola ×2 (la mitad de rápido).

## 4. Datos y particiones

Sólo **exploración**:
- NQ: `P-NQL2-EXP` (41 sesiones);
- ES, GC y 6E: las mismas sesiones de `P-VRND-*` (41, 31 y 38).

Se declaran particiones nuevas `P-MMQI-<inst>` en el ledger propio. `P-NQL2-CONF` y el holdout L2 (nov–dic) quedan **intactos**. Una variante que pase se confirma **sólo** en `P-NQL2-CONF`, con una spec en revisión ciega y una campaña aprobada.

## 5. Regla de sugerencia (escrita antes de correr)

Una variante es SUGERENCIA sólo si cumple todo esto:
- IC por sesión del P&L neto por intento **> 0**;
- sigue > 0 **en las dos sensibilidades**;
- es positiva en ≥ 60 % de las sesiones.

No se elige la mejor variante por su punto máximo. Se publican las 24.

## 6. Riesgos (el que manda es el primero)

1. **El modelo de fill no está validado contra el mercado real.** Frente a NT8 es conservador (79 % contra 90 %), pero una cola real con HFT puede ser peor que "detrás de todo lo visible". **Cualquier resultado positivo queda condicionado al modelo** y **no se promueve sin fills reales** (etapa 3 de EXEC-QI).
2. **Latencia real desconocida.** Por eso la sensibilidad de 1 s.
3. **Relojes de P-84:** los días no certificados quedan excluidos.
4. **24 miradas:** mitigado porque todo es exploración y la reserva no se toca.
5. **No se transportan costos entre instrumentos:** cada uno tiene su comisión en ticks y su propia simulación.

## 7. Resultado (24/09): MUERTA en su alcance declarado

Reporte `artifacts/mm_qi/report.json` (sha `06cf0bb8e624…`). Sesiones: NQ 41, ES 40 (sin el 21/08, P-92), GC 31 y 6E 38. Ninguna sugerencia.

| Inst. | P&L neto por intento (rango de las 6 variantes) | Por trade | Sesiones positivas | Latencia 1 s / cola ×2 |
|---|---|---|---|---|
| NQ | −3,77 a −3,91 t | ≈ −4,5 t | **0 %** | igual o peor |
| GC | −2,16 a −2,30 t | ≈ −3,4 t | **0 %** | igual o peor |
| ES | −0,85 a −0,90 t | ≈ −1,2 t | **0 %** | igual o peor |
| 6E | −0,34 a −0,74 t | ≈ −1,9 t | **0 %** | igual |

**Lectura:**
- Proveer liquidez de forma pasiva **pierde en todos los instrumentos, variantes y escenarios**, y ninguna sesión termina positiva.
- El mecanismo, medido en NQ:
  - la entrada pasiva se llena cuando el precio ya va ~2 ticks en contra;
  - la salida pasiva cobra sólo ~+0,5 t;
  - las salidas que no se llenan cuestan ~−25 t.
- **El filtro de QI no rescata nada**: los tres terciles dan prácticamente lo mismo.
- Este modelo de fill es **más favorable** que la realidad (P-89: NT8 y los foros coinciden en que el fill real es peor), así que el resultado real sólo puede ser peor.

**Alcance de la muerte:**
- **Muere:** la provisión pasiva de ida y vuelta, con esta regla y con filtro de QI, en NQ, GC, ES y 6E.
- **No muere:**
  - el uso de la orden pasiva para **entrar** en una estrategia con otra fuente de ventaja (EXEC-QI);
  - el market making con información adicional, que no se midió.

**Lección para las estrategias tendenciales** (Nico, 24/09): en las operaciones que dependen de movimientos que se escapan, la orden pasiva se llena cuando uno se equivoca. TBZ-E2 y TREND-MICRO usan entrada agresiva por diseño.
