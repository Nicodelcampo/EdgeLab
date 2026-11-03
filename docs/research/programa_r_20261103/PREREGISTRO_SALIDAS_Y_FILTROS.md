# Pre-registro: políticas de salida y filtros comunes para mejorar el R por operación (2026-11-03)

Estado: VIGENTE, registrado antes de ver ninguna trayectoria. Programa: `PROGRAMA_R.md` (punto 3). Referente: `docs/NORTH_STAR.md`, cuerpo
sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF3: datos de desarrollo ya usados, sin holdout.

## Idea
Las reglas no tienen potencia para confirmarse una por una. **Una misma política de salida aplicada a las 8 reglas de la v5 usa todas sus
operaciones juntas** (≈ 1.000 en DESC + réplica): la potencia es la del conjunto, no la de cada regla. Lo mismo vale para un filtro.

## Datos
Etapa `TRAYECTORIAS` (`tools/trayectorias_v5.py`). Por operación, el camino vela a vela en R (favorable, adverso y cierre) desde el
llenado hasta 240 velas o el fin de la sesión, más la fricción en R y las variables de la celda. DESC para elegir, réplica para confirmar.

## Motor (`tools/salidas_r.py`)
- **Granularidad de vela, conservador:** si en una vela se alcanzan el stop y la salida favorable, gana el stop.
- **Las salidas por tiempo usan el cierre de la vela.**
- **Si una política achica el stop, el R se mide contra el riesgo nuevo.** El tamaño de la posición cambia, y si no, se estaría inflando el R.
- **Fricción** = fricción en R × (riesgo original / riesgo nuevo).
- **Línea base:** la regla tal cual, simulada con el mismo motor (stop −1R, su objetivo en R y el fin del camino). Así ninguna política
  le gana a la base por diferencias de granularidad.

## Familia de políticas (fija, 28 en total, además de la base; lista exacta en `salidas_r.politicas()`)
| Tipo | Valores |
|---|---|
| Stop por tiempo: cierra en la vela N | N ∈ {15, 30, 60, 120} |
| Objetivo fijo en R, en lugar del de la regla | T ∈ {0,5; 1; 1,5; 2; 3} |
| Break-even: el stop pasa a 0 cuando la ganancia máxima llega a b | b ∈ {0,5; 1} |
| Trailing: con ganancia máxima ≥ a, stop en (máximo − d) | (a, d) ∈ {(1; 0,5), (1; 1), (2; 1)} |
| Stop más corto, en fracción del original | s ∈ {0,5; 0,75} |
| Combinaciones | objetivo T con break-even en 0,5, para T ∈ {1; 1,5; 2}; stop por tiempo N ∈ {30, 60} con break-even en 1; trailing (1; 0,5) con stop por tiempo 120 |

Además, objetivo T ∈ {1; 2} cada uno combinado con s ∈ {0,5; 0,75}, y stop por tiempo N ∈ {30, 60} combinado con objetivo 1,5.

## Filtros (fijos)
- **Franja horaria de entrada:** Asia (22–07 UTC), Europa (07–13:30) y EE.UU. (13:30–22).
- **Lado:** compra o venta.

Un filtro excluye una franja o un lado completos, para todas las reglas.

## Decisión
1. **DESC, agrupando las 8 reglas:** para cada política, la diferencia emparejada por operación contra la base, con IC90 por bootstrap de
   sesiones. Se elige **una** política: la de mayor cota inferior del IC90 de esa diferencia. Lo mismo para **un** filtro.
2. **Réplica, agrupada:** una sola prueba por la política elegida y otra por el filtro. Diferencia > 0 con p < 0,05 a una cola. Holm sobre las
   2 pruebas.
3. **Confirmada:** pasa a las variantes de la v5 (punto 4 del programa) con regla congelada. Se sigue sólo forward, desde sesiones nuevas,
   en papel y con e-proceso.
4. **No se elige por regla:** una política distinta por regla reabre el problema de potencia. Por regla sólo se informa.

## Cómo podría refutarse
Que ninguna política ni filtro mejore la base en réplica, o que la mejora dependa de una sola regla. Se informa la mejora por regla y la
mejora sin la regla de mayor peso.

## Registro
hasta 35 en DESC (28 políticas + 5 filtros) y 2 en réplica: `programa_r/salidas_filtros/20261103` en `TRIAL_REGISTRY_GLOBAL.jsonl`.

## Resultado (2026-11-03), en `SALIDAS_RESULTADO.json` (decisión) y `SALIDAS_REP_DESCRIPTIVO.json` (descriptivo)
**Validación del motor:** reproduce el R real de las reglas. Correlación por operación 0,99 en DESC y 0,98 en réplica; media agrupada
+0,236 contra +0,232 real en DESC y +0,104 contra +0,118 en réplica.

**Decisión pre-registrada: nada se confirma.**
- **Política elegida en DESC:** objetivo 2R con stop 0,75. En DESC da +0,079R contra la base, con IC90 [−0,018; +0,172] (no excluye 0).
  En réplica da +0,008R (p 0,46, Holm 0,92): **no confirma**.
- **Filtro elegido:** sacar Europa. En DESC −0,013R; en réplica −0,034R: **no confirma**.
- **Todos los filtros empeoran el R en DESC.** Las reglas ganan en todas las franjas y en los dos lados: sacar una parte saca ganancia.

**Lo que sí se repite en DESC y en réplica** (descriptivo; no es una prueba nueva, pero tiene el mismo signo en las dos ventanas):

| Política | DESC | Réplica |
|---|---|---|
| Cerrar a las 15 velas | −0,17 | −0,09 |
| Cerrar a las 30 velas | −0,14 | −0,07 |
| Cerrar a las 60 velas | −0,10 | −0,04 |
| Objetivo de 0,5R | −0,14 | −0,09 |
| Break-even + cierre a las 30 velas | −0,14 | −0,08 |
| Trailing (las tres variantes) | −0,02 a −0,05 | −0,01 a −0,03 |

**Lectura (idea transferible, negativa): no cortar las ganancias.** Salir antes por tiempo, por objetivo chico, por break-even o por
trailing le resta R a estas reglas en los dos tramos. Su salida natural ya es casi óptima entre las variantes probadas.

Lo único con signo positivo en los dos tramos es ampliar el objetivo a 2R con un stop más corto: +0,08 / +0,05 (stop 0,5) y
+0,08 / +0,01 (stop 0,75). Sin significancia. Queda como pista para probar en familias nuevas, no se aplica a la v5.
