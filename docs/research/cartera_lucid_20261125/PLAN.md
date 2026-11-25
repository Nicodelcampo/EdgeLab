# Cartera Lucid inverso-volatilidad: plan (criterio declarado antes de simular)

Estado: PLAN (descriptivo de cuenta; no elige reglas ni busca ventaja, no suma pruebas al contador, igual que `lucid_plan_20261119`)  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Antecedentes: EXP-8 (`docs/research/caida_2026_20261125/RESULTADO_EXP8_MITIGACION.md`, F-CARTERA-INV-VOL-BAJA-DD), `tools/lucid_canastas.py`
(reglas oficiales LucidFlex 25K, ver `docs/research/propfirm_lucidflex_20261117/RESULTADO.md`), F-LUCID-SIN-OVERNIGHT, F-FRENO-DIARIO-NO.  
Pedido de Nico (2026-11-25): «armá la cartera con esos pesos en NT8… sencillo, diversificado, mitigando drawdown y riesgo, asegurar
payouts sin sacrificar tanta rentabilidad potencial».

## Qué entra
Lucid exige estar plano a las 16:45 ET y no permite tenencia nocturna: entran las 8 intradía de EXP-8 (T_NQ, R_NQ, Z_NQ, V_NQ,
RQ5_NQ, RQ5_ES, ES5N_ES, Franklin_NQ) en micros (MNQ, MES). C2_VZ (mantiene 24 h) y SOM sin_finde (19 % de noches) quedan fuera:
son la base de una segunda cartera sólo si se abre una cuenta que permita tenencia nocturna.

## Tamaño (lo que NT8 ejecuta: contratos fijos por estrategia, recalculados cada trimestre)
Al inicio de cada trimestre, con datos de los 12 meses anteriores de cada corrida NT8:
- peso `w_i` ∝ 1 / sd del R mensual (media 1 entre las 8, recorte [0,25; 2]);
- `n_i = max(1, round(w_i × B / mediana del stop en USD de 1 micro en los últimos 3 meses))`;
- si Σ n_i > 20 (tope de Lucid), todos se escalan hacia abajo (mínimo 1).
Esquemas: `UNO` (1 micro cada una), `RIESGO_IGUAL` (w_i = 1), `INV_VOL` (w_i de arriba); B ∈ {100, 150, 200, 300, 400} USD.
P&L diario = Σ n_i × (pnl_pts − fricción canónica del micro) × valor del punto (conservador: los pnl_pts de NT8 ya incluyen 1 tick
de deslizamiento). Sesiones 2020-01-02 → 2026-09-29.

## Evaluación y criterio
`lucid_canastas.evaluar` (bootstrap por bloques de 5 sesiones, evaluación + fondeada, 5 retiros, media contraída a la mitad).
**Criterio declarado**: en `DLL600|40%|contraida|max` (consistencia 40 % como la cuenta actual), el plan con mayor probabilidad de
cobrar más que el precio de la evaluación (`p_ganar`); entre los que quedan a ≤ 0,02 de ese máximo, el de mayor valor esperado
(`ev`). Se publican todas las variantes, la media de desarrollo y la media cero, y el mismo cálculo desde 2024-01 (régimen reciente).
