# Estrategias candidatas: dónde está cada una, con qué evidencia y cómo se ejecuta (2026-11-20)

Estado: VIGENTE — índice para cualquier agente o persona que lea EdgeLab.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **0 edges promovidos.** Todas están en papel o en forward. Operar con dinero real lo decide Nico.
- **Detalle:** `docs/research/HANDOFF_2026-11-20_FILTROS_HOLDOUTS_CANASTA_NT8.md` y `docs/research/canasta_correlacion_20261120/RESULTADO.md`.

## Por estrategia
R/mes y t mensual son de los meses DESC + REP de 2018-01 → 2025-07, a 1 R por operación.

| Estrategia | Regla (código) | Operaciones medidas | Evidencia | R/mes (t) | Ejecución en NT8 |
|---|---|---|---|---|---|
| **T** (FtmOrb de FundedSync, NQ) | `edgelab/research/fundedsyncstack/modulos_w_n_t.py::run_t` | `docs/research/m1_largo_20261117/FS_OPS_T2008_NQ.csv.gz` | Pista fuerte en NQ, bruto + en 13 de 14 años desde 2012 (`m1_largo_20261117/RESULTADO_T_2020.md`); holdout terminal de FundedSync | +2,03 (3,60) | FundedSync con su licencia |
| **R** (AtrPhase, NQ) | `fundedsyncstack/modulos_r_z_e_q.py::run_r`; variante `R_21_100_2.5_660` con stop de catástrofe de 0,25 × ATR20 | `docs/research/neto_pistas_20261119/RZ_OPS.csv.gz` | REGIMEN_ROBUSTO 81/81, PBO 0,23 (`neto_pistas_20261119/RESULTADO.md`) | +1,32 (3,50) | `nt8/strategies/EdgeLabAtrPhaseStop.cs`; paridad contra `regimen_forward_20261119/R_REFERENCIA_PARIDAD.csv` |
| **Z-banda** (ZetaTrendDay, NQ) | `fundedsyncstack/modulos_r_z_e_q.py::run_z`; 9 configuraciones `Z_{10_30,15_20,30_10}_{35,45,55}`, mismo stop | `RZ_OPS.csv.gz` | Serie separada del forward (`regimen_forward_20261119/PREREGISTRO_ZBANDA.md`) | +0,63 (2,93) | FundedSync con su licencia |
| **RQ5** (banda de ruido de Zarattini, NQ) | `edgelab/research/rq5_regimen.py`; fábrica `L60_m1_c689`, s 0,45, tp 2 | `docs/research/rq5_regimen_20261119/OPS_DESC_REP.csv.gz`, `HOLDOUT_OPS.csv.gz` | REGIMEN_ROBUSTO en desarrollo (+0,050 R); holdout A5 NO_CONCLUYENTE (+0,027) | NQ +1,00 (2,61); 4 índices +2,44 (1,99) | `nt8/strategies/EdgeLabRQ5.cs`; paridad contra `docs/research/nt8_rq5_20261120/RQ5_NQ_REFERENCIA_PARIDAD.csv` |
| **A20** (Absorb 20m, NQ, **sólo corta**) | `fundedsyncstack/modulos_a1_a20_f_s.py::run_a20`; fábrica `A20_7_2_2.5_1.5` | `RZ_OPS.csv.gz`; terminal en `docs/research/filtros_contexto_20261120/A20_TERMINAL_OPS.csv` | Positiva desde 2022; holdout terminal NO_CONCLUYENTE (+1,10 R/op, n 29, potencia 0,08); −1 R por cada 1 % de NQ | +0,59 (0,49) en 2018–25; +2,65 (1,78) desde 2022 | FundedSync con su licencia; **no va a 1 R en la canasta** |

## Canasta
- **Composición:** T + R + Z-banda + RQ5 NQ.
- **Resultado medido:** +4,98 R/mes, t 5,17, 71 % de meses positivos, caída máxima −23 R.
- **Ejecución:**
  - T y Z en FundedSync;
  - R con `EdgeLabAtrPhaseStop.cs` (o en FundedSync, sin stop);
  - RQ5 y la guarda de toda la cuenta (pérdida diaria, piso, plano a las 16:45 ET) con `nt8/strategies/EdgeLabCanasta.cs`.
- **Por qué no está A20:** sumarla a 1 R por operación baja el t a 3,0 y lleva la caída máxima a −90 R.

## Por qué T, Z y A20 no tienen archivo NT8 propio
Su lógica en Python es una traducción del código desensamblado de FundedSync, un producto comercial con licencia por hardware. En Python
sirve para research. Para operar se usa el producto original con su licencia.

## Otras con señal estable (sin canasta todavía)
- **SOM y Franklin:** `docs/research/m1_largo_20261117/SOM_OPS_*.csv.gz` y `FRANKLIN_OPS_*.csv.gz`.
- **Carteras v2, v3 y B:** `docs/cartera/CANASTAS_VIGENTES.md`.
