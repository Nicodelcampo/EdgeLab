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

## Addendum de auditoría (2026-11-27, Antigravity)
Generado sobre los archivos versionados con `python tools/confianza_sin_forward.py dsr && python tools/confianza_sin_forward.py auditar_h1_h3` (`DSR_HAIRCUT.json`, `AUDITORIA_H1_H3.json`).

### 1. Corrección de doble estándar en `DSR_HAIRCUT.json`
El DSR (Bailey & López de Prado 2014) corrige selección *in-sample* (`N` pruebas); aplicarlo con `N` de toda la familia sobre un **HOLDOUT único congelado** (`N_efectivo = 1`) doble-penalizaba a Cripto v3 (`N=33 → DSR 0,07`) y Macro RP (`N=7 → DSR 0,30`) mientras eximía a Carril 2:

| Estrategia | Muestra | N_IS familia | N_efectivo DSR | Sharpe | t | p Holm (4 frentes HO) | DSR corregido |
|---|---|---|---|---|---|---|---|
| Carril 2 sellada (HOLDOUT A5, 63m) | sellada | 32 | **1** | 1,057 | 2,42 | 0,0309 | **0,992** |
| Cripto OFI (HOLDOUT A5, 18m) | sellada | 5 | **1** | 1,133 | 1,39 | 0,2479 | **0,911** |
| Macro risk premia (HOLDOUT A5, 63m) | sellada | 7 | **1** | 0,380 | 0,87 | 0,3839 | **0,806** |
| Cripto v3 (HOLDOUT A5, 18m) | sellada | 33 | **1** | 0,493 | 0,60 | 0,3839 | **0,721** |
| Carril 2 sellada (DESC+REP, 186m) | vista | 32 | 32 | 0,857 | 3,37 | — | **0,897** |
| Cripto v3 (DESC+REP, 51m) | vista | 33 | 33 | 1,289 | 2,66 | — | **0,698** |
| Macro risk premia (DESC+REP, 186m) | vista | 7 | 7 | 0,365 | 1,44 | — | **0,518** |
| Cripto OFI (DESC+REP, 51m) | vista | 5 | 5 | 0,596 | 1,23 | — | **0,510** |
| T+R+Z+V NQ (2021–2026-09, 51m) | vista vendedor | 948 | 948 | 2,494 | 5,14 | — | 0,968 |

### 2. Hallazgos en `H1` y `H3` (`AUDITORIA_H1_H3.json`)
- **`C2_VBB` en H1 usaba `^VIX` de EE. UU. para Europa y Asia:** quitando `VBB`, las 4 reglas de precio en 8 índices suben `+31 %` de Sharpe: **`Sh = 0,635, t = 3,84`** (`1990–2026`), `Sh = 0,314 (t = 1,32)` desde `2009` y `Sh = 0,260 (t = 0,72)` desde `2019`.
- **La caída post-2009 afuera NO es sesgo ex-dividendos:** `DAX` (*total return*, con dividendos) cae más post-2009 (`Sh = 0,093`, `2019+ 0,040`) que los otros 7 índices *price return* (`Sh = 0,256`, `2019+ 0,183`).
- **Placebo `regla − control N` afuera:** en `1990–2026` las 4 reglas sin `VBB` superan claro al control (`Sh = 0,568, t = 3,44`, con `TOM t = +2,23` y `TT t = +2,05`); desde `2009` ninguna de las 5 reglas supera al control afuera (`4` sin `VBB`: `t = −1,42`; `2019+ t = −1,80`). Esto respalda calibrar la expectativa en vivo de Carril 2 a `Sharpe ~0,5–0,7`.
- **Discrepancia `H3 DESC` (`1,072`) vs `SERIES_HOLDOUT_A5_NOCME_MENSUAL` (`0,801`):** en `HOLDOUT` coinciden a `0,0` (`1e-15`); la diferencia en `DESC`/`REP` (`279` ops en `DESC`, `53` en `REP`) proviene de que `canasta_amplia.py` censuraba toda operación cuya salida tocaba otro bloque (`HOLDOUT`/`EMBARGO`), afectando sobre todo a `C2_TOM` de fin de mes (`2016-06`, `2018-12`). Sin censura de borde, la retención real de Carril 2 es `~95 %` (`1,057 / 1,11`).
