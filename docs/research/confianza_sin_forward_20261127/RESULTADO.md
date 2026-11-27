# CONFIANZA-SIN-FORWARD: qué sube y qué baja la confianza sin esperar forward (resultado, 2026-11-27)

Estado: RESULTADO — campaña EF3 pre-registrada en [PREREGISTRO.md](PREREGISTRO.md) (`ecda52cb` en el contador: 3 pruebas,
`CARRIL2_CONFIANZA`). Datos hasta 2026-09-30; TERMINAL sellado. Herramienta: `python tools/confianza_sin_forward.py correr|dsr`.

## 1. Carril 2: las tres pruebas confirman (BH q 0,10 sobre 3: las tres)
| Prueba | Datos que nadie había usado para estas reglas | Sharpe anual | t | Meses | Meses + | Veredicto |
|---|---|---|---|---|---|---|
| **H1** transferencia | 5 reglas × 8 índices extranjeros, 1990–2026 (15.508 operaciones) | 0,50 | 3,02 | 440 | 65 % | CONFIRMA |
| H1 con costos ×2 (6 pb) | ídem | 0,36 | 2,19 | 440 | 62 % | se sostiene |
| **H2** período anterior | 5 reglas × 4 índices de EE. UU., 1990–2005 (4.106 operaciones) | 1,01 | 4,05 | 192 | 65 % | CONFIRMA (ver salvedad) |
| **H3** placebo | Canasta sellada menos su control N con la misma exposición, 2006–2026 | 0,46 | 2,07 | 248 | 58 % | CONFIRMA |

**Lo que sube la confianza:**
1. **El mecanismo se transfiere.** En 8 índices de Europa, Asia, Australia y Canadá, con las reglas sin tocar, conserva el 58 % del
   Sharpe de desarrollo (0,50 contra 0,86). Es justo el 0,57 que la literatura mide para reglas publicadas fuera de su muestra.
   - Los 8 índices dan positivo: ASX 0,53, Hang Seng 0,42, FTSE 0,40, EuroStoxx 0,38, DAX 0,28, TSX 0,25, CAC 0,24 y Nikkei 0,15.
   - Los controles N ganan menos: Sharpe 0,17.
2. **La ventaja es de la señal y no sólo de estar comprado.** La canasta sellada le gana a su placebo en todo el período (t 2,07),
   en DESC (t 2,18) y en el HOLDOUT A5: regla 1,06 contra control 0,37, diferencia t 1,22.

**Lo que la baja:**
1. **Afuera de EE. UU., la ventaja se achica con el tiempo:** Sharpe 0,73 antes de 2009, 0,24 desde 2009 (t 1,00) y 0,16 desde 2019
   (t 0,45).
   - En los futuros de EE. UU. del HOLDOUT, 2019–2026 sigue en 1,12 (`canasta_amplia_20261127/RESULTADO_HOLDOUT_CARRIL2.md`).
   - El patrón (fuerte antes de que estas reglas se publicaran y difundieran, más débil después) es el de McLean y Pontiff, y
     anticipa que en vivo rinda menos que en el HOLDOUT.
2. **En la REP, el placebo le ganó a la regla** (control 1,45 contra regla 1,26). En meses de suba fuerte, la deriva domina.
   - El control solo ya rinde 0,47 de Sharpe en 2006–2026: cerca de la mitad del resultado de Carril 2 es estar comprado.
3. **Por regla, afuera:**
   - cambio de mes (TOM, t 4,31), Turnaround Tuesday (t 2,47) y Double 7 (t 2,21) se sostienen;
   - IBS es débil (t 1,05);
   - VBB da negativo (−0,19), probablemente porque el VIX de EE. UU. no mide la volatilidad de esos índices.
   - Nada de esto se usa para cambiar pesos: sería elegir con datos ya mirados.
4. **H2 suma poco:** 1990–2005 es la muestra con la que se publicaron varias de estas reglas, y ahí el control también gana (0,58).

## 2. Sharpe deflactado y corrección por pruebas (descriptivo, `DSR_HAIRCUT.json`)
| Estrategia | Pruebas de su familia | Sharpe | t | p Bonferroni | Sharpe deflactado | Lectura |
|---|---|---|---|---|---|---|
| Carril 2 (DESC+REP, donde se eligió) | 32 | 0,86 | 3,37 | 0,012 | **0,90** | Sobrevive a la selección dentro de su familia |
| Carril 2 (HOLDOUT A5) | 1 prueba pre-registrada | 1,06 | 2,42 | — | — | Prueba única: no se deflacta |
| T+R+Z+V NQ (2021–2026) | 948 | 2,49 | 5,14 | < 0,001 | 0,97 | Cota optimista: no se conocen las pruebas del vendedor |
| Cripto OFI (HOLDOUT) | 5 | 1,13 | 1,39 | 0,41 | 0,56 | Sin evidencia suficiente |
| Macro risk premia (HOLDOUT) | 7 | 0,38 | 0,87 | 1,00 | 0,30 | Sin evidencia |
| Cripto v3 (HOLDOUT) | 32 | 0,49 | 0,60 | 1,00 | 0,07 | Sin evidencia; consistente con la REP iterada |

## 3. Confianza por estrategia, sin forward
| Estrategia | Antes | Después | Qué la movió |
|---|---|---|---|
| **Carril 2** | HOLDOUT a favor (t 2,42) | **Sube**, con un tamaño esperado menor | Transferencia a 8 índices, placebo superado y deflactado 0,90. Expectativa en vivo ≈ 0,4–0,6 de Sharpe por el decaimiento desde 2009 |
| T+R+Z+V intradía NQ | Vista por el vendedor | Sin cambio | El deflactado no corrige la selección del vendedor; lo que sigue disponible es M1 2006–2019 (`VEREDICTO_M1_20261117.md`) y el forward |
| Cripto OFI | NO_CONCLUYENTE | Sin cambio | Le falta n: 18 meses |
| Macro risk premia | NO_CONCLUYENTE | Baja | Deflactado 0,30 y tramos largos planos |
| Cripto v3 | NO_CONCLUYENTE | Baja | Deflactado 0,07; retiene 38 % del Sharpe |

**Pendiente** (otra corrida, otra decisión):
- cripto de 2019-09 a 2020-12, período anterior al universo punto en el tiempo y que nadie miró;
- T, R y Z en índices extranjeros con M1 de Dukascopy, que está en la máquina de Nico y no en este entorno.

Diagnóstico de grilla: sin grilla. Las reglas, stops y topes son los de `carril2.py` sin cambios; las únicas perillas son el costo
(3/6 pb) y el universo, publicados completos (por regla, por índice y por época).
Episodios: afuera, Sharpe 0,73 en 1990–2008 contra 0,24 desde 2009 y 0,16 desde 2019 (decae, no se apaga: 61–62 % de meses
positivos); en la REP 2006–2026 el control superó a la regla.

Aporte al referente: con datos que nadie había usado para estas reglas, la confianza en Carril 2 sube como mecanismo (se transfiere y
le gana al placebo) y su tamaño esperado baja a 0,4–0,6 de Sharpe. Las demás quedan donde estaban o bajan, con números.
