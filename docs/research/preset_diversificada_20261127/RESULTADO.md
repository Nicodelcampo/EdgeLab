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
