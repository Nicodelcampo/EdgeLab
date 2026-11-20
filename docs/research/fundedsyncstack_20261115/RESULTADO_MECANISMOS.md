# FundedSync: mecanismos, contextos y combinaciones — resultado (2026-11-16)

Estado: RESULTADO (EF2 exploración + EF3 réplica dirigida). Pre-registro `PREREGISTRO_MECANISMOS.md` (commit `9c6a905f`). Datos:
`mecanismos/MECANISMOS.json` (celdas, descriptivo, correlaciones, canasta). Operaciones de desarrollo 2020-01 → 2026-09 (el holdout no se usó).

## 1. Prueba pre-registrada de contextos: ninguna mejora confirmada
375 celdas (15 módulos × 25 niveles de 8 ejes conocidos antes de entrar). En A (2020–2023) se eligieron 18; **en B (2024–2026) ninguna pasa
BH**. 10 de 18 conservan la dirección en B; las más firmes: A20 con gap alto (B +27,9 contra +6,5 del módulo, p 0,006), A1 con gap alto
(p 0,038), R con tendencia de 60 días a la baja (p 0,037) y R entre 09:30 y 10:30 (p 0,037). Quedan como hipótesis para datos nuevos; no se
filtra ningún módulo con esto.

## 2. Mecanismos (descriptivo, 2020–2026)

### 2.1 El resultado de casi todo depende de los días de tendencia, y no se pueden anticipar con lo que se sabe a la apertura
Día de tendencia = |cierre − apertura de la rueda| ≥ 0,8 × rango del día (etiqueta ex post, 15,6 % de los días en A).

| Módulo | Neto en días de tendencia | Neto en el resto | Lectura |
|---|---|---|---|
| R AtrPhase | +152 (85 ops) | −6,6 (165) | vive de los días de tendencia |
| A20 Absorb 20m | +85 | −7,6 | ídem |
| T FtmEngine | +79 | **+3,9** | también gana fuera de ellos: por eso pasa todos los controles |
| N NDayLong | +64 | −6,7 | ídem R |
| C CapstoneGap | +60 | −0,6 | ídem |
| F Fabio ORB | +50 | −2,3 | ídem |
| S Swas | +36 | −3,9 | ídem |
| V VaultBreak | +26 | −5,4 | ídem |
| **Z ZetaTrendDay** | **−32 (18)** | **+39 (155)** | al revés: toma un objetivo temprano (161 de 173 salen por objetivo) |

Ni la noche movida, ni el gap, ni la volatilidad de 20 días, ni la tendencia de 60 días cambian la frecuencia de días de tendencia en A
(13–19 % contra 15,6 %). **Mecanismo central:** los módulos de ruptura/tendencia son una apuesta a que el día sea de tendencia; su ventaja
depende de cuánto pierden los otros días y de si dejan correr la ganadora hasta el cierre.

### 2.2 La ganancia está en dejar correr hasta el cierre; las salidas técnicas la regalan
| Módulo | Sale al cierre (EOD/sesión) | Sale por regla técnica | Sale por stop |
|---|---|---|---|
| S | +84 (264) | giro de SuperTrend −7,2 (2.585) | — |
| W | +131 (420) | recruce del VWAP −6,3 (8.579) | — |
| N | +76 (336) | ruptura fallida −41 (503) | — |
| A20 | +117 (373) | giro de SuperTrend +23 (277) | −52 (909) |
| T | +47 / +61 (cierre 16:00 / condicional 15:30) | — | −67 (675), objetivo +152 (232) |
| R | +58 (240, cierre) | fase opuesta −209 (9) | — |

Las salidas técnicas rápidas (SuperTrend, VWAP, «ruptura fallida») cortan muchas operaciones con pérdidas chicas que, sumadas a la fricción,
se comen lo que ganan las que llegan al cierre. Es la misma palanca que EdgeLab midió en la cartera (stop amplio frente a la fricción).

### 2.3 Fricción: cuatro módulos están muertos por diseño
Fricción / bruto: A1 150 %, Q 104 %, W 94 %, P 88 % (operan 25–110 veces por mes por 1–2 pts brutos). T 9 %, R 3 %, Z 5 %, C 16 %: los que
sobreviven ganan muchos puntos por operación.

### 2.4 Combinación: T + Z + R es una canasta casi descorrelacionada
Correlación diaria en A: T–Z −0,12, T–R 0,29, Z–R −0,04. Canasta T+Z+R por día: A t 5,2 (+20,5 pts/día), B t 6,5 (+35,9; peor día −271).
En el holdout (una apertura, `RESULTADO_HOLDOUT.md`) las tres fueron positivas. Las más correlacionadas entre sí son las de ruptura temprana
(V–W 0,42, F–V 0,36, F–W 0,35): mismo mecanismo, no suman diversificación.

## 3. Qué se puede mejorar y cómo probarlo sin sobreajuste (propuestas; cada una necesita su pre-registro)
1. **Salida al cierre en lugar de salida técnica** para S, W, N y A20 (stop duro amplio + cierre 15:55), variante contra la original **en
   datos no usados**: el M1 de S&P, Dow y Russell (los módulos de SuperTrend/ATR no dependen de puntos fijos), 2012–2026.
2. **Canasta T+Z+R a forward** junto a la cartera v2 (e-proceso), con Z y R con un stop duro de catástrofe (hipótesis nueva: el stop sólo
   tiene que cortar la cola, Z salió por objetivo en el 93 % de los casos).
3. **[RETIRADO 2026-11-18, K48: gap y noche se conocen a las 09:30 y A1/A20 entran mayormente de noche; ver la nota al pie]** **Contextos que conservaron dirección** (A20 y A1 con gap alto; R con tendencia de 60 días a la baja y en la primera hora): a forward como
   filtros, sin tocar las reglas ya en papel.
4. **Predecir días de tendencia** es el problema de fondo para cualquier regla de ruptura: buscar predictores nuevos (rango de los primeros
   30–60 min, volumen relativo de la apertura, amplitud de mercado) como familia propia, sin retornos de estrategia (E0: ¿predicen la etiqueta?).

## 4. Transferible a EdgeLab
- La cadena «ruptura → mantener al cierre» y «cortar rápido sólo con stop duro, no con salida técnica» aplica a ORB/PREAPERTURA/CVGAP.
- El filtro de T (KNN sobre las operaciones pasadas de la propia regla) es la idea más original: probarlo como capa sobre PREAPERTURA-NQ y CVGAP-ES-C
  (desarrollo → réplica no mirada).
- Z demuestra que en días de tendencia **tomar un objetivo temprano** también paga, al revés que las rupturas: combinarlo con ASIA (noche movida)
  es una hipótesis natural.


## Nota de auditoría K48 (2026-11-18)
El atlas condicionó todos los módulos por `noche` (18:00→09:30), `gap` (apertura 09:30) y `orb15` (09:30–09:45), pero A1, A20, E, S y O
entran mayormente de noche y Z, W, N y R antes de las 09:45. Para esos módulos esas variables miraban el futuro.
- **Arreglo:** `tools/fundedsync_mecanismos.py` (`CONOCIDA_EJE`) marca NO_CAUSAL cada eje que se conoce después de alguna entrada del
  módulo. Se volvió a correr (`mecanismos/MECANISMOS.json`).
- **Efecto:** las elegidas en A bajan de 19 a 12 (salen A1 noche/gap, A20 noche/gap, E noche/gap/orb15) y siguen siendo 0 las que
  pasan en B.
- **Alcance:** ninguna conclusión vigente dependía de esas celdas. La propuesta 3 (A20/A1 con gap alto) queda retirada. Los nulos
  sobre el día de tendencia (medidos a las 10:30 y 12:00) no cambian.
