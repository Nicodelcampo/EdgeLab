# FundedSync en futuros, capa 2: variantes de salida, stop de catástrofe y cartera completa (resultado, 2026-11-17)

Estado: RESULTADO — pre-registro `PREREGISTRO_CAPA2.md`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Datos: `RESULTADO_CAPA2.json`, `FS_VAR_*.csv.gz`, `ATR_RTH_*.csv`, `CARTERA_*_NQ.csv.gz`. La corrida de ES de las variantes murió por memoria
(4 procesos en paralelo, sin salida) y se relanzó sola: mismo código, mismos datos.

## 1. Variantes de salida (confirmatorio en años limpios 2006–2011, NQ + ES + YM)
| Módulo | Diferencia por día (ATR) 06-11 [IC90] | 12-19 | 20-25 | Veredicto | Neto absoluto de la variante |
|---|---|---|---|---|---|
| W (sin salida por cruce de VWAP) | **+0,224 [+0,198, +0,250]** | +0,179 | +0,028 | **CONFIRMA_MEJORA** | sigue negativo: −0,04 a −0,07 ATR por día en 06-11, ≈ 0 en 20-25 |
| N (sin salida por ruptura fallida) | **+0,026 [+0,010, +0,041]** | +0,010 | +0,004 | **CONFIRMA_MEJORA** | sigue ≈ 0 o negativo |
| S (al cierre con stop duro) | +0,001 [−0,015, +0,016] | +0,010 | +0,000 | NO_CONCLUYENTE | — |
| A20 | −0,004 [−0,013, +0,005] | +0,002 | −0,000 | NO_CONCLUYENTE | — |

Las mejoras de W y N se confirman donde nadie miró, pero sólo reducen pérdidas: ninguna de las dos variantes tiene ventaja propia. La
mejora de S que la tanda 2 había visto en el CFD no se sostiene en futuros.

## 2. Stop de catástrofe de Z y R: 0,5 × ATR20 sobre la MAE (descriptivo)
Corta la peor operación a la mitad o menos y cambia poco el neto:

| Caso | Peor operación (pts) | Neto (ATR/op) |
|---|---|---|
| Z en NQ, 2020–25 | −331 → −222 | +0,133 → +0,122 |
| Z en YM, 2012–19 | −871 → −232 | — |
| R en NQ, 2020–25 | −415 → −169 | +0,185 → +0,171 |
| R en NQ, 2012–19 | — | +0,030 → +0,052 |

- En ES y YM, R decae después de 2011 con o sin stop.
- Para una cuenta de prop, la versión con stop es la única operable.

## 3. Cartera completa del vendedor (descriptivo; MNQ, filtro de noticias apagado)
| Perfil | Total 2006–2026 (USD) | Años + | Máx. drawdown cerrado (USD) | 2006–2018 | 2019–2026 |
|---|---|---|---|---|---|
| Lucid50K (fábrica) | −38.900 | 33 % | −380.700 | negativo todos los años (−13 k a −38 k) | +18 k a +85 k por año |
| Lucid25K | +67.900 | 38 % | −127.700 | negativo todos los años (−3 k a −15 k) | ≈ 0 en 2019; +5 k a +54 k por año desde 2020 |

- **Qué selecciona la cartera de fábrica:** no incluye a T, N ni Q, y con el perfil 25K tampoco a A1 ni a W.
- **Qué la sostiene:** O, R, Z, V y A20. P, W y A1 la hunden.
- Es el mismo patrón de la fricción relativa (`RESULTADO.md` §3), ahora en dólares: la cartera del vendedor es rentable sólo con la
  fricción de los últimos años.
- Su drawdown histórico es incompatible con el límite de pérdida de una cuenta Lucid de 25K.
