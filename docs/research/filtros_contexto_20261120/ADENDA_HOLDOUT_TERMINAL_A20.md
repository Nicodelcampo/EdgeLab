# A20 NQ: apertura del holdout terminal (desde la sesión del 2026-10-01) pedida por Nico (adenda, 2026-11-20)

Estado: PRE-REGISTRO — adenda de `PREREGISTRO.md` (sección «Holdout terminal de A20 NQ»). Se commitea y la apertura se registra en
`HOLDOUT_VENTANAS.jsonl` ANTES de calcular cualquier operación con datos desde la frontera.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Decisión humana (Nico, 2026-11-20):** «Luego de eso abrí el último holdout en el caso de que no haya nada que cambiar o probar en
  cuanto a filtros».
  - FILTROS-CONTEXTO dio SIN_FILTRO (`RESULTADO.md`), así que se cumple la condición.
  - Nico levanta para esta apertura **dos compuertas**, y el registro las guarda:
    1. **K27:** la potencia es 0,08.
    2. **Una apertura por familia:** A20 pertenece a la familia `FUNDEDSYNC`, que ya abrió su terminal para T, Z y R
       (`FUNDEDSYNC::holdout_TZR_20261116`).
  - **A20 nunca se calculó con datos posteriores a la frontera.** `FUNDEDSYNC_HOLDOUT_OPS.csv` sólo tiene T (26), Z (7) y R (5), y el
    forward de la canasta B no incluye A20. La regla no está contaminada; lo que se gasta es multiplicidad de la familia, y se declara.

Antecedentes:
- A20-REGIMEN: INTERMEDIO.
- NOTA_HOLDOUT_A5: el holdout A5 de A20 no está limpio.
- Curva de A20 NQ: positiva desde 2022, +0,186 R/op en 2022-01 → 2026-09.
- FILTROS-CONTEXTO: SIN_FILTRO.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27/K42 potencia y alfa de la apertura, K48, K49 un nulo sin potencia no mata, K51, K56 episodios).

Potencia previa:
- **N fijo:** todas las operaciones de la fábrica en las sesiones del 2026-10-01 al 2026-11-16.
  - Son 32 sesiones completas en el M1 de NT8 local. Se excluye el 2026-10-07 por `SESIONES_EXCLUIDAS_HOLDOUT`, aunque el archivo lo
    trae completo. El 2026-11-17 está incompleto y queda fuera.
  - A unas 0,95 operaciones por sesión, N ≈ 30. El N real se publica.
- **Efecto del plan:** 0,093 R. Es la mitad del +0,186 de 2022–2026, que se eligió mirando la curva.
- **sd:** 2,36.
- **Potencia: 0,08.** Harían falta 3.982 operaciones (≈ 17 años de A20).
- **Lectura:** esta apertura es descriptiva. **No confirma ni refuta nada** (K49). La confirmación real es el e-proceso del forward.

Diagnóstico de mecanismo: no aplica. Es una sola regla congelada, sin grilla. Se publican las operaciones por semana (episodios) y la
curva.

## Qué se calcula (fijo)
- **Regla:** fábrica `A20_7_2_2.5_1.5` (`neto_pistas.FABRICA`), sin filtro.
- **Medida:** el mismo kernel (`neto_pistas._ms/_ops` con `fundedsyncstack`).
  - R = (resultado − fricción canónica de NQ) / riesgo del stop duro.
- **Datos:** M1 de NT8 de NQ leído sin el corte de la frontera **sólo después del registro**. Lleva un calentamiento desde el 2026-01-01.
- **Control de paridad:** las operaciones del calentamiento (2026-03 → 2026-09) se comparan con `RZ_OPS` de la fábrica, que ya se
  conocían. Se publica la coincidencia; si no coinciden, el resultado no se lee.
- **Prueba:** media de R > 0, bootstrap por sesión, p de una cola. Se informan además R/mes, aciertos y la curva.
- **Lectura:**
  - CONFIRMA si p < 0,05, imposible en la práctica con esta potencia;
  - NO_CONCLUYENTE si la media es > 0;
  - EN_CONTRA_SIN_POTENCIA si la media es ≤ 0, con su MDE.
  - Ninguna lectura cambia la regla.
- **Una sola apertura** (cid `FUNDEDSYNC::holdout_terminal_A20_NQ`). Nunca se usa para elegir, ajustar ni reintentar.

## Justificación económica
- **Mecanismo:** el de A20-REGIMEN. Sigue tendencias intradía de NQ con SuperTrend y un stop duro, y gana con pocas operaciones grandes en días de tendencia.
- **Por qué ahora:** la fricción relativa baja desde ≈ 2018 dejó el neto positivo desde 2022.
- **Etapa EF5:** confirmación en el holdout terminal, sin potencia.

## Cómo podría refutarse
- Con esta potencia, no puede. Una media muy negativa (≤ −0,5 R con p < 0,05) sería una señal de alarma para el forward, no una muerte.
