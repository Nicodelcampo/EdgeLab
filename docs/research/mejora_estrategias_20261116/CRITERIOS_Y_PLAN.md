# Cómo mejorar una estrategia sin engañarnos: criterios, método y plan (2026-11-16)

Estado: VIGENTE — pre-registro del programa de mejora. Pedido de Nico: «definí criterios para intentar mejorar la estrategia, iterá la
planificación una vez buscando maximizar rentabilidad, estabilidad y potencia de lo último de Antigravity, y después repetí el proceso con las
otras donde valga». North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. Qué es «mejor» (criterios, en orden)
| # | Criterio | Medida | Por qué esta y no otra |
|---|---|---|---|
| C1 | **Rentabilidad neta** | R neto por **mes** (no por operación) y su t mensual | Un filtro que sube el R por operación pero corta la mitad de los días puede ganar menos por mes. El t mensual junta media, variabilidad y cantidad. |
| C2 | **Estabilidad** | años positivos; bloques; peor año; vecinas también buenas (meseta) | La lección dura (F-SELECCION-EN-GRILLAS-GRANDES): lo elegido como pico aislado vale ≈ 0 en la réplica. |
| C3 | **Potencia** | operaciones por mes y MDE del R por operación | Más operaciones independientes = el forward decide antes (e-proceso) y la prop se pasa en menos días. |
| C4 | **Ejecutabilidad y riesgo** | fricción en R ≤ 0,08; nada abierto el fin de semana; drawdown máximo y peor racha en R | Regla de Nico y de las props; la fricción se come las reglas de stop corto (F-STOP-CORTO-ES-FRICCION). |
| C5 | **Diversificación** | correlación diaria con la v2, la Cartera B y Franklin | Una mejora que copia lo que ya tenemos suma poco a la cartera. |

**Puntaje para elegir:** t del R mensual (C1). **Restricciones duras:** C4. **Desempate y veto:** C2 (no se elige una variante con menos
años positivos que la base) y C3.

## 2. Método (lo que la historia del proyecto obliga)
- **Variantes por mecanismo, una perilla por vez** (ATJ-26, marginales): cada variante declara su mecanismo y cómo podría refutarse. Nada de
  grillas grandes: tope de ~15 variantes por estrategia (F-SELECCION-EN-GRILLAS-GRANDES, K4).
- **Las palancas que ya probaron servir se prueban primero**: dejar correr la salida (F-SALIDA-TECNICA-REGALA-LA-GANANCIA), stop grande
  frente a la fricción (F-STOP-GRANDE-FRENTE-A-FRICCION), tamaño fijo y piso de fricción (MEJORAS M1/M3), contexto de noche movida
  (F-ASIA-NQ-NOCHE-MOVIDA), acuerdo con otra regla (Franklin como filtro de T).
- **No se repite lo que no sirvió**: filtros de contexto que eran fricción (F-ATLAS-CONTEXTO-ES-FRICCION), rotar por régimen reciente
  (F-REGIMEN-OFFLINE), freno diario (F-FRENO-DIARIO-NO), KNN por voto (F-KNN-VOTO-NO-TRANSFIERE), tamaño por volatilidad pronosticada.
- **Elegir y confirmar en datos distintos**, con la regla de confirmación escrita antes; el holdout ya abierto no se toca para elegir; lo
  que confirma va a **forward como versión paralela** (la base sigue, nunca se reemplaza sin forward).
- Siempre en R neto con costos canónicos; test de causalidad de cada código nuevo; corrida con código corregido = se descarta y se relanza.

## 3. Plan, primera versión (v0)
SOM: barrer EMA rápida {6, 12, 24} × stop {6, 8, 10} × EMA de trailing {60, 120, 240} × arranque {0, 0,5, 1} R × hora {09:35, 09:45, 10:00}
= 243 combinaciones en NQ, ES y YM; elegir la de mayor R por operación en 2012–2019 y confirmar en 2020–2026.

## 4. Crítica de la v0 (contra la historia y las herramientas)
1. **243 × 3 es una grilla de retornos sin E0**: exactamente lo que K4 y F-SELECCION-EN-GRILLAS-GRANDES prohíben; la mejor celda va a ser
   un pico. → marginales alrededor de la base de fábrica, una perilla por vez.
2. **Optimiza R por operación**: premia filtrar operaciones aunque baje la ganancia mensual y la potencia. → puntaje = t del R mensual.
3. **Elegir en 2012–2019 y confirmar en 2020–2026** favorece lo que andaba en el régimen viejo (ATJ-24: queremos lo que anda ahora) y deja la
   confirmación sin datos viejos. → **elegir en años pares, confirmar en años impares**: cada mitad tiene régimen viejo y nuevo y la misma
   cantidad de datos; lo reciente se informa aparte.
4. **Sólo perillas de parámetros**: ignora las palancas que sí mejoraron reglas en el proyecto (frecuencia, salida, contexto, acuerdo con otra
   regla). SOM tiene una restricción cara: **no abre si la anterior sigue abierta** (en el Tester se perdieron 86 de ~250 días por año). →
   agregar la variante **rotar** (a las 09:35 cierra la vieja y toma la señal del día): más operaciones, más potencia.
5. **ES y YM como selección triplica la búsqueda**. → se elige sólo en NQ (donde SOM vive); ES y YM son acuerdo entre fuentes (descriptivo).
6. **Sin regla para combinar**: si dos mejoras de mecanismos distintos sirven, la combinación es otra hipótesis. → se declara ahora: la
   combinación de las dos mejores de **categorías distintas** entra como una finalista más.

## 5. Plan definitivo (v1) — SOM
- **Base:** SOM `sin_finde` (la de fábrica que cierra el viernes 15:55 NY; la del holdout).
- **14 variantes (una perilla por vez):**
  | Categoría | Variante | Mecanismo |
  |---|---|---|
  | Frecuencia | `rotar` | Cada día una señal nueva; más n y menos exposición a una idea vieja |
  | Salida | `trail_desde_0` / `trail_desde_1R` | Proteger antes vs dejar respirar |
  | Salida | `trail_ema60` / `trail_ema240` | Trailing más rápido vs dejar correr (palanca de salida) |
  | Stop | `stop_6atr` / `stop_10atr` | Stop más chico (más R por op, más fricción) vs más grande |
  | Señal | `ema6` / `ema24` | Lectura más rápida vs más lenta del impulso de apertura |
  | Entrada | `entrada_1000` | Esperar a que el primer impulso se confirme (cierre de la vela de las 09:55) |
  | Contexto | `franklin_no_en_contra` | No operar contra el sesgo NY vs Londres y VWAP (funcionó como filtro de T) |
  | Contexto | `noche_no_baja` | Excluir noches quietas (F-ASIA-NQ-NOCHE-MOVIDA) |
  | Contexto | `sin_gap_grande` | Excluir |gap| ≥ 0,5 ATR20 (el impulso puede ser sólo el gap) |
  | Riesgo | `cierre_diario` | Ya medida (`eod`); sirve de referencia de riesgo |
- **Elección (años pares 2012, 2014 … 2026):** elegibles las que tengan fricción ≤ 0,08 R y no menos años positivos que la base; se congelan las
  **3 de mayor t mensual** y, si son de categorías distintas, la combinación de las dos primeras (≤ 4 finalistas).
- **Confirmación (años impares 2013 … 2025):** diferencia mensual variante − base > 0 con p < 0,10 (bootstrap por mes), **BH q 0,10 sobre las
  finalistas**, y R de la variante > 0. Se informan ES/YM y la ventana reciente (ago-25 → sep-26).
- **Salida:** la ganadora (si hay) pasa al forward como **SOM v2** en paralelo; la base sigue. Contador global: 14 + 4.

## 6. Repetición en otras estrategias (después de SOM, con lo aprendido)
Se aplica donde el valor esperado lo justifica: (a) la regla tiene ventaja confirmada o casi, (b) tiene perillas de mecanismo **no exploradas**,
y (c) hay datos para elegir y confirmar por separado. Triage previsto: **T de FundedSync** (la más sólida; sus salidas por objetivo y a las
15:30 son la palanca de salida sin probar), **Franklin** (ya pasó por 32 variantes sin mejora: sólo se le prueba lo nuevo que aprenda SOM),
**Cartera B / v2** (mejoras de cartera ya hechas; sólo si SOM deja una palanca transferible).

## 7. Resultado SOM (`SOM_MEJORAS.json`, `tools/mejora_som.py`): **ninguna variante mejora a la base**
| Variante | t mes pares | t mes impares | R/mes impares | años + (pares / impares) | ops/mes | DD (R) |
|---|---|---|---|---|---|---|
| **base (sin_finde)** | **3,26** | **2,05** | **0,93** | 8/8 · 5/7 | 18,8 | −20,9 |
| noche_no_baja | 3,55 | 2,74 | 0,90 | 7/7 · 5/7 | 12,1 | −16,4 |
| trail_ema60 | 3,39 | 1,90 | 0,76 | 7/8 · 5/7 | 19,4 | −17,2 |
| stop_6atr | 2,80 | 1,54 | 0,83 | 7/8 · 6/7 | 19,8 | −24,2 |
| ema6 / ema24 | 2,83 / 2,43 | 1,86 / 2,00 | 0,92 / 0,90 | 7/8 | 18,8 | −21 / −25 |
| rotar | 2,56 | 1,45 | 0,64 | 7/8 · 4/7 | 21,1 | −32,7 |
| trail_desde_0 / 1R | 2,87 / 2,45 | 1,79 / 0,85 | 0,69 / 0,44 | 7/8 | 20,4 / 16,4 | −16 / −29 |
| trail_ema240 | 2,04 | 1,41 | 0,61 | 6/8 | 17,3 | −22,5 |
| stop_10atr | 2,26 | 1,30 | 0,49 | 6/8 | 17,4 | −25,5 |
| sin_gap_grande | 3,02 | 1,47 | 0,58 | 6/8 | 14,2 | −23,9 |
| entrada_1000 | 1,78 | −0,22 | −0,07 | 6/8 | 15,9 | −29,2 |
| cierre_diario (ref.) | 3,00 | 1,27 | 0,51 | 7/8 | 21,0 | −28,4 |

Por la regla declarada la única elegible fue `franklin_no_en_contra`, que resultó **idéntica** a la base: el filtro nunca actúa porque
cuando NY está arriba del máximo de Londres y del VWAP a las 09:34, el cierre M5 siempre está arriba de la EMA12 (crosstab 0 conflictos en
3.282 operaciones). No es un error del código: las dos señales están anidadas. Sin ganadora: **SOM sigue con la base de fábrica**.

## 8. Lecciones (alimentan la repetición)
- **L1 Meseta**: las 14 vecinas de una perilla siguen positivas (t mensual 1,8–3,5 en pares): la base no es un pico. La configuración de
  fábrica ya está cerca del óptimo; **ajustar parámetros no paga**.
- **L2 Dejar correr gana a la frecuencia**: rotar (más operaciones) baja el t y duplica el drawdown: cortar la posición vieja corta tendencias.
- **L3 El efecto está en los primeros 5 minutos**: entrar a las 10:00 lo mata (impares −0,07 R/mes).
- **L4 La noche movida no agrega ganancia pero baja el riesgo**: misma ganancia mensual con 35 % menos operaciones y menos drawdown (−16 vs
  −21 R). Es una mejora de **eficiencia de riesgo** (útil en prop), no de rentabilidad; queda como pista, no se elige (no estaba en los criterios
  de elección, que priorizan R/mes).
- **L5 Señales anidadas**: SOM y Franklin miran la misma información de la apertura; apilar uno como filtro del otro no agrega nada.

## 9. Repetición: triage con las lecciones
| Estrategia | ¿Vale? | Por qué |
|---|---|---|
| **T (FundedSync)** | **Sí** | Ventaja confirmada (holdout por regla del acta); 1.143 de 2.703 salidas son STOP pero 339 TARGET y 652 «Conditional 15:30»: la palanca de salida (L2, F-SALIDA-TECNICA) nunca se le probó. Perillas de mecanismo no exploradas. |
| Franklin | No | Ya pasó 32 variantes sin mejora; L5 dice que su información es la de SOM; la única transferencia nueva (L4) baja frecuencia en una regla de pocas operaciones. |
| Cartera B (Z, R) | No | Evidencia fuera de muestra mínima (R 5 operaciones); mejorar lo que no está confirmado es optimizar ruido. |
| Cartera v2 | No | Ya se mejoró (M1, M3, A1, A2); sus reglas corren en Kaggle sobre ticks y la palanca de salida ya se midió en los cubos. |

## 10. Plan T (pre-registro, misma metodología; puntaje en puntos por mes porque T usa su propio stop y 1 contrato)
Variantes (una perilla, `correr_modulo("T", ..., **cfg)`): `sin_objetivo` (objetivos a 100 R: se mantiene hasta su stop/cierre), `sin_1530`
(sin la salida condicional de las 15:30), `salida_libre` (las dos), `stop_x1.0` y `stop_x1.5` (multiplicador del rango de apertura; base
1,25), `noche_no_baja` (L4). Elección en años pares (t de los puntos netos por mes; elegible si no tiene menos años positivos que la base),
3 finalistas + combinación de categorías distintas; confirmación en impares (diferencia mensual vs base, bootstrap por mes, BH q 0,10).
Contador: 6 + 4.

## 11. Resultado T (`T_MEJORAS.json`, `tools/mejora_t.py`): **ninguna variante mejora a la base**
| Variante | t mes pares | t mes impares | pts/mes impares | años + | ops/mes | DD (pts) |
|---|---|---|---|---|---|---|
| **base** | **4,08** | **4,19** | **129** | 5/7 · 4/6 | 18,8 | −840 |
| noche_no_baja | 4,28 | 2,87 | 69 | 6/7 · 4/6 | 12,7 | −722 |
| sin_1530 | 4,01 | 3,41 | 108 | 5/7 · 3/6 | 18,8 | −912 |
| stop_x1.5 / x1.0 | 3,76 / 3,53 | 3,59 / 2,96 | 108 / 85 | 5/7 | 18,8 | −1.020 / −951 |
| sin_objetivo | 3,58 | 3,61 | 96 | 5/7 | 18,8 | −1.095 |
| salida_libre | 3,47 | 2,75 | 88 | 5/7 | 18,8 | −1.008 |
| noche_no_baja + sin_1530 | 4,18 | 2,05 | 49 | 6/7 | 12,7 | −841 |
Finalistas (noche, sin_1530, stop_x1.5 y la combinación): todas **peores** que la base en impares (p ≥ 0,97). T se queda con la de fábrica.

- **L6 La palanca de salida no es universal**: sirve donde la salida técnica es rápida (S, W de FundedSync), pero en T el objetivo y la salida de
  las 15:30 son parte del diseño: quitarlos baja la ganancia y sube el drawdown.
- **L7** (con L1): en las dos reglas confirmadas, las vecinas de una perilla son peores o iguales. Lo que queda para subir la rentabilidad
  **no está dentro de cada regla sino en la cartera** (criterio C5): sumar reglas descorrelacionadas.

## 12. Cartera (C5): v2 + SOM (pre-registro, descriptivo; decide el forward)
SOM `sin_finde` a **1 MNQ** (stop mediano ≈ 8 × ATR M5) junto a la v2 (A1, A2, M1, M3), ventana común 2025-08-05 → 2026-09-29 (la de la
cartera): USD, t, drawdown y prop (50K arrastrada, fija 3.500, fija 5.000) con media contraída y media 0. Regla de uso: la combinación entra
al forward como versión paralela si en la 50K su quema ≤ 10 % y su probabilidad de pasar ≥ la v2 sola. Contador: 1.

## 13. Resultado cartera v2 + SOM (`CARTERA_V2_SOM.json`; ago-25 → sep-26, 301 sesiones; pasa / quema con media contraída)
| | USD | t diario | DD | 50K arrastrada | fija 3.500 | fija 5.000 |
|---|---|---|---|---|---|---|
| v2 | 24.210 | 5,35 | −1.214 | 63 % / 3 % | 91 % / 0,1 % | 91 % / 0 % |
| SOM 1 MNQ | 15.094 | 1,96 | −2.967 | 43 % / 52 % | 70 % / 15 % | 72 % / 6 % |
| **v2 + SOM** | **39.305** | 4,32 | −2.295 | 68 % / **30 %** | **94 % / 3,6 %** | **96 % / 0,9 %** |
Por la regla declarada (50K) **no entra**: la quema sube a 30 %. En cuenta de drawdown fijo la suma sí mejora (pasar 91 → 94–96 % con quema
≤ 3,6 %), igual que con la Cartera B: el límite es el tipo de cuenta, no la combinación. SOM a 1 MNQ en USD es mucho más ruidoso que en R
(t 1,96 vs t mensual ≈ 3 en R) porque el riesgo en dólares varía con el ATR: el tamaño por R constante es la hipótesis siguiente (no corrida).

## 14. Balance del programa
- Criterios y método quedan como estándar para mejorar reglas (este documento).
- **SOM y T: sin mejora** dentro de la regla (meseta, L1/L7); salir del diseño de fábrica empeora (L2, L3, L6).
- **Lo que sí mejora la rentabilidad es la cartera en la cuenta correcta**: v2 + SOM y v2 + Cartera B en cuentas de drawdown fijo. La elección de
  firma/cuenta es de Nico; con sus reglas reales se repite la simulación.
- Pistas abiertas: noche no baja como filtro de riesgo (SOM, T); SOM con tamaño por R constante.

## 15. Ronda 2 (pre-registro, 2026-11-16): «aplicalo a las otras que lo valgan»
Con L1–L7 la mejora ya no se busca en las perillas de la señal sino en **cómo se arriesga** (tamaño) y **cómo se combinan** (cartera).
Triage completo:
| Estrategia | ¿Vale? | Qué se le aplica / por qué no |
|---|---|---|
| SOM | Sí | **Tamaño** (pista abierta): su stop va de 5 a 813 pts (mediana 68); a 1 contrato el riesgo en USD varía ×100 y el t en USD (1,96) queda muy por debajo del t en R. |
| T | Sí | **Tamaño**: stop variable (rango de apertura × 1,25). |
| Franklin | Sí (sólo tamaño) | Señal ya explorada (32 variantes); su stop (rango 09:30–10:00) es variable. |
| Z, R (Cartera B) | No | 2–3 operaciones por mes y evidencia fuera de muestra mínima; el contexto de noche de Z ya se miró en estos datos (tanda 4) → sólo forward. |
| Reglas de la v2/v3 | No | Su celda salió de una grilla ya medida (cambiar la celda es re-elegir); tamaño (M3), fricción (M1), comisión (A1) y pesos (A2) ya se probaron. |
| PREAPERTURA-ES, noche como filtro | No acá | Su dato ya se vio: lo decide el forward (T5b). |
| **Cartera SOM + T + Franklin** | Sí | Criterio C5: son las tres reglas con historia 2012–2026; se prueba cómo pesarlas. |

### R2-A. Tamaño por regla (SOM NQ, T NQ, Franklin NQ+ES)
Variantes: `fijo` (1 contrato, base) · `R_const` (contratos ∝ 1/riesgo: todas las operaciones arriesgan lo mismo) · `raiz` (∝ 1/√riesgo,
intermedio; F-STOP-CORTO-ES-FRICCION halló que el contrato fijo superaba al riesgo fijo en la cartera v2). Tamaño continuo (el t es
invariante a la escala; la conversión a micros enteros se hace al operar). Puntaje: t del resultado mensual; también drawdown en múltiplos
del riesgo medio y años positivos. Elección en años pares, confirmación en impares: diferencia mensual de t no se testea directo, se exige
**t mensual mayor que el de `fijo` en impares y años positivos ≥**; con 3 reglas × 2 variantes = 6 pruebas, BH q 0,10 sobre la diferencia
mensual normalizada (cada serie dividida por su desvío en pares).
### R2-B. Pesos de la cartera SOM + T + Franklin (con el tamaño que gane en R2-A, o `fijo`)
`igual_contrato` (1 de cada una) · `igual_riesgo` (cada regla al mismo riesgo medio por operación) · `paridad_vol` (peso ∝ 1/desvío mensual,
estimado en pares). Puntaje: t mensual de la suma y drawdown; confirmación en impares; correlaciones mensuales informadas. Descriptivo con
regla de uso: la mejor en impares pasa como propuesta de pesos para el forward (no reemplaza nada).
Contador: R2-A 6, R2-B 2.

### Enmienda R2-1 (2026-11-16): primera corrida de T DESCARTADA (sesgo de futuro en el riesgo)
El motor de T devuelve en `stop_price` el stop ACTIVO al salir, que se mueve a la entrada cuando la operación llega a su disparador: las
ganadoras parecían de riesgo ≈ 0 (piso 4 pts) y el tamaño ∝ 1/riesgo las sobreponderaba a posteriori (t mensual 4 → 9, falso). Se reconstruye el
riesgo inicial exacto de `submit_entry`: clip(rango 09:30–09:45 × 1,25, 2, 100) pts, y se relanza. Es también la causa de la «métrica R absurda»
de T vista en la cadena de FundedSync. SOM y Franklin no cambian (sus stops son los iniciales); sus cifras de la corrida descartada coinciden.
Efecto colateral: el tamaño de T a 200 USD de la tanda 4 (C2) usó la mediana de ese riesgo sesgado (T sobredimensionada en esa versión); la
Cartera B (1 MNQ fijo) no se afecta.

## 16. Resultado ronda 2 (`RONDA2.json`, `tools/mejora_ronda2.py`, con el riesgo inicial de T corregido)
**R2-A Tamaño: el contrato fijo gana en las tres.**
| Regla | fijo: t mes pares / impares | R_const | raíz | p (vs fijo, impares) |
|---|---|---|---|---|
| SOM | 2,83 / **2,98** | 3,38 / 2,05 | 3,28 / 2,64 | 0,77 / 0,55 |
| T | 3,98 / **4,13** | 2,99 / 2,59 | 3,76 / 3,65 | 0,92 / 0,76 |
| Franklin | 1,38 / **1,94** | 0,07 / 0,84 | 1,09 / 1,64 | 0,89 / 0,85 |
Confirma F-STOP-CORTO-ES-FRICCION en tres reglas nuevas: igualar el riesgo por operación pone más contratos en los stops chicos, que es donde la
fricción y el ruido pesan más. **Se queda el contrato fijo** (en SOM la pista de la ronda 1 queda refutada).

**R2-B Pesos de SOM + T + Franklin (contrato fijo):** igual_contrato t impares 3,80 (654 USD/mes por micro), igual_riesgo 3,75, paridad_vol
3,74: **los pesos no importan** (las tres reglas ya tienen riesgos parecidos a 1 micro). La suma **no supera el t de T sola** (4,13): SOM y
Franklin tienen menos t y correlación mensual 0,20–0,35 con T. Suman ganancia (más USD por mes con drawdown de la misma escala), no eficiencia.

## 17. Balance final del programa (rondas 1 y 2)
| Palanca | SOM | T | Franklin | Lección |
|---|---|---|---|---|
| Perillas de señal/entrada | no | — | no (32 var.) | L1, L3, L5 |
| Salida | no | no (empeora) | no | L2, L6 |
| Stop | no | no | — | L1 |
| Contexto (noche) | baja riesgo, no gana | baja riesgo, pierde | — | L4 |
| Tamaño | fijo | fijo | fijo | L8 |
| Pesos de cartera | indistintos | | | L9 |
- **L8**: el contrato fijo le gana al riesgo constante en todas las reglas medidas (cartera v2 y ahora SOM, T, Franklin).
- **L9**: entre reglas de riesgo parecido, los pesos no mueven el t; lo que mueve la rentabilidad es **qué reglas** se suman y en **qué cuenta**.
- **Integridad**: el `stop_price` de T es el stop final, no el inicial (corregido en el análisis; el motor de FundedSync no se tocó).
- Conclusión para la siguiente etapa: las reglas confirmadas ya están en su forma eficiente; el aumento de rentabilidad viene de **sumar reglas
  nuevas descorrelacionadas que confirmen en forward** y de la **cuenta** (pendiente con Nico). El método queda escrito para la próxima regla.
