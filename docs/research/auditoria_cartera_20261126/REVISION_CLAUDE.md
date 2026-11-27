# Revisión de la auditoría de Antigravity (2026-11-26): qué se sostiene y qué no

Estado: VIGENTE — revisión de Claude (2026-11-27) de `RESULTADO.md` y `ROADMAP_FRENTES_CONTINUACION.md`, verificada contra el código y
los artefactos de esta carpeta. Las corridas no tenían pre-registro: quedaron contadas después (`REGISTRO_POSTERIOR.md`, 169 pruebas, EF2).

North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

> **Corrección (2026-11-27, revisión pedida por Nico: «quizás fuiste demasiado estricto»).** Tres afirmaciones de esta revisión eran más
> duras de lo que la evidencia permite:
> 1. **Los stops ATR de R, Z, N y W no se eligieron mirando el holdout.** Son la configuración de `fundedsync_prop_opt_20261122`
>    (pre-registrada, DESC → REP) y la que corre en NT8 (`R_osc30_end660_ATR50`, `Z_b15_e20_eff40_ATR50`, `N_d5_fbTrue_ATR25`,
>    `W_slope_allowReFalse_ATR25`). Sólo `V_nm30_tp1400` y `T_ES_adapt` son variantes nuevas de la auditoría.
>    - Lo que sigue en pie: las series de los estudios de cartera (de Antigravity y de Claude) usan también los meses HOLDOUT de A5.
> 2. **El universo de `Regla_V2_Clean` no está armado mirando el futuro**, salvo V re-preciada. Es el de los motores operables en NT8:
>    un criterio previo y legítimo. Su walk-forward (2021-07 → 2026-09, pesos sólo con historia) a igual volatilidad sigue en pie, con esa
>    salvedad: Sharpe 1,94 contra 1,89, y caída intradía −8.712 contra −14.499.
> 3. **El barrido de Kaggle no está «al nivel del azar».** 8 sobrevivientes contra 3,9 esperados: Fisher una cola p 0,014. La persistencia
>    más fuerte es la de los negativos (overnight de ES, EMD y FTSE pierden en los dos bloques). Ningún sobreviviente tiene t ≥ 2 en REP. El
>    mejor (overnight del Russell, DESC t 2,17) no tiene potencia: 228 meses para decidir.
>
> 4. **(Segunda revisión, 2026-11-27.) Concedí demasiado sobre REGLA-CARTERA.** Con los números de la propia auditoría
>    (`AUDITORIA_RESUMEN.json`), a igual volatilidad:
>    - el Sharpe queda igual en walk-forward (1,91 contra 1,89);
>    - la caída baja de verdad: Calmar intradía 2,03 contra 1,37 en walk-forward 2021–2026, y caída intradía −9.364 contra −14.499 en
>      2023–2026 (−35 %);
>    - la versión operable en NT8 (Fix3: sin F ni C, pesos acotados) da Calmar 1,97 y caída −8.470.
>
>    El 55–60 % de la baja de caída era tamaño, como dijo Antigravity; el resto es real y es lo que pesa en una cuenta con pérdida máxima.
>    Sigue en pie que la regla es frágil al corte temprano (2021-12 y 2022-12 quedan debajo de la actual).
>
> Lo que **no** cambia, verificado:
> - La ventaja cripto de la auditoría dependía de las monedas elegidas con información de hoy. El top-8 punto en el tiempo da REP −$28/mes
>   con 20 pb y ≈ $0 con 10 pb (`cripto_pit_20261127/RESULTADO_TOP8.md`).
> - F, C y O no son operables en NT8.
> - (La frase «la regla de Claude no supera a la actual a igual riesgo» queda corregida por el punto 4: empata en Sharpe y baja la caída.)

## 1. Críticas a REGLA-CARTERA que se aceptan

| Crítica | Verificación | Consecuencia |
|---|---|---|
| F, C y O no tienen motor en NT8; N, W y SOMEOD sí existen pero no están en los presets | Correcta | La selección de la regla no es operable tal cual |
| O no opera desde 2025-10-14 (tope de margen); sin tope perdió −3.341 USD en ese tramo | Correcta | O no entra a ninguna cartera de futuros prop |
| F y C tienen Sharpe 0,22/0,25 en 2012–2026; entraron por la ventana 2019–2023 | Correcta | La regla elige por t en una ventana: le pasa lo mismo que a toda selección |
| 55–60 % de la baja de caída (−13.964 → −3.702) viene de operar al 44 % del riesgo base | Correcta: la caída escala con el tamaño; a igual volatilidad la regla queda en −9.364 | La ventaja de la regla en caída era sobre todo tamaño |
| En cortes tempranos (2021-12, 2022-12) la regla queda debajo de la cartera actual | Correcta (6 cortes) | La ventaja de Sharpe no es robusta al corte; en walk-forward queda empatada (1,91 vs 1,89) |

Corrección propia: `F-REGLA-CARTERA-DECORRELACIONADA` pasa a decir que la regla **no supera** a la cartera actual a igual riesgo; lo que
deja es el criterio (sumar decorrelacionadas a riesgo parejo), no una selección.

## 2. Lo que la auditoría afirma y no se sostiene

1. **«Todos los candidatos nuevos se evaluaron sólo en DESC y REP, con HOLDOUT sellado»: falso para las variantes CME.** Las series de
   `R_ATR50_NQ`, `Z_ATR50_NQ`, `V_nm30_tp1400_NQ`, `N_ATR25_NQ`, `SOM_eod_NQ`, `W_eod_ATR25_NQ` y `T_ES_adapt` tienen valores en los 478
   días HOLDOUT de A5 (`SERIES_EXPANDIDAS_DIARIAS.csv.gz`). La columna «Sharpe 2019–26» y el walk-forward los incluyen, y los stops ATR
   (0,25/0,50) y `nm30_tp1400` se eligieron mirando esa ventana. Sólo M1DK, Kaggle y cripto quedaron sellados. Lo mismo vale para el
   trabajo de cartera de Claude (ESTABILIDAD, REGLA, ADAPTAR-PRESENTE 1 usaron todos los meses de las series FundedSync). **Conclusión:**
   la familia FUNDEDSYNC no tiene HOLDOUT A5 limpio para variantes; sólo el terminal (desde 2026-10-01) y el forward.
2. **`Regla_V2_Clean` le gana a la regla de Claude con un universo armado después de mirar.** Sacar F/C/O se justifica por operabilidad
   (no hay motor NT8), y eso vale. Pero las variantes que entran en su lugar (stops ATR, V re-preciada, SOM al cierre) se eligieron por su
   resultado en 2019–2026. El walk-forward elige pesos sin mirar el futuro, pero dentro de un universo ya filtrado con el futuro.
3. **«May–sep 2026: +14.449 a igual volatilidad»** cae justo en el tramo que motivó los cambios, y sep-2026 es HOLDOUT A5. No es evidencia.
4. **Barrido de Kaggle: 8 de 99 «sobreviven»** (DESC > 0 y REP > 0). Con 24 positivas en DESC y 16 en REP, al azar se esperan 3,9. Hay algo
   de persistencia (P(REP+ | DESC+) 0,33 contra 0,11), pero ninguna tiene t ≥ 2 en REP, y la correlación de t entre bloques (0,53) viene
   sobre todo de la fricción: las negativas lo son en los dos. `DK_WTI_DON` tiene 56 operaciones en 14 años. Son pistas débiles.
5. **Cripto: la pista más útil para decorrelacionar, todavía sin evidencia.** 3 de 5 reglas positivas en DESC y REP. Cada una tiene t de
   1,2 a 1,8, REP de 12 meses, y la cartera 1/N tiene t 2,31 en 51 meses. La correlación mensual con la cartera CME es +0,02. Hay tres
   sesgos sin cubrir:
   - 8 monedas elegidas hoy: sesgo de supervivencia (sin LUNA, FTT…).
   - Costo de 10 pb ida y vuelta: es sólo la comisión taker, sin deslizamiento. Importa porque `CR_Trend_4H_EMA` hace 509 operaciones por
     mes.
   - HRP pone el 91 % en `CR_XSMOM_Neutral`.
6. **Monte Carlo de props (20 000 caminos).** Los simuladores ahora tienen calibración K28 con series de resultado conocido
   (`tests/research/test_auditoria_cartera_mc20k.py`): hacen lo que dicen sus reglas. Pero su retiro es «saldo − piso − 500», hasta 4
   veces, y no es el de `tools/cartera_lucid.py` (el calibrado contra las reglas de la cuenta). Los EV por cuenta son exploratorios.
7. **Procedimiento.**
   - 169 pruebas sin pre-registro ni conteo, ahora contadas como posteriores.
   - 3 simuladores nuevos fuera del motor único (K28), ahora calibrados.
   - Faltaba el encabezado «Estado:».
   - Los enlaces apuntaban a una ruta local de Windows.

## 3. Frentes del roadmap contra los criterios (rentabilidad, estabilidad, n de estrategias, caída, decorrelación)

| Frente | Valor | Riesgo / falta | Orden propuesto |
|---|---|---|---|
| 1. Preset NT8 sin F/C/O | Alto: hace operable la idea de sumar decorrelacionadas | Paridad M1↔NT8 de N y SOMEOD. Los stops ATR van como capa de riesgo declarada (cola), no como mejora medida | **1.º**, con versiones base + stop de catástrofe, a papel/forward |
| 6. Tamaño por cuenta (vol objetivo según el MLL) | Alto: es lo que de verdad bajó la caída | Usar el simulador calibrado `cartera_lucid.py`, no el del MC | **1.º** (junto con el 1) |
| 2. Cripto | Alto para decorrelación (+0,02) | Universo punto en el tiempo, costos ×2 y deslizamiento, pre-registro y apertura A5 con plan de potencia; cuenta/broker cripto es decisión de Nico | **2.º** |
| 3. Activos no-equity | Medio: una hipótesis única de tendencia diversificada (muchos futuros, un pre-registro) es más fuerte que perseguir los 8 sobrevivientes | Datos (ZB/ZN, SI, CL) y costos medidos | 3.º |
| 4. Pistas vivas | Medio | Z-banda y A20 ya están en curso; Franklin en YM/EMD/RTY/GC sí falta | Con el 3.º |
| 5. Ticks nuevos y costos | Bajo hoy; necesario antes de operar activos nuevos | — | Cuando un activo nuevo pase la réplica |

Aporte al referente: separa lo que la auditoría prueba (la regla de Claude no le gana a igual riesgo; F/C/O no son operables) de lo que no
(las variantes elegidas mirando el HOLDOUT A5 de FUNDEDSYNC y los «sobrevivientes» al nivel del azar). Deja contadas las 169 pruebas y
ordena los frentes por cuánto acercan una cartera neta, operable y decorrelacionada.
