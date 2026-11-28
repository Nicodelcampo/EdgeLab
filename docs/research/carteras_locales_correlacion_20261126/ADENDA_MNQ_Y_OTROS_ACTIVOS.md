# Adenda 3: cada estrategia candidata o en observación en MNQ (correlación y curvas) y las 8 mejores fuera de NQ (2026-11-26)

Estado: PRE-REGISTRO — adenda descriptiva de `PREREGISTRO.md`, commiteada antes de calcular. No cuenta pruebas: no elige reglas, sólo
ordena curvas ya medidas.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Pedido de Nico:** «tomá todas las estrategias candidatas a carteras o en observación como potencialmente rentables y correlalas una por
  una en el MNQ, y pasame las curvas. Luego pasame las curvas de las 8 mejores estrategias aplicadas a cualquier otro activo (excluido NQ)».

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36 escalas: todo en USD con 1 micro).

Diagnóstico de mecanismo: no aplica (sin grilla).

## Qué se calcula (fijo)
- **Unidad y ventana:** USD por día con 1 micro, neto de la fricción canónica del micro, de 2019-07 a 2026-09. Incluye todas las
  particiones (también HOLDOUT A5); el terminal no está abierto para estas series.
- **Estrategias en MNQ:**
  - de `cartera_nt8_20261125/MATRIZ_DIARIA_1MICRO`: T, R, Z, V, RQ5, Franklin, ES5N, SOM sin finde y C2_VZ;
  - A20, N y S de la re-medición con la traducción corregida (`remedicion_fs_il_20261121/FS_OPS_NQ_IL`), pasadas a MNQ (bruto − fricción
    MNQ, × 2 USD);
  - C2_EVRP de la corrida NT8 (`candidatas_nt8_20261125/corridas_nt8_nuevas/NT8_C2_EVRP_NQ.csv`), pasada a MNQ.
- **Para MNQ:** matriz de correlación mensual, y por estrategia USD/mes, t mensual, % de meses positivos y caída máxima.
  Curvas en paneles separados.
- **Fuera de NQ:** todas las columnas de la matriz en ES, YM, RTY y GC, más C2_EVRP en ES (MES). Se ordenan por t mensual y se grafican
  las 8 primeras, con su USD/mes y su caída máxima. Elegir por t sobre datos ya vistos es descriptivo y no habilita nada.

## Justificación económica
Ver qué componentes de las carteras se pisan en MNQ y qué hay fuera del NQ para diversificar.

## Cómo podría refutarse
Si las estrategias de MNQ están todas correlacionadas por encima de 0,5, no diversifican. Si fuera de NQ no hay ninguna con t > 2, no hay
alternativa.
