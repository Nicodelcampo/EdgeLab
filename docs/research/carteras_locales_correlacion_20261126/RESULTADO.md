# CARTERAS-LOCALES-CORRELACION: las intradía son casi la misma cartera; la interdía y C2_VZ son las que diversifican (resultado, 2026-11-26)

Estado: RESULTADO — descriptivo, pre-registrado (`PREREGISTRO.md`), 1 lectura contada.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Archivos:** `RESULTADO.json`, `SERIES_DIARIAS.csv.gz`, `CURVAS_CAPITAL.png`. Herramienta `tools/carteras_locales_correlacion.py`.

Episodios: R o USD por mes por bloque A5, en la tabla de abajo.

## Correlación mensual

| 2019-07 → 2026-09 | INTRADIA8 | INTERDIA3 | C2VZ_2 | CANASTA_TRZQ |
|---|---|---|---|---|
| INTRADIA8 | 1 | 0,25 | −0,12 | **0,60** |
| INTERDIA3 | | 1 | **0,66** | 0,03 |
| C2VZ_2 | | | 1 | −0,28 |

| 2025-01 → 2026-09 | INTRADIA8 | INTERDIA3 | C2VZ_2 | P_OPT_SF_v2 | CANASTA_TRZQ |
|---|---|---|---|---|---|
| INTRADIA8 | 1 | 0,25 | −0,16 | **0,65** | 0,48 |
| INTERDIA3 | | 1 | 0,60 | 0,43 | −0,10 |
| C2VZ_2 | | | 1 | 0,10 | −0,33 |
| P_OPT_SF_v2 | | | | 1 | **0,63** |

Correlación diaria 2025–26: INTRADIA8–P_OPT 0,72; INTRADIA8–CANASTA 0,72; P_OPT–CANASTA 0,67.

## Por bloque A5 (todas las particiones; R/mes o USD/mes con 1 micro, t mensual, % de meses positivos)

| Cartera | DESC | REP | HOLDOUT | TERMINAL | Todo |
|---|---|---|---|---|---|
| INTRADIA8 (USD) | +1.622, t 3,48, 65 % | +534, t 0,94, 56 % | +1.309, t 2,97, 59 % | — | +1.362, t 4,50, 63 % |
| INTERDIA3 (USD) | +501, t 2,09, 71 % | +792, t 2,01, 69 % | +495, t 1,59, 73 % | — | +574, t 3,31, 70 % |
| C2VZ_2 (USD) | +142, t 0,96, 63 % | +644, t 2,78, 62 % | +325, t 1,46, 73 % | — | +286, t 2,57, 66 % |
| P_OPT_SF_v2 (R, desde 2025) | +8,15, t 2,84, 73 % | +8,10, t 2,01, 100 % | +8,30, t 1,90, 67 % | +9,35 (2 meses) | +8,58, t 4,59, 78 % |
| CANASTA_TRZQ (R) | +6,01, t 4,82, 76 % | +4,69, t 2,60, 75 % | +4,92, t 2,77, 77 % | — | +5,64, t 6,28, 72 % |

El TERMINAL sólo está para P_OPT_SF_v2, cuya campaña ya lo había abierto. Las demás no lo tienen abierto y no se calculó.

## Lectura
- **INTRADIA8, P_OPT_SF_v2 y CANASTA_TRZQ son variaciones de lo mismo:** las tres usan T, R, Z, V y RQ5 en NQ, con correlación de
  0,6–0,7. Sumarlas en cuentas distintas no diversifica: es más tamaño de la misma apuesta.
- **INTERDIA3 y C2VZ_2 sí diversifican a las intradía** (correlación de −0,33 a 0,25). Son las únicas que lo hacen. INTERDIA3 y C2VZ_2
  se pisan entre sí (0,60–0,66), porque C2VZ es parte de INTERDIA3.
- **Todas se sostienen en los meses HOLDOUT de A5,** con R o USD por mes parecido al de DESC. La más pareja es CANASTA_TRZQ (t 2,77 en
  HOLDOUT). INTRADIA8 tiene la REP floja (t 0,94).
- **Para repartir cuentas:** una intradía (cualquiera de las tres) más INTERDIA3 es la combinación que reduce el riesgo conjunto.

## Adenda: futuros intradía contra CFD swing (`ADENDA_FUT_VS_CFD.md`)
Gráfico: `CURVAS_FUT_VS_CFD.png`. Datos: `FUT_VS_CFD.json`.

| Cartera | DESC | REP | HOLDOUT | Todo | Caída máx. |
|---|---|---|---|---|---|
| Futuros intradía (INTRADIA8, USD con 1 micro) | +1.622/mes, t 3,48 | +534, t 0,94 | +1.309, t 2,97 | +1.362, t 4,50, 63 % meses + | −13.964 USD |
| CFD swing (C2_VZ + C2_EVRP ES/NQ + Turtles GC, R) | +0,34/mes, t 1,00 | +1,73, t 2,46 | +1,13, t 1,57 | +0,76, t 2,60, 58 % meses + | −18,5 R |

Correlación mensual entre las dos: −0,22.

Episodios: la cartera CFD swing tuvo su peor tramo en 2022 (de ≈ +35 a +17 R) y la intradía, en 2026 desde junio.

**Lectura:**
- La intradía tiene más ventaja (t 4,5) y se sostiene en HOLDOUT (t 2,97).
- La CFD swing es más floja (t 2,6), con DESC casi plano y HOLDOUT positivo sin significancia (t 1,57). Su valor principal es que va al
  revés de la intradía (−0,22).
- La CFD se midió sobre precios de futuros; los costos y el horario de los CFD pueden cambiarla.

## Adenda 2: corrección de Nico, sin Turtles; las dos carteras del 25-nov (`EdgeLabCartera`, presets Intradía e Interdía)
Gráfico: `CURVAS_INTRADIA_VS_INTERDIA.png`. Datos: `INTRADIA_VS_INTERDIA.json`. Las dos en USD con 1 micro, de 2019-07 a 2026-09.

| Cartera | DESC | REP | HOLDOUT | Todo | Caída máx. |
|---|---|---|---|---|---|
| Intradía (MNQ: T, R, Z, V, RQ5, Franklin; MES: RQ5, ES5N) | +1.622, t 3,48 | +534, t 0,94 | +1.309, t 2,97 | +1.362, t 4,50, 63 % meses + | −13.964 |
| Interdía / swing (MNQ: SOM sin finde, C2_VZ; MES: C2_VZ) | +501, t 2,09 | +792, t 2,01 | +495, t 1,59 | +574, t 3,31, 70 % meses + | −10.896 |

Correlación mensual: +0,25.

Episodios: la interdía tuvo su peor tramo en 2022; la intradía, desde junio de 2026.

La adenda anterior (con Turtles) queda reemplazada por ésta.

## Adenda 3: estrategias candidatas en MNQ y las 8 mejores fuera de NQ (`ADENDA_MNQ_Y_OTROS_ACTIVOS.md`)
Gráficos: `CURVAS_MNQ_POR_ESTRATEGIA.png`, `CORR_MNQ.png` y `CURVAS_TOP8_OTROS_ACTIVOS.png`. Datos: `MNQ_Y_OTROS.json`.
USD con 1 micro, 2019-07 → 2026-09, todas las particiones.

Episodios: las caídas máximas por estrategia, en las tablas.

| MNQ | USD/mes | t mensual | % meses + | Caída máx. |
|---|---|---|---|---|
| T | +404 | 5,12 | 67 % | −2.037 |
| R | +189 | 3,62 | 60 % | −1.591 |
| Z | +90 | 2,71 | 61 % | −1.521 |
| C2_VZ | +204 | 2,67 | 67 % | −4.670 |
| V | +180 | 2,52 | 61 % | −3.220 |
| RQ5 | +221 | 2,41 | 63 % | −6.784 |
| SOM sin finde | +288 | 2,22 | 59 % | −9.088 |
| Franklin | +147 | 2,20 | 60 % | −4.387 |
| N | +104 | 2,10 | 53 % | −2.707 |
| A20 | +194 | 1,92 | 45 % | −6.345 |
| ES5N | +137 | 1,80 | 52 % | −5.741 |
| S | +152 | 1,12 | 56 % | −8.659 |
| C2_EVRP | +86 | 0,63 | 54 % | −9.816 |

**Correlación mensual en MNQ:**
- La mayoría entre −0,3 y +0,4.
- Pares más altos: RQ5–ES5N 0,62, RQ5–Franklin 0,58, T–R 0,50 y Franklin–ES5N 0,47.
- Cubren a las demás: C2_VZ, negativa con T, R y Z (−0,27 a −0,34), y C2_EVRP, −0,45 con A20.

| Fuera de NQ (las 8 primeras por t) | USD/mes | t mensual | % meses + | Caída máx. |
|---|---|---|---|---|
| C2_VZ ES | +82 | 2,10 | 62 % | −2.672 |
| RQ5 ES | +87 | 1,44 | 52 % | −3.285 |
| ES5N ES | +44 | 1,04 | 53 % | −3.185 |
| T ES | +52 | 1,03 | 56 % | −3.045 |
| C2_EVRP ES | +47 | 0,75 | 54 % | −5.438 |
| Franklin ES | +22 | 0,59 | 53 % | −2.026 |
| RQ5 GC | +29 | 0,43 | 39 % | −4.968 |
| RQ5 RTY | −8 | −0,23 | 46 % | −3.217 |

**Lectura:**
- Fuera de NQ, sólo C2_VZ en ES pasa t 2. Las demás son débiles o nulas.
- Las de RTY, YM y GC no aparecen en el top salvo RQ5 GC y RQ5 RTY, que son ≈ 0.
- Lo diversificable está en NQ, entre estrategias, más que en otros activos.
