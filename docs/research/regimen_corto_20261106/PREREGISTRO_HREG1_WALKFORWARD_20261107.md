# Pre-registro — H-REG-1 sobre la regla que produjo el trío Q3

Estado: PROVISIONAL
Fecha: 2026-11-07
Familia / módulo: `CANASTA_REGIMEN` / régimen corto (`regimen_corto_20261106`)
North Star: sha256 del archivo `docs/NORTH_STAR.md` = `f8e6660fc102c1a6af95916eeddeddc1b0df6b5429cc8e3e2732888ba9cc3930`
Procedencia: parche `regimen_estructural_y_series_diarias_20261107.patch`, SHA-256 `befcd4bc85e279df254ad84c2e07d686f1708fbfa5ca30321c91889223a4c885`, aplicado sobre `foundation/f0b-compatibility-probe`. Series: `docs/research/regimen_corto_20261106/series_diarias_regimen_20261106.json`. Tablero del trío: `docs/research/regimen_corto_20261106/top3_estabilidad_diaria_q3.html`.

Este archivo se escribe **antes** de correr el walk-forward. No promueve estrategias. No abre el holdout `>= 2026-10-01`.

## 1. Qué se vio y qué no se va a volver a medir mal

El tablero Q3 (`2026-07-01 .. 2026-09-30`) muestra tres estrategias: `ABSORCION-NQ-3R`, `COMPRESION-NR-GC`, `PREAPERTURA-ES`. Reconstruir el ranking sobre `series_cand` recupera exactamente ese trío, y no hace falta inventar umbrales:

- Universo visible del ranking: las 16 con `grupo = confirmada_q3` (hay además 10 `candidata_rechazada` en el mismo archivo).
- Puntaje: **R neto total** del trimestre, no R/op ni t.
- Desempate de familia: como máximo una celda por `(familia, instrumento)`. Eso saca a `ABSORCION-NQ-2R` (27,41 R en Q3, segunda del ranking crudo) porque `ABSORCION-NQ-3R` es la misma familia en NQ y suma 33,04 R.
- Quedan, en orden: `ABSORCION-NQ-3R` (33,04 R, 50 ops, 54,5 % días +, t diario 2,34), `COMPRESION-NR-GC` (21,91 R, 57 ops, 52 % días +, t 1,64), `PREAPERTURA-ES` (20,26 R, 25 ops, 44 % días +, t 1,47).

Un piso de t ≥ 2 o de 50 % de días positivos **no** produce este trío: dejaría afuera a `PREAPERTURA-ES` y, con t ≥ 2, también a `COMPRESION-NR-GC`. La fricción (0,093 / 0,082 / 0,100 R) tampoco es un filtro: hay confirmadas con fricción más baja que no entraron. El «0,038 ortogonal» del tablero es un KPI escrito después de elegirlas, no la regla de entrada. `COMPRESION-NR-GC` es negativa en la muestra completa (−2,94 R, 293 ops) y sólo se ve bien en este trimestre.

Eso es una foto del trimestre ya observado. Medir «cuántas veces un régimen de 3 meses siguió al 4º» **sólo sobre estas tres** repite la selección. Este pre-registro congela la misma regla y la corre hacia atrás sobre el pool entero.

Prior ya medido, que este test no reabre:

- CANASTA-REGIMEN-1 (`docs/research/canasta_regimen_20261026/RESULTADO_PERSISTENCIA.md`): en la grilla U1, 2023–mar-2026, ρ(0) − ρ(12) ≈ 0. Lo que persiste es calidad estática. Las canastas top-k por racha no pasaron el umbral.
- REGIMEN_ETAPA0 (`docs/research/REGIMEN_ETAPA0_RESULTADOS_20261006.md`): la eficiencia no persiste; la amplitud sí. Eso es H-REG-2 y queda fuera de esta corrida.

## 2. Hipótesis

H-REG-1, esta regla: el R neto de los últimos W meses, usado para elegir k = 3 celdas del pool de abajo, predice el R/op del mes siguiente por encima de una canasta del mismo tamaño elegida al azar y por encima de una canasta elegida por calidad estática.

Justificación económica: si el entorno que explota una familia dura más que la ventana de selección, rotar hacia la racha reciente sube el R/op. Si la racha es ruido o calidad fija, no lo sube.

## 3. Pool

Pool primario: las **26** series de `series_cand` (16 confirmadas + 10 rechazadas). La etiqueta `confirmada_q3` **no** es filtro de elegibilidad: se asignó con información que incluye los mismos meses que el walk-forward va a puntuar.

No entra `series_p4` (21 celdas del diagnóstico P4). Salieron de otro procedimiento (`P4_DESC_CONGELADO_MAS_REGIMEN_OOS`) y mezclarlas cambiaría la población. Queda como NO MEDIDO.

Cada serie ya trae el R neto diario (`celdas[día].r`, `.n`). No se recalcula fricción ni se toca el holdout.

## 4. Regla, congelada

En el cierre del último mes de W, con sesiones ya cerradas y sin usar H:

1. Elegible: al menos **8** operaciones dentro de W. Si hay menos de 3 elegibles, la ventana no se puntúa (no se imputa 0).
2. Puntaje: suma del R neto en W.
3. Como máximo una celda por `(familia, instrumento)`: se queda la de mayor puntaje.
4. Se operan las **k = 3** de mayor puntaje durante el mes H.
5. Si hay empate de puntaje, gana la que tenga más operaciones en W y, si sigue, el nombre de regla en orden lexicográfico.

Horizontes, sin solapar H. W son los meses calendario inmediatamente anteriores.

| Id | W | H | Primera H posible | Última H |
|---|---|---|---|---|
| **Primario** `W3H1` | 3 meses | el mes siguiente (el 4º) | 2025-11 | 2026-09 |
| Secundario `W2H1` | 2 meses | el mes siguiente (el 3º) | 2025-10 | 2026-09 |

La unidad de inferencia es el mes H, no la operación. Como máximo 11 ventanas en `W3H1` y 12 en `W2H1`, menos las que no lleguen a 3 elegibles. Con ese N el test puede quedar sin potencia; se publica igual el efecto y el error estándar entre ventanas. No se descarta la hipótesis por un nulo sin MDE.

## 5. Controles, mismo k y misma deduplicación

- **Aleatorio.** En cada ventana, 200 canastas de 3 celdas sorteadas entre las elegibles de esa ventana, después del paso 3 (una por familia e instrumento). El estadístico de control es la media de esas 200 en R/op de H.
- **Calidad estática.** Mismo k y misma deduplicación, pero el puntaje es el R neto acumulado desde la primera sesión de la serie hasta el último día anterior a H, no el de W.

## 6. Qué número decide

En cada mes H, R/op de una canasta = suma del R neto de sus operaciones / cantidad de operaciones. Las tres celdas se juntan en un solo pool de operaciones. No se promedia primero el R/op de cada celda.

Para cada horizonte, sobre las ventanas válidas:

- Δ_azar = R/op de la regla − R/op medio de las 200 aleatorias
- Δ_estática = R/op de la regla − R/op de la canasta estática
- t = media(Δ) / (desvío(Δ) / √n_ventanas), entre ventanas

**Decisión (sólo el horizonte primario `W3H1`).** Hay continuación por racha si Δ_azar y Δ_estática son los dos positivos y los dos tienen t ≥ 2. Si falta cualquiera de los dos, la hipótesis de esta regla no pasa.

`W2H1` se informa con la misma cuenta y **no rescata** un primario que no pasa. No se elige el horizonte después de ver el signo.

Esto no promueve `ABSORCION-NQ-3R`, `COMPRESION-NR-GC` ni `PREAPERTURA-ES`. El trimestre que las eligió es una de las ventanas del walk-forward, no una confirmación fuera de muestra. Un pase manda a otro pre-registro, con réplica no usada y el holdout todavía cerrado.

## 7. Cómo podría refutarse

Δ_azar ≤ 0 o Δ_estática ≤ 0 en `W3H1`, o t < 2 en cualquiera de los dos, con las ventanas válidas publicadas. Eso acota esta regla (top 3 por R reciente, una celda por familia e instrumento, sobre estas 26 series). No mata la idea de régimen ni H-REG-2.

## 8. Qué no mide

- H-REG-2: condicionar estas familias a amplitud realizada observable antes de operar (overnight, rango previo). Es el paso siguiente si `W3H1` no pasa, y necesita su propio pre-registro.
- Un detector que cuente continuaciones sólo sobre las 3 ganadoras.
- Pisos de t, de % de días positivos, de fricción o de correlación ρ ≤ 0,35. No son la regla que armó el trío.
- `series_p4`, la grilla U1, otras gramáticas, y cualquier sesión `>= 2026-10-01`.
- Declarar régimen estable porque jul–sep 2026 les fue bien.

## 9. Lectura barata, que no decide

Sobre las series diarias ya publicadas se puede mirar, para estas tres solas, el R/op del mes que sigue a cada bloque de 2 y de 3 meses. Sirve para ver la magnitud. No tiene el control aleatorio ni el estático, y N es el de tres series elegidas a ojo. No sustituye la sección 6.
