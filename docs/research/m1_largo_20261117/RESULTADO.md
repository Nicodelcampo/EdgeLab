# FundedSync (15 módulos), SOM y régimen análogo sobre M1 real de futuros 2006–2025 (resultado, 2026-11-17)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (con su enmienda 1, sobre las fechas de T) y análisis posterior, que se marca como tal.
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `RESULTADO.json`,
`FS_OPS_*.csv.gz`, `FS_OPS_T2008_*.csv.gz`, `SOM_OPS_*.csv.gz`, `ESTADO_*.csv`.

## 1. Calibración: la medición sobre el CFD representaba al futuro
NQ futuros contra la medición anterior sobre el CFD (2012–2025), por sesión: 15 de 16 calibran (correlación 0,72–1,0, mismo signo; SOM
0,90). Excepción: A20 (correlación 0,94, pero la media cambia de signo: −1,3 contra +1,3 puntos). Las conclusiones previas sobre el CFD
valen para el futuro.

## 2. Pre-registrado (en neto, costos canónicos): todo NO_CONCLUYENTE
| Estrategia | Años limpios | Neto por op. | IC90 | Años + | Potencia | Veredicto |
|---|---|---|---|---|---|---|
| T (ATR) | 2008–2011 (enmienda 1) | −0,032 | [−0,046, −0,017] | 25 % | 0,59 | NO_CONCLUYENTE (IC entero < 0) |
| Z (ATR) | 2006–2011 | −0,011 | [−0,049, +0,026] | 33 % | 0,60 | NO_CONCLUYENTE |
| R (ATR) | 2006–2011 | +0,054 | [−0,002, +0,110] | 67 % | 0,17 | NO_CONCLUYENTE (casi a favor) |
| SOM sin_finde (R) | 2006–2011 | −0,025 | [−0,056, +0,007] | 33 % | 0,14 | NO_CONCLUYENTE |

**Régimen análogo** (estado de referencia: volatilidad media o alta con tendencia alcista de 6 meses): las 9 dan NO_CONCLUYENTE.
- Patrón sugestivo, no significativo, en dos reglas de NQ:
  - PREAPERTURA-NQ: +0,35 R en meses análogos (147 operaciones) contra −0,34 en el resto;
  - IF-LUX-NQ: +0,19 contra −0,38.
- T, Z, R y SOM: sin diferencia entre meses análogos y no análogos.
- COMEX: peor en los meses análogos.

## 3. Análisis posterior (descriptivo, no pre-registrado): el «régimen» es la fricción
- **La fricción cambió de escala.** Es fija en puntos, y el rango diario creció. Fricción / ATR20 por operación:
  - NQ: 0,041–0,047 en 2006–2011 → 0,006 en 2020–2025;
  - ES: ≈ 0,045 → 0,015;
  - YM: ≈ 0,03 → 0,011.
  - Por eso casi todos los módulos pasan de negativo a ≈ 0 o positivo neto con el tiempo, también los que no tienen ventaja (A1, W).
- **Bruto (antes de costos), años limpios, NQ + ES + YM:**

| | Ops | Bruto por op. | IC90 | Años + |
|---|---|---|---|---|
| **SOM** (R) | 4.218 | **+0,064** | **[+0,033, +0,095]** | 67 % |
| **R** AtrPhase (ATR) | 481 | **+0,097** | **[+0,041, +0,154]** | 83 % |
| Z (ATR) | 356 | +0,028 | [−0,009, +0,065] | 67 % |
| O (ATR) | 1.613 | +0,010 | [−0,009, +0,030] | 67 % |
| T (ATR, 2008–2011) | 2.598 | +0,007 | [−0,008, +0,021] | 50 % |
| A1 (control) | 14.668 | −0,003 | [−0,004, −0,001] | 0 % |
| W (control) | 21.326 | −0,001 | [−0,003, +0,001] | 33 % |

- **SOM bruto por período e índice:** positivo en los 9 casos (NQ +0,061 / +0,085 / +0,054; ES +0,033 / +0,045 / +0,048; YM +0,097 / +0,041 /
  +0,012).
  - Su fricción en R bajó de 0,07–0,10 a 0,01–0,03.
  - Hoy, en NQ, el neto esperado es ≈ +0,04 R por operación.
- **R AtrPhase:** positivo bruto en NQ en los tres períodos. En ES y YM, positivo en 2006–2011 y ≈ 0 o negativo después. No tiene stop.
- **T:** sin señal bruta antes de 2020 (+0,002 / +0,016 / +0,053 en NQ). Lo de 2020–2025 es propio de esos años o ruido.
  - La prueba de régimen no lo apoya: en los meses análogos da −0,02.

## 4. Lectura
1. La mayor parte del «antes no, ahora sí» de las estrategias externas es fricción relativa, que cayó a 1/7 en NQ. No es un cambio de
   comportamiento del mercado.
2. SOM tiene la señal bruta más estable que medimos en EdgeLab: 20 años, 3 índices y años nunca usados. Con la fricción de hoy en NQ
   queda neta positiva y chica (≈ +0,04 R).
3. Un mecanismo con señal bruta estable sirve cuando la fricción relativa es baja. Esa condición es medible y se puede declarar antes:
   no hay que adivinar un régimen de mercado.
4. T, la pieza que sostenía la cartera B, no tiene señal en la historia larga: su ventaja 2020–2025 es frágil.
5. Las 5 reglas del embudo: sin señal bruta (`atras_m1_20261117`). El régimen análogo sólo deja una sospecha en PREAPERTURA-NQ e
   IF-LUX-NQ, sin significancia.

## 5. Qué sigue
- **SOM y R:** confirmar con datos no mirados, en neto y con la fricción actual:
  - otro índice de futuros (RTY y MidCap exportados de NT8: el «no transfiere a RTY» del 17-nov fue en CFD y en neto);
  - y el forward.
- **Para el tamaño:** que se gobierne por fricción en R al momento de operar, que es el paso 3 de `urgencia_vs_evidencia`.
- **Cartera B:** revisar el peso de T con un pre-registro nuevo; no se toca sobre la marcha.
