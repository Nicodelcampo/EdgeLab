# EdgeExperiment en el embudo de EdgeLab — resultado (2026-10-03)

Pre-registro: `PREREGISTRO_EMBUDO.md` (y su enmienda 1, escrita al ver los resultados 1–5 y antes de correr los controles de deriva). Números: `resultados_embudo.json`. Contador de pruebas: `trial_registry.jsonl` (63 pruebas, cadena válida). La lógica de la estrategia no está en este repositorio.

## Veredicto final
**`EDGE_NO_CONFIRMADO`.** Antes del holdout la réplica era un candidato (ver abajo); la confirmación única en el holdout de MNQ (jul–sep 2026) **falló** los criterios pre-registrados, y la apertura posterior de la cesta MES+RTY+YM (enmienda 5) tampoco los cumplió (efecto positivo pero IC95 que incluye 0; ver su sección).

| Holdout MNQ, serie correctamente especificada (corrida 3, enmienda 4) | |
|---|---:|
| Trades / sesiones | 395 / 41 |
| Media neta por trade (fills de libro, comisión real) | **−4,4 ticks** (−USD 2,2) |
| IC95 por bootstrap de sesiones | −32,4 a +23,5 |
| «Siempre largo», mismas horas | +3,4 |
| p nulo de dirección / que preserva exposición / calendario placebo | 0,46 / 0,60 / 0,26 |

Éxito exigía media > 0, IC que excluya 0, los tres p ≤ 0,05 y superar a «siempre largo»: no se cumple ninguno. El IC de ±28 ticks es ancho, por lo que **no demuestra que el efecto sea cero**: su extremo superior (+23,5) queda justo por debajo del IS (+23,9), es decir, el holdout es compatible con «sin edge» y casi excluye un efecto del tamaño observado en IS.

**Cómo llegamos a esa cifra (transparencia).** Hubo tres lecturas del mismo tramo; las dos primeras fueron ejecuciones defectuosas mías (roll mal especificado que dejó a MNQ_12-26, ilíquido, como líder en julio–agosto), documentadas en las enmiendas 3 y 4 antes de repetir: corrida 1 −18,1 ticks (307 trades), corrida 2 −17,5 (309), corrida 3 −4,4 (395). La corrida 3 no es ciega. Los datos del holdout en Kaggle **tienen cobertura incompleta** (5 sesiones faltantes y varias truncadas en MNQ_09-26); se excluyeron las sesiones con menos del 50 % del volumen mediano. Un test limpio requiere el histórico 1 minuto completo de MNQ jul–sep exportado desde NinjaTrader, o datos nuevos (trading en demo hacia adelante).

## Datos y réplica
- MNQ, ticks de Kaggle, 2025-08-01 a 2026-06-30 (holdout de EdgeLab `2026-06-30T22:00Z` sin tocar), 211 sesiones; huecos 03-20→04-06 y 06-10→06-25.
- Barras de 1 minuto desde ticks: 27/27 trades de la réplica coinciden exactamente con los generados sobre las barras de NinjaTrader (SEP26, hasta el holdout). Las tablas de oportunidades reproducen las 1.959 señales y los 1.929 trades no cerrados por netting, con 0 diferencias.
- Ejecución principal: mercado en el primer tick tras la orden, compra al ask / venta al bid; comisión de usuario USD 1,90 ida y vuelta = 3,8 ticks.

## Resultados MNQ (ticks netos por trade; 1 tick = USD 0,50)
| | IS (hasta 2026-05-27) | OOS (desde 2026-05-28) |
|---|---:|---:|
| Trades / sesiones | 1.837 / 198 | 122 / 13 |
| Media neta, fills de libro | **+23,9** (IC95 +12,3 a +35,4) | **+83,8** (IC95 +26,5 a +142,3) |
| Media neta, fills al open de barra (réplica del proveedor) | +25,8 | +86,0 |
| Nulo de dirección por sesión (5.000) | p = 0,0002 | p = 0,007 |
| Nulo de dirección que preserva la exposición (5.000) | p = 0,0002 | p = 0,001 |
| Calendarios placebo (2.000) | p = 0,0005 | p = 0,0015 |
| Línea base «siempre largo», mismas horas | +8,0 | −5,5 |
| Sin la mejor sesión / sin las 3 mejores (total, ticks) | 40.683 / 35.654 | 7.245 / 3.618 |
| Largos / cortos (total, ticks) | 33.124 / 10.787 | 5.048 / 5.170 |
| Con 1 tick de slippage por lado | +21,9 | +81,8 |

- **Mejor de 60 reglas** (nulo de máximo del embudo, IS partido en D0/D1, 24 reglas con ≥10 trades en ambos tramos): **p_max = 0,22**. Ninguna regla individual se distingue del azar una vez corregida la selección entre 60. La evidencia es del conjunto (patrón de calendario), no de reglas sueltas.
- Rentabilidad positiva en 10 de 11 meses; positiva en largos y en cortos; positiva por tenencia (15/30/60 min), por franja horaria (overnight, Londres/pre-apertura y sesión de EEUU) y por tipo de filtro (continuación, reversión y sin filtro).
- P&L descriptivo con netting entre reglas (1 contrato): IS +USD 21.885 y OOS +USD 5.098 con fills de libro.

## Qué no queda demostrado
1. **OOS corto y no virgen**: 13 sesiones, 122 trades. El usuario vio estadísticas agregadas del backtest del proveedor de jun–sep sobre contratos poco líquidos. El OOS (+83,8) es 3,5 veces el IS (+23,9): lo razonable es esperar algo más cercano al IS, o menos si el calendario se minó.
2. **Multiplicidad desconocida**: el proveedor eligió 60 reglas de un espacio que no conocemos. El IS está contaminado por esa búsqueda; sólo el OOS cuenta, y el mejor-de-60 no se rechaza.
3. **Supuestos**: calendario de sesión CME mínimo (la plantilla de NinjaTrader no estaba disponible); ejecución idealizada (sin latencia); la réplica reproduce lo observado en dos contratos pero hay parámetros no identificables (calentamiento, margen de sesión).
4. **Cobertura**: faltan 2 semanas de junio y el tramo marzo–abril.

## Transferencia: mismo calendario congelado, sin reoptimizar
| Activo | IS media neta (ticks) / trades | OOS media neta / trades | p dirección OOS | p calendario placebo OOS |
|---|---|---|---:|---:|
| YM (Dow) | +3,8 (IC +0,4 a +7,4) / 1.875 | +15,8 (IC +6,3 a +25,1) / 227 | 0,0003 | 0,0005 |
| GC (oro) | +5,8 (IC −2,3 a +14,7) / 1.963 | −5,5 (IC −20,7 a +11,8) / 226 | 0,58 | 0,40 |
| ZB (bono 30a) | −0,8 / 1.358 | −0,8 / 171 | 0,20 | 0,35 |
| 6J (yen) | −1,4 / 1.796 | −1,8 / 174 | 0,75 | 0,81 |

Comisión USD 1,90 convertida a ticks de cada activo (para YM y GC es menor que la real de un contrato completo). Lectura: **sólo se transfiere a otro índice bursátil**; no a oro, bonos ni yen. Un índice correlacionado no es una réplica independiente (YM y MNQ comparten el flujo intradía de EEUU).

## Transferencia a otros índices (solo datos previos al holdout; sus holdouts no se abrieron)
Mismo calendario congelado, ejecución de libro, comisión USD 1,90 en micros y USD 4,50 en contratos completos (supuesto). OOS = sesiones 2026-05-28 a 06-30 (24 sesiones por la mayor cobertura de estos activos).

| Activo | IS media neta (ticks) / trades | OOS media neta / trades / IC95 | p OOS (dirección, exposición, calendario) |
|---|---|---|---|
| ES | +4,9 / 2.045 | +15,8 / 230 / +9,9 a +22,0 | todos < 0,001 |
| NQ | +31,1 / 1.974 | +114,8 / 227 / +71,7 a +156,6 | todos < 0,001 |
| MES | +3,8 / 1.629 | +15,1 / 230 / +9,1 a +21,2 | todos < 0,001 |
| RTY | +3,9 (IC −1,7 a +9,3) / 694 | +16,8 / 234 / +10,1 a +23,8 | todos < 0,001 |
| YM (USD 4,50) | +3,3 / 1.875 | +15,3 / 227 / +5,7 a +24,6 | < 0,001 / 0,002 / < 0,001 |

(p < 0,001 = ningún sorteo igualó el resultado real.) Las predicciones registradas (ES, NQ y MES parecidos a YM) se cumplieron. **Pero estos cinco índices están muy correlacionados con MNQ y comparten el mismo período OOS y el mismo régimen, así que no son confirmaciones independientes**; y el holdout de MNQ, que cubre el período posterior, no confirmó. Oro, bonos y yen siguen sin evidencia (tabla de la sección anterior).

## Holdout de la cesta MES + RTY + YM (enmienda 5, una sola apertura)
Ventana: sesiones del 2026-07-01 al 2026-09-28 en el contrato líder por volumen (09-26 hasta el 14 de septiembre; 12-26 después). Sesiones faltantes o truncadas excluidas con la regla pre-registrada. ES y NQ no tienen datos posteriores al holdout en Kaggle; MYM se omitió por duplicar el Dow. Cesta de 1 MES + 1 RTY + 1 YM, USD netos de comisión.

| | Operaciones | Sesiones | Media neta por operación (USD) | «Siempre largo» (USD) |
|---|---:|---:|---:|---:|
| MES (USD 1,90) | 501 | 53 | −2,70 | −1,92 |
| RTY (USD 4,50) | 584 | 60 | +6,36 | −1,38 |
| YM (USD 4,50) | 476 | 52 | +14,05 | −4,38 |
| **Cesta** | **689** | **60** | **+13,13** (IC95 **−25,8 a +61,3**) | **−5,59** |

Nulos sobre la cesta: dirección por sesión **p = 0,066**; dirección que preserva exposición **p = 0,016**; calendarios placebo **p = 0,015**.

**Criterio pre-registrado: no se cumple.** Exigía IC95 que excluya 0 y los tres p ≤ 0,05. El IC incluye 0 (−25,8 a +61,3) y el nulo de dirección queda en 0,066. Sí se cumplen la media positiva, la superación de «siempre largo» y dos de los tres nulos. Por la regla escrita antes de ver los datos, el resultado es **NO CONFIRMADO**.

**Defecto declarado.** La mediana de volumen de 12-26 se calculó con todos sus días desde julio, incluidos los de contrato lejano (mediana de 149 contratos en RTY), de modo que su umbral de elegibilidad fue casi nulo. Cumple la letra de la enmienda, no su intención. Sensibilidad post hoc con la mediana calculada solo en los días en que cada contrato es líder (`holdout_cesta_sensibilidad_elegibilidad.json`): media +13,44 USD, IC95 −25,6 a +61,7, p = 0,065 / 0,016 / 0,015. El defecto no cambia el resultado. El resultado principal sigue siendo el pre-registrado.

**Cómo leerlo.** El efecto sigue siendo positivo en la cesta y no es deriva de mercado (los dos nulos que fijan la exposición pasan), pero el intervalo es muy ancho (60 sesiones) y el resultado depende de YM y RTY: MES, el contrato con más volumen, fue negativo. MNQ, medido antes con la misma especificación, también fue negativo (−4,4 ticks). El conjunto de los cuatro mercados no es una confirmación ni una refutación limpia.

## Lectura final
1. Hay un patrón de calendario que funcionó en 2025-08 a 2026-06 en todos los índices de acciones y que no es deriva ni suerte de una sola regla; es coherente con una estacionalidad intradía real o con un régimen de esos diez meses.
2. En el período siguiente (jul–sep 2026) el resultado es mixto: negativo en MNQ y en MES, positivo en RTY y YM, y +13 USD por operación en la cesta MES+RTY+YM con un intervalo que incluye 0 y un nulo de dirección en 0,066. Ninguno de los dos tests cumple el criterio pre-registrado.
3. La explicación más parsimoniosa: un calendario minado por el proveedor sobre datos hasta mayo-2026 con sobreajuste parcial más un junio excepcionalmente favorable. No se puede descartar un efecto menor.
4. Qué haría falta para cerrar: histórico MNQ 1 minuto completo jul–sep desde NinjaTrader (o datos hacia adelante) y, si se quiere seguir, correr el mismo calendario congelado en demo antes de arriesgar capital.
