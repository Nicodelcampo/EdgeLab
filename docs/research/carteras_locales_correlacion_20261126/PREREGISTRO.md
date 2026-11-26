# CARTERAS-LOCALES-CORRELACION: correlación y curvas de capital de las carteras subidas desde la sesión local (pre-registro, 2026-11-26)

Estado: PRE-REGISTRO — descriptivo, se commitea y se cuenta antes de calcular.
- **Pedido de Nico (2026-11-26):** «subí algunas carteras; cuando las encuentres, correlalas en EdgeLab incluyendo holdout y pasame las
  equity curves».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF2:** descriptivo sobre series ya calculadas, sin selección.
- **Familia:** `CANASTA_CORRELACION`.

Antecedentes:
- `cartera_nt8_20261125/RESULTADO.md`: carteras INTRADIA8, INTERDIA3 y C2VZ_2, a 1 micro, 2019-07 → 2026-09.
- `fundedsync_deploy_multiprop_20261122/RESULTADO.md`: P_OPT_SF_v2 (pesos W5); su referencia tiene operaciones desde 2025-01 hasta el
  2026-11-17, con HOLDOUT A5 y TERMINAL, ya abiertos por esa campaña.
- `canasta_correlacion_20261120/RESULTADO.md`: canasta T + R + Z-banda + RQ5 NQ.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36 escalas: se correlaciona en sus unidades; las curvas se muestran en las suyas).

Potencia previa: no aplica a una prueba (descriptivo). Se publica el t mensual por bloque A5.

Diagnóstico de mecanismo: no aplica (sin grilla). Episodios: los bloques DESC/REP/HOLDOUT de A5 y el tramo TERMINAL por separado.

## Justificación económica
Saber si las carteras se pisan o se diversifican antes de repartir cuentas entre ellas.

## Qué se calcula (fijo)
**Series diarias:**
- INTRADIA8, INTERDIA3 y C2VZ_2, en USD a 1 micro, de la matriz `MATRIZ_DIARIA_1MICRO`;
- P_OPT_SF_v2: Σ peso × R neto por día, desde su CSV de referencia;
- CANASTA_TRZQ: T + R + Z-banda + RQ5 NQ, en R, todas las particiones hasta el 2026-09-30, a partir de sus operaciones versionadas.

**Correlaciones:** Pearson diaria y mensual en el período común. Se hacen dos cortes: 2019-07 → 2026-09 sin P_OPT, y 2025-01 → 2026-09
con P_OPT.

**Por serie y bloque A5:** R/mes o USD/mes, t mensual y % de meses positivos.

**Curvas de capital** de cada una.

**Contador:** 1.

## Cómo podría refutarse
Correlación mensual > 0,5 entre carteras: no diversifican y repartirlas no reduce riesgo.
