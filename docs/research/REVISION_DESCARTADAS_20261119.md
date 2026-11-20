# Revisión de lo descartado la noche del 18 al 19-nov: errores de encuadre que dejaban afuera reglas frecuentes (2026-11-19)

Estado: VIGENTE — análisis descriptivo sobre operaciones ya medidas. No abre holdout ni cuenta pruebas; la ventana 2018 → 2025-07 es la misma
convención por época de `RE_INDAGACION_PISTAS_20261119.md` y `FRECUENCIA_PROP_20261119.md`.
- **Pedido de Nico:** «releé todo lo que hiciste a la noche … si hay errores de medición o conclusiones equivocadas que podrían dejar
  fuera estrategias buenas con más frecuencia y edge. Como A20». También: PICOS-DEFENDIDOS opera muy poco, hay que encontrar cómo opere
  más, con menos fricción y que valga la pena.
- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. El error que se repite
Varias reglas se descartaron por su R neto promedio de toda la ventana (2006/2008 → 2025). Pero la fricción relativa cayó a menos de la
mitad desde ≈ 2018 (fricción / riesgo en NQ: 0,13 → 0,03): el promedio largo mezcla años en que la fricción se comía todo con años en que no.
La directiva «edges actuales» (Nico, 2026-10-22) pide mirar el régimen actual. Para T se hizo (régimen desde 2021); para estas reglas, no.

## 2. Reglas afectadas (R neto por operación, fricción canónica)
| Regla | Ventana | Bloque | Ops/mes | R/op | Fricción/R | Comentario |
|---|---|---|---|---|---|---|
| **RQ5** (Noise-Band Momentum, Zarattini; NQ+ES+YM) | 2006–2017 | DESC | 42 | −0,050 | 0,094 | lo que hundía el promedio |
| RQ5 | **2018–2025** | **DESC** | **40** | **+0,051** | 0,029 | NQ +0,082, ES +0,093, YM −0,022 |
| RQ5 | **2018–2025** | **REP** | **43** | **+0,054** | 0,025 | NQ +0,042, ES +0,048, YM +0,072 |
| RQ5N (control: ruptura tardía) | 2018–2025 | DESC / REP | — | −0,052 / −0,133 | — | el control pierde |
| FM2 (FLUJOS-MACRO) | 2018–2025 | DESC / REP | 22 | +0,061 / +0,014 | 0,02 | más débil |
| RQ6 | 2018–2025 | DESC / REP | 48 | +0,029 / −0,022 | 0,03 | no se sostiene |
| FM1 | 2018–2025 | DESC / REP | 83 | +0,011 / −0,007 | 0,015 | ≈ 0 |
| **A20** (FundedSync, NQ, fábrica) | 2008–2017-10 | — | 21 | −0,295 | ≈ 0,13 | |
| A20 | 2018–2025-07 | — | 20 | +0,052 | ≈ 0,03 | R/mes +1,03, t 0,94 |
| A20 | 2022–2025-07 | — | 20 | +0,185 | — | R/mes +3,69, t 2,43, 63 % meses + |
| A20 | 2025-08 → 2026-09 | — | 19 | +0,190 | — | R/mes +3,57, t 1,6 |

RQ5 por año, 2018–2025 (R/op): +0,070, −0,018, +0,096, +0,005, +0,023, +0,051, +0,072, +0,122 (7 de 8 positivos).

Episodios:
- **RQ5 DESC 2018–2025:** media +0,051 (n 2183); sin los 3 peores meses +0,076; sin los 3 mejores +0,019. Peores: 2022-01 −14,8; 2020-03 −14,7;
  2021-11 −13,0. Mejores: 2020-06 +27,8; 2020-09 +23,9; 2024-07 +20,6.
- **RQ5 REP 2018–2025:** media +0,054 (n 683); sin los 3 mejores −0,003.
- **A20 2018–2025-07:** media +0,052 (n 1822); sin los 3 mejores +0,003.
- **Lectura:** las dos dependen de pocos meses buenos; son reglas de cola derecha.

Diagnóstico de grilla:
- **A20:** 81 variantes con número efectivo de variantes 1,19 (operaciones por celda ≈ 1.800 en 2018–2025-07). El «81/81 positivas» y el PBO
  0,39 del acta A20-REGIMEN no informan nada: se juzga la serie de la fábrica.
- **RQ5:** una sola definición; no hay grilla.

## 3. Lo que cambia respecto de la noche
1. **RQ5:**
   - se había leído «bruto real, neto negativo» sobre toda la ventana;
   - en el régimen actual el neto es positivo en DESC y en REP con el mismo tamaño (+0,05 R), con ≈ 40 operaciones por mes y el control en
     contra;
   - es la regla más frecuente con neto positivo replicado que tiene el catálogo.
   - **No está confirmada:** el corte 2018 es una convención por época, no un pre-registro de RQ5, y REP ya se había calculado para la familia.
2. **A20:**
   - el acta decía «sólo forward con vigilancia podría sostenerlo», pero **A20 no está en la vigilancia forward** (el kernel forward corre
     sólo T, Z y R);
   - es una omisión, no una conclusión;
   - sumarla a T sube el R/mes (2,27 → 3,30) pero baja la consistencia (t mensual 4,67 → 2,46; meses positivos 64 % → 54 %);
   - con la directiva de frecuencia (comparar por R/mes y consistencia) no mejora a T en desarrollo. Correlación mensual con T 0,33.
3. **Confirmación posible de RQ5:**
   - holdout A5 de ROBOQUANT en los meses HOLDOUT 2018–2025: ≈ 860 operaciones; potencia 0,42 para el efecto entero y 0,18 para la mitad;
   - una sola apertura por familia, combinable con DESC y REP en modo exploratorio (Fisher);
   - y forward.

## 4. PICOS-DEFENDIDOS: frecuencia contra fricción (conteo de eventos sin desenlaces, M1 2025-08 → 2026-03, ya mirado)
| Diseño (NQ) | Ops/mes | Riesgo mediano (pts) | Fricción/R con stop 1 A | Fricción/R con stop estructural |
|---|---|---|---|---|
| Regla de la captura (10 min, PAR, E20 a favor, ALEJA) | 13,6 | 11,5 | 0,076 | 0,135 |
| 10 min, PAR, primer disparo de cada candidato, cualquier tendencia | 50,4 | 11,8 | 0,074 | 0,132 |
| 10 min, los tres tipos de pico, primer disparo | 272,6 | 12,3 | 0,072 | 0,126 |
| 10 + 15 min, los tres tipos de pico, primer disparo | 435,8 | 13,3 | 0,067 | 0,116 |
| 5 + 10 + 15 min | 1.046,1 | 10,3 | 0,086 | 0,150 |

En ES, YM y RTY los mismos diseños dan una frecuencia parecida pero una fricción/R de 0,18–0,43 (el riesgo es de 1–3 puntos en ES y RTY):
quedan fuera.

Lectura (datos):
- **La frecuencia no es el problema:** juntar los tres tipos de pico, tomar el primer disparo de cada candidato y usar 10 y 15 min lleva
  NQ de 14 a ≈ 400 operaciones por mes.
- **El límite es la fricción contra el bruto:** en el DESC de ticks el bruto de 10 y 15 min fue +0,06 a +0,08 R con stop estructural, y la
  fricción con ese stop es 0,12–0,13 R. Agrandar el stop baja la fricción/R pero también el bruto por R si el bruto en puntos no crece (la
  palanca del stop ya se probó en SOM y Franklin).
- **Diseño que vale el experimento:** **una sola prueba agrupada**, NQ, 10 + 15 min, los tres tipos de pico, primer disparo, stop 1 A y
  objetivo 1 A más allá del nivel, en el M1 de 18 años con la partición A5. Con ≈ 400 operaciones por mes en los meses DESC (≈ 100 meses),
  la prueba tiene decenas de miles de operaciones: detecta +0,02 R. Así contesta de una vez si el bruto supera la fricción, sin grilla.

## Justificación económica / cómo podría refutarse
- **Justificación:** RQ5 y A20 son reglas de momentum intradía cuyo bruto existe desde siempre. Su neto depende de la fricción relativa,
  que cayó con el nivel de precio de los índices.
- **Cómo podría refutarse:** el holdout A5 o el forward de RQ5 con media ≤ 0; para A20, el forward con media ≤ 0; para PICOS-DEFENDIDOS,
  la prueba agrupada con bruto ≤ fricción.

Aporte al referente: encuentra dos reglas frecuentes (≈ 20 y ≈ 40 operaciones por mes) descartadas por un promedio que mezclaba épocas de
fricción distinta, y reduce PICOS-DEFENDIDOS a una sola prueba con potencia en vez de una grilla.
