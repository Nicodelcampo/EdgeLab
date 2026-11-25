# Estado vivo de EdgeLab (snapshot maestro de contexto)

Estado: VIGENTE
Fecha: 2026-11-25
Fuente: generado por `python tools/contexto_vivo.py --write` (no editar a mano).

## 1. Anclas e Invariantes (fail-closed)
- North Star SHA-256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- Holdout A4/A5: frontera `2026-10-01 (20261001)` (`edgelab/holdout.py`); A5 `7 DESC / 2 REP / 3 HOLDOUT`
- Indice obligatorio: `docs/research/LEER_ANTES_DE_CADA_CORRIDA.md` v4 (2026-11-19)
- Contador global: `751` campanas / `538,657,014` pruebas registradas
- Edges promovidos: `ninguno` (`EDGES_DISCOVERED.md`)

## 2. Guardas y Leyes Empiricas Activas
- Costos canonicos unicos: `edgelab/costos.py` (`config/costos/costos_canonicos.json`); prohibido tablas ad-hoc
- Medicion: unidad R sobre stop inicial (bruto+neto, mini+micro); causalidad por prefijo verificada
- Friccion relativa: no elegir micro-edges donde friccion/R > 0.08; stop amplio frente a friccion
- M1 (K40/K43): stop al nivel salvo hueco; toda familia M1 calibra contra ticks por `a5.calibrar_por_sesion`
- Cadena unica: `tools/tablas.py` / `edgelab/research/ejecucion.py`; K27 potencia>=0.8; K51 contado antes; K55/K56 grilla
- Memoria activa (`edgelab/research/memoria_activa.py`): proponer algo en NO_REPETIR exige `Cambio respecto a falla previa:`
- Puertas de salida: `puerta_kernel.py` (pre-push Kaggle AST/holdout/sintetico) y `tools/puerta_corrida.py`

## 3. Pistas Vivas y Canastas en Papel
- Pistas vivas (`PISTA_VIVA`): 38 | Palancas (`PALANCA_DE_DISENO`): 33
  - `F-FS-IL-REMEDICION-V-CANDIDATA` (2026-11-21): Re-medición de los 15 módulos de FundedSync con la traducción IL corregida (commit 7965e7fb)
  - `F-RQ5-REGIMEN-ROBUSTO` (2026-11-20): RQ5 banda de ruido (Zarattini), fábrica, régimen 2018–2025
  - `F-RQ5-HOLDOUT-NO-CONCLUYENTE` (2026-11-20): RQ5 fábrica, holdout A5 2018-01 → 2026-09 (cinco índices)
  - `F-CANASTA-T-R-Z-RQ5-DIVERSIFICA` (2026-11-20): Correlación y canasta de las fábricas A20, T, R, Z-banda y RQ5 (1 R por operación)
  - `F-A20-SOLO-CORTA-HOLDOUT-TERMINAL` (2026-11-20): A20 NQ fábrica (sólo cortos) en el holdout terminal 2026-10-01 → 2026-11-16 y su beta corta
  - `F-Z-TRANSFER-RTY` (2026-11-19): Z (ZetaTrend de FundedSync, fábrica, stop 0,25 × ATR20) en Russell (RTY) y MidCap (EMD), nu…
- Canastas papel: Cartera v2 (2026-11-16) — 8 reglas, base de `SELECCION… | Cartera v3 (2026-11-16) — 8 reglas (forward en paralel… | Cartera B (2026-11-16) — T + Z + R de FundedSync en MN…

## 4. Bloqueado / NO_REPETIR (66 vigentes en FACTORES.jsonl)
- `F-ESTADO-APERTURA-20S-NO-FILTRA` (2026-11-25): Filtro por estado de la apertura de las 20 sesiones previas (cont_orb, ac5_ma…
- `F-ENTRADA-RETROCESO-SELECCION-ADVERSA` (2026-11-25): Entrar en el retroceso (límite a k=0,25/0,50 del riesgo, 30 min) en vez de en…
- `F-Z-RTY-REP-COLAPSA` (2026-11-24): Z (ZetaTrend) en Russell M2K — supera a F-Z-TRANSFER-RTY
- `F-RQ6-ES-NQ` (2026-11-24): RQ6 ES/NQ
- `F-RQ2-ES-NQ` (2026-11-24): RQ2 ES/NQ
- `F-PREAPERTURA-NQ-INTENTO1-SUBMINUTO` (2026-11-24): PREAPERTURA-NQ Intento 1
- `F-PREAPERTURA-INTENTO0` (2026-11-24): PREAPERTURA Intento 0 (NQ_OP_SAL, GC_OP_SAL, ES/YM)
- `F-HOBBIECODE-SUPERTREND-ORO` (2026-11-24): HobbieCode Supertrend Oro H1
- `F-HOBBIECODE-GANN-HILO-ORO` (2026-11-24): HobbieCode Gann HiLo Oro H1
- `F-FM2-CONCRETUM-NO-REPLICA` (2026-11-24): FM2 (Concretum Band)
- `F-ES5N-NQ` (2026-11-24): ES5N en NQ (10:00 NY)
- `F-DUAL-THRUST-GC-X038` (2026-11-24): Dual Thrust GC (X038)
- `F-DRC-TORI-FRICCION` (2026-11-24): DRC-NQ-R, TORI-NQ-R, U1-ZONAS-AVCL-ES/NQ, CVGAP-CFD-NQ (ejecución)
- `F-CVGAP-COMEX-CIERRE-ATRAS` (2026-11-24): CVGAP-ES-C, CVGAP2-GC#11, COMEX-CIERRE-GC-R#0
- `F-C2-VBB-DBO-P80` (2026-11-24): CARRIL2 variantes VBB, DBO, P80 (y D7, IBS, TT, TOM en 2020–25)
- `F-BAJA-FRICCION-A5-BF1-BF8` (2026-11-24): BAJA_FRICCION_A5, variantes BF1..BF8 (Fut y CFD)
- `F-VENDEDOR-FUNDEDSYNC-CURVAS-2022` (2026-11-20): Curvas de los 15 módulos de FundedSync que muestra el vendedor (2022–2026)
- `F-FILTROS-CONTEXTO-SIN-FILTRO` (2026-11-20): VIX, VVIX, GEX, DIX, SKEW, VIX9D/VIX y COT (percentil móvil causal, terciles)…
- `F-SELECTIVIDAD-INVERSA` (2026-11-19): Pureza del día de tendencia (1 − retroceso máximo / rango, percentil causal d…
- `F-PICOS-DEFENDIDOS-ES-REFUTADA` (2026-11-19): PICOS-DEFENDIDOS en ES con la grilla de 207.360 celdas (8 meses de DESC)
- `F-FRANKLIN-FILTRO-ATR-NO-SIRVE-POR-MES` (2026-11-19): Franklin sólo en días de ATR alto (mejora de MEJORA-SF) medido por mes en el…
- `F-EXTERNAS28-DUAL-THRUST` (2026-11-19): Catálogo externo de 28 estrategias (114 variantes) en M1 de futuros con A5
- `F-EXTERNAS-ESTRUCTURALES-REFUTADA` (2026-11-19): 8 reglas externas con stop estructural (Gao 30m, Dual Thrust, Dynamic Breakou…
- `F-CRASH-VIX-INVERTIDA-REFUTADO` (2026-11-19): Filtro de crash 'no comprar la reversión corta con VIX9D/VIX ≥ 1' (IBS, Doubl…
- `F-CONFLUENCIA-MISMA-INFORMACION` (2026-11-19): Confluencia causal de señales intradía con bruto real (SOM, Franklin, FM1, FM…
- `F-A20-NO-TRANSFIERE` (2026-11-19): A20 (FundedSync) en YM, RTY y EMD
- `F-ORB5-BRUTO-ESTABLE` (2026-11-18): ORB de 5 min (Zarattini-Aziz) en índices de EE. UU.: el bruto existe y es chi…
- `F-OPTION-ALPHA-FUTUROS` (2026-11-18): Reglas del Top 20 Live de Option Alpha (Taco/Sandwich 13:45, ORB 60 con días…
- `F-LUXIMB-EJECUCION-TIMING` (2026-11-18): Rediseñar la ejecución del fade de impulsos LUX-IMB (stop 0,5–2·D, objetivo 1…
- `F-IB-MADONNA-NO-DEFIENDE` (2026-11-18): Fade del primer rechazo en el borde del Initial Balance (Madonna) y 10 varian…
- `F-GEX-DIA-TENDENCIA` (2026-11-18): Gamma de los dealers (GEX del cierre previo): baja → días de más magnitud y r…
- `F-FILTRO-PICOS-NO-AGREGA` (2026-11-18): Esperar picos o un barrido (pivotes blandos de 1 vela, vuelta 0,25·D, cancela…
- `F-ESCALONADAS-M1-SIN-SENAL` (2026-11-18): Escalera plana de picos (escalonadas_det PLANAS) detectada en M1 y operada a…
- `F-DIA-TENDENCIA-CLASES-NUEVAS-NULAS` (2026-11-18): Calendario (vencimiento mensual, vuelta de mes), NR7, día interior, ubicación…
- `F-AUDITORIA-UNIDADES-Y-VIEJAS` (2026-11-18): Errores de unidad y escala: medir en ATR módulos que arriesgan mucho menos qu…
- Ver lista completa `NO_REPETIR` (66) en `docs/research/FACTORES.jsonl`

## 5. Holdout Consumido y Aperturas
- Familias con sesiones miradas: `AREAS_EXP_1_CRUZADO`<=20261022, `LUXIMB_FADE_VISOR`<=20261021
- Aperturas confirmatorias activas: 32 (ZONAS_GAPS:ZGAP-NQ-CANASTA, U1_RACIMOS_GRILLA_NQ:U1-RACIMOS-GRILLA-NQ, U1_ZONAS_BT2_NQ:U1-ZONAS-BT2-NQ, U1_ZONAS_BT2_ES:U1-ZONAS-BT2-ES, U1_RACIMOS_GRILLA_ES:U1-RACIMOS-GRILLA-ES)

## 6. Arranque y Cierre Obligatorios (4 comandos)
1. `python tools/estado.py`  2. `python tools/antecedentes.py "<idea>" --familia <FAM>`
3. `python tools/puerta_corrida.py --prereg <PREREG.md> --modulo <mod> --exigir-contada`  4. `python tools/cierre.py`
