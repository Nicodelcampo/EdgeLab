# PRESET-DIVERSIFICADA: resultado

Estado: RESULTADO (descriptivo de cuenta, lectura pre-registrada en `PREREGISTRO.md`). Operar con dinero real lo decide Nico.

Herramientas:
- `tools/nt8_cartera_paridad.py`: arnés NT8, en `paridad/` y `paridad_completa/`.
- `tools/cartera_lucid.py simular --universo INTRA8|DIVERSIFICADA10`: `PLANES_*.json`.

Las operaciones de N salen del arnés: `ARNES_N_NQ.csv.gz`.

## 1. Error encontrado y corregido: el reloj caía en silencio a UTC
- `FundedSyncMath.ResolveTz` devolvía UTC sin aviso si el id de Windows de la zona no existía. Pasaba en mono/Linux, o sea en el arnés de
  paridad.
- Con el reloj corrido 4–5 h, T emparejaba 15 % contra NT8 y SOMEOD daba pérdida.
- Ahora prueba el id IANA equivalente y, si tampoco existe, falla. En NT8/Windows no cambia nada.
- Las verificaciones del arnés de esta sesión anteriores al arreglo comparaban modos entre sí (virtual contra broker, la cascada OCO).
  Siguen valiendo para la mecánica de órdenes, no para la paridad contra NT8.

## 2. Paridad de la cartera de 10 en el arnés (2018-12 → 2026-09, 1 micro c/u)

| estrategia | emparejadas con su corrida NT8 | misma entrada | P&L arnés vs NT8 (pts) |
|---|---|---|---|
| T | 98,9 % | 100 % | 20.727 vs 20.101 |
| R | 98,8 % | 100 % | 8.717 vs 8.869 |
| Z | 100 % | 100 % | 4.289 vs 4.282 |
| V | 99,7 % | 100 % | 10.600 vs 10.579 |
| RQ5 NQ | 99,7 % | 100 % | 12.003 vs 11.968 |
| Franklin NQ | 99,6 % | 1,7 % (precio) | 7.734 vs 7.194 |
| SOMEOD | 99,8 % | 100 % | 16.569 vs 16.767 |
| RQ5 ES | 99,7 % | 100 % | 2.852 vs 2.713 |
| ES5N ES | 99,0 % | 4,1 % (precio) | 1.220 vs 987 |
| N | sin corrida NT8 | — | 950 operaciones vs 881 de la traducción en Python, mismo patrón por año |

- Modo broker:
  - 0 descuadres broker/libro;
  - 0 órdenes vivas al final;
  - las mismas emparejadas.
- Franklin y ES5N empatan la operación pero no el precio de entrada (el arnés llena mejor). Ya se conocía; queda para la paridad en
  el Strategy Analyzer.

## 3. Tamaño por cuenta (media contraída a la mitad; mismo criterio de `cartera_lucid`)

| cuenta | universo | plan elegido | P(cobrar > evaluación) | sin ventaja | valor esperado | $/día | sd/día | caída máx. |
|---|---|---|---|---|---|---|---|---|
| 150K | 8 (hoy) | 1 micro c/u | **0,269** | 0,119 | +$561 | 68 | 798 | −20.339 |
| 150K | 10 (+N, SOMEOD) | 1 micro c/u | 0,224 | 0,094 | +$542 | 90 | 1.001 | −23.449 |
| 50K | 8 | 4 micros c/u | 0,176 | 0,118 | +$1.235 | 261 | 2.773 | −56.955 |
| 50K | 10 | 4 micros c/u | 0,154 | 0,106 | +$1.109 | 342 | 3.537 | −62.589 |
| 25K | 8 | 2 micros c/u | 0,170 | 0,115 | +$611 | 131 | 1.387 | −28.477 |
| 25K | 10 | 2 micros c/u | 0,149 | 0,102 | +$544 | 171 | 1.768 | −31.295 |

**Lectura pre-registrada:**
- En las tres cuentas, la cartera de 10 queda más de 0,02 por debajo de la de 8. Sumar N y SOMEOD **no ayuda en cuentas LucidFlex**.
- En la 25K y la 50K, la de 10 tampoco supera a «sin ventaja» por 0,05 (+0,047 y +0,048): esas cuentas no la llevan.
- Los planes elegidos de 25K y 50K (2 y 4 micros) son apuestas grandes, como ya decía `cartera_lucid_20261125`.

**Por qué:** la cartera de 10 no es peor por calidad. Su Sharpe diario es apenas mayor (0,090 contra 0,085). Pero con 1 micro como mínimo
por estrategia, sumar dos estrategias suma riesgo (sd +25 %, peor día −6.246 contra −4.685). En una cuenta con pérdida máxima fija, eso
cuesta más probabilidad de la que la diversificación devuelve. La decisión del 26-nov («sumar decorrelacionadas») rinde donde el riesgo
de 1 micro por estrategia es chico frente al colchón: una cuenta personal o una prop más grande. No rinde en una LucidFlex.

## 4. Qué queda
- **LucidFlex 150K:** sigue el preset `Intradia` (8, 1 micro c/u).
- **Preset `Diversificada` (10)** agregado a `EdgeLabCartera.cs` para cuentas donde el colchón es ≥ 2× el de la 150K, o para una cuenta
  personal. No se propone para Lucid.
- La decisión de incluir N y SOMEOD en cuentas Lucid la retoma Nico (pre-registro: la inclusión no dependía de este resultado; el
  resultado dice que en Lucid cuesta probabilidad).
- Pendiente de Nico: corrida del Strategy Analyzer con `Diversificada` desde 2024-01 (paridad de N y del precio de Franklin/ES5N).

Aporte al referente: deja una cartera de 10 motores con paridad verificada y un arreglo de reloj que evitaba falsos negativos de paridad.
También mide con el simulador calibrado que, en cuentas con pérdida máxima fija y 1 micro mínimo, sumar estrategias baja la probabilidad
de cobrar. La diversificación paga recién con más colchón.

## 5. Revisión (2026-11-27, pedida por Nico): el criterio por intento era demasiado estricto
La lectura de arriba usa el criterio heredado de `cartera_lucid`: máxima P(cobrar más que la evaluación) por intento. Tu regla de
frecuencia (`docs/research/FRECUENCIA_PROP_20261119.md`) pide comparar por resultado **por mes**. Con el mismo simulador y los mismos
caminos, la métrica justa por mes es la **ventaja por mes**: valor esperado por mes con la media contraída, menos el de «sin ventaja».
Esa resta aísla lo que aporta la ventaja de lo que regala la estructura de la prop: la pérdida está topeada en el precio de la evaluación.
Detalle completo en `VENTAJA_POR_MES.csv`.

| cuenta | universo, plan | P(cobrar) por intento | ventaja/mes | ventaja/mes desde 2024 |
|---|---|---|---|---|
| 150K | 8, 1 micro c/u (plan vigente) | 0,269 | +$125 | +$129 |
| 150K | 10, 1 micro c/u | 0,224 | +$153 | +$169 |
| 150K | 8, 4 micros c/u | 0,125 | +$330 | +$503 |
| 150K | 10, 4 micros c/u | 0,100 | +$337 | +$510 |
| 150K | 8, riesgo igual B800 | 0,131 | +$377 | +$375 |
| 50K | 8, inverso-vol B800 | 0,157 | +$314 | +$319 |
| 25K | 8, 2 micros c/u | 0,170 | +$142 | +$224 |

- **Por mes, la cartera de 10 iguala o supera a la de 8 en la 150K.** Con 1 micro c/u da +$153 contra +$125; con 4 micros, +$337 contra
  +$330. Con tu regla de frecuencia, `Diversificada` es preferible en la 150K. Lo de la sección 3 (P por intento) era demasiado estricto
  para tu criterio.
- **El tamaño grande rinde más por mes en las tres cuentas**, aunque cobre con menos probabilidad por intento: pasa o se rompe más rápido
  y se recompra. Para la 150K, de +$125 a +$330–377 por mes. Supuestos que lo condicionan:
  - se recompra la evaluación cada vez que se rompe (≈ 7–9 de cada 10 intentos se pierden);
  - el modelo de retiros de `cartera_lucid` es el real de Lucid;
  - el deslizamiento no crece con el tamaño (hasta 88 micros simultáneos).

  Es una decisión de riesgo y de bolsillo: la toma Nico.
- El «sin ventaja» por mes da positivo en todos los planes grandes (150K B800: +$313/mes). Es el regalo de la estructura en el modelo; si
  el modelo de retiros es optimista, ese número es el primero que se cae. Por eso la comparación usa la resta, no el valor esperado bruto.

### Cómo cargarlo en NT8 (preset `Personalizada`, campo Composición), si Nico decide subir tamaño en la 150K
| plan | Composición | micros simultáneos máx. | peor día sin DLL |
|---|---|---|---|
| vigente (8, 1 micro) | `MNQ:T=1,R=1,Z=1,V=1,RQ5=1,FR=1;MES:RQ5=1,ES5N=1` | 20 | −$4.685 |
| 10, 1 micro (`Diversificada`) | `MNQ:T=1,R=1,Z=1,V=1,RQ5=1,FR=1,N=1,SOMEOD=1;MES:RQ5=1,ES5N=1` | 26 | −$6.246 |
| 10, 4 micros | `MNQ:T=4,R=4,Z=4,V=4,RQ5=4,FR=4,N=4,SOMEOD=4;MES:RQ5=4,ES5N=4` | 40 | −$8.957 |
| 10, riesgo igual B800 | `MNQ:T=4,R=2,Z=2,V=3,RQ5=2,FR=2,N=3,SOMEOD=2;MES:RQ5=4,ES5N=4` | 89 | −$20.546 |

Todos los planes grandes dependen del límite diario de $2.700 de la 150K (el simulador corta el día ahí, como hace Lucid). Sin él, un
solo día podría superar la pérdida máxima de $4.500. Los contratos de «riesgo igual» se recalculan cada trimestre:
`python tools/cartera_lucid.py contratos --universo DIVERSIFICADA10 --esquema RIESGO_IGUAL --B 800 --tope 100`.

## 6. Corrección del simulador: el límite diario se dispara intradía (`ADENDA_DLL_INTRADIA.md`, 2026-11-27)
El simulador aplicaba el DLL sobre el cierre del día; Lucid liquida cuando el P&L del día lo toca. Se rearmó el camino minuto a minuto de
las 10 estrategias:
- extremo adverso de cada vela de 1 minuto;
- fricción al entrar;
- realizado al salir.

El camino cierra exacto contra la suma de operaciones (`tools/intradia_min_cartera.py`). Calibración K28 nueva en
`tests/research/test_cartera_lucid_calibracion.py`. Detalle: `VENTAJA_POR_MES_DLLINTRA.csv`, `PLANES_*_DLLINTRA.json`.

| 150K | ventaja/mes, DLL al cierre (§5) | **ventaja/mes, DLL intradía** | P(cobrar) por intento | días que tocan el DLL (2020–2026) |
|---|---|---|---|---|
| 8, 1 micro (vigente) | +$125 | **+$125** | 0,269 | 4 |
| 10, 1 micro | +$153 | **+$152** | 0,222 | 5 |
| 8, 2 micros | +$220 | **+$222** | 0,154 | 26 |
| 10, 2 micros | +$245 | **+$229** | 0,106 | 52 |
| 8, 4 micros | +$330 | +$213 | 0,053 | 253 |
| 10, 4 micros | +$337 | +$241 | 0,034 | 348 |
| 8, riesgo igual B800 | +$377 | +$218 | 0,044 | 343 |
| 8, riesgo igual B600 (máximo con DLL intradía) | — | +$267 | 0,077 | 192 |

- **Lectura pre-registrada:**
  - el plan de más ventaja/mes sigue siendo grande (riesgo igual B600, +$267);
  - 4 micros (+$213/+$241) sigue por encima de 1 micro (+$125/+$152).

  «Más tamaño rinde más por mes» no queda refutado.
- **Pero la ventaja del tamaño grande estaba inflada un 35–40 %,** y su probabilidad por intento cae a 3–8 % (es casi una lotería). El
  plan grande vivía en parte de días que tocaban −$2.700 y se recuperaban.
- **El punto robusto es 2 micros por estrategia:**
  - da +$222 (8) o +$229 (10) por mes, cerca del máximo;
  - cobra con probabilidad 0,11–0,15, el doble o el triple que los grandes;
  - casi no depende del DLL (26–52 días en 6,7 años);
  - desde 2024: +$241 (8) y +$243 (10).

  La cartera de 8 y la de 10 empatan con 2 micros.
- **25K y 50K se desarman con el DLL intradía:**
  - 25K, el mejor plan da +$75/mes con P 1–2 % (antes +$142);
  - 50K, +$149/mes con P 3–10 % (antes +$314).

  En esas cuentas la cartera no tiene un plan sensato.

Composición NT8 del punto robusto (150K), preset `Personalizada`:
- 8 estrategias: `MNQ:T=2,R=2,Z=2,V=2,RQ5=2,FR=2;MES:RQ5=2,ES5N=2`
- 10 estrategias: `MNQ:T=2,R=2,Z=2,V=2,RQ5=2,FR=2,N=2,SOMEOD=2;MES:RQ5=2,ES5N=2`

### Sensibilidad del DLL intradía (pre-registrada en `ADENDA_DLL_INTRADIA.md`): cota pesimista contra optimista
El camino de §6 usa el extremo adverso de cada vela para todas las estrategias a la vez (cota pesimista: con posiciones opuestas cuenta
dos veces el rango). La cota optimista usa el cierre de cada vela de 1 minuto (`SENSIBILIDAD_DLL_150K.csv`).

| 150K | ventaja/mes, pesimista | ventaja/mes, optimista | P(cobrar), pesimista / optimista |
|---|---|---|---|
| 8, 1 micro | +$125 | +$125 | 0,269 / 0,269 |
| 8, 2 micros | +$222 | +$217 | 0,154 / 0,155 |
| 8, 4 micros | +$213 | +$309 | 0,053 / 0,073 |
| 8, riesgo igual B600 | +$267 | +$291 | 0,077 / 0,084 |
| 10, 2 micros | +$229 | +$234 | 0,106 / 0,110 |
| 10, 4 micros | +$241 | +$227 | 0,034 / 0,041 |

- **Lectura pre-registrada:**
  - 2 micros no cambia entre las dos cotas: queda firme como el plan estable;
  - con 8 estrategias, 4 micros rinde por mes entre +$213 y +$309: la ventaja del tamaño grande depende de la cota y se informa como
    rango.
- **Corrección a §6:** «el tamaño grande estaba inflado 35–40 %» era la cota pesimista. Con las dos cotas, la inflación de 4 micros
  (contra el DLL al cierre, +$330) está entre 6 y 35 %. El error de Monte Carlo es ≈ ±$15–20/mes (10.000 caminos).
- **Para decidir:** 2 micros da +$217 a +$229 con certeza de modelo y P(cobrar) 0,11–0,15. 4 micros (cartera de 8) puede dar hasta
  +$309, pero con P 0,05–0,07 por intento y dependiendo de cómo se recorra cada minuto. Es elección de riesgo de Nico.
