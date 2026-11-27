# SUPERCARTERA v2: Integración Multi-Frente Ortogonal (CME + Carril 2 + CRIPTO-PIT v3 + Frentes Ortogonales) a Volatilidad Idéntica y CSCV/Bootstrap (pre-registro, 2026-11-27)

Estado: PREREGISTRO — campaña pre-registrada antes de integrar `CRIPTO-PIT v3` y `FRENTES-ORTOGONALES-20261127`. **`HOLDOUT A5` de todas las familias y sesiones `>= 2026-10-01` permanecen estrictamente SELLADOS (`NaN`).**

- **Pedido de Nico (2026-11-27):** aumentar número de frentes/estrategias decorrelacionadas, estabilidad y relación retorno/drawdown mediante diversificación sin forward y comparación auditable.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- **Etapa EF2.** Familia: `CANASTA_AMPLIA`. **Pruebas:** `4` (`Super_v2_EQ`, `Super_v2_HRP_Weekly`, `Super_v2_NoCME_EQ`, `Super_v2_Core_TRZV_EQ`).

Cambio respecto a iteración previa (`auditoria_claude_20261127/MARCO_SIN_FORWARD.json`): se incorpora `CR3_Canasta_InvVol` (`CRIPTO-PIT v3`, que suma `CR3_BAB_LowVol_Stag5d` ortogonal con `corr = -0.217` vs `XSMOM`) junto con los candidatos de `FRENTES-ORTOGONALES-20261127` (`FundedSync O qty=1 MNQ` y `Global_VolComp_M1DK`) bajo **regla fija causal** (entran si su `DESC media_mes > 0` antes de abrir `REP`, excluyendo explícitamente `FutNoEq_v2` por roll sin back-adjustment en Yahoo), con **escalado idéntico a `10%` anual propio**, mapeo semanal `W-FRI` / mensual `M` libre de spike de lunes, CSCV separado entre limpio (`Sin CME`) y descriptivo (`Con CME`, `upstream_selection_caveat=True`), estrés `CME 0.5x` y cálculo de potencia conjunta sobre holdouts sellados.

Antecedentes:
- `docs/research/auditoria_claude_20261127/MARCO_SIN_FORWARD.json` y `RESULTADO.md`
- `docs/research/cripto_pit_v3_20261127/PREREGISTRO.md` y `RESULTADO.md`
- `docs/research/frentes_ortogonales_20261127/PREREGISTRO.md`

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27 potencia antes de abrir holdout, K36 causalidad por prefijo, K51 registro global, cero lectura de `>= 2026-10-01` ni `HOLDOUT A5`).

Potencia previa: no abre ningún `HOLDOUT A5`. Evalúa la potencia estadística conjunta del pool no-CME (`Carril 2 63m` + `Cripto v3 18m` [+ `Global_VolComp 63m` si califica]) para verificar antes de cualquier eventual apertura única si alcanza `>= 0.70` bajo `0.7x` del efecto medido.

Diagnóstico de mecanismo: cero optimización sobre `REP` ni `HOLDOUT`. Cada frente se estandariza por su propia `SD` mensual de `DESC` en la ventana común (`2021-01..2026-09`). Los pesos `HRP` se ajustan semanalmente (`W-FRI`) con covarianza `LedoitWolf` únicamente sobre semanas `DESC`. Las `4` variantes declaradas (`EQ`, `HRP_Weekly`, `NoCME_EQ`, `Core_TRZV_EQ`) se evalúan en igualdad de condiciones en `DESC`, `REP`, `CSCV (12,870 splits)`, `DSR (N=1..5000)`, `Bootstrap 20k semanal @ 10% vol` y estrés `CME 0.5x`.

## Justificación económica
1. Combinar frentes de distinta microestructura (intradía CME, swing/volatilidad US, cross-section crypto momentum + low-vol `BAB`, y frentes globales/overnight si sobreviven `DESC` y fricción real) reduce la varianza por el factor $\approx \sqrt{1/N + (1 - 1/N)\bar{\rho}}$ sin depender de sobreajuste paramétrico.
2. Evaluar todas las carteras normalizadas exactamente a `10%` de volatilidad anual propia elimina ilusiones de drawdown derivadas de escala de apalancamiento.

## Cómo podría refutarse
1. Si la super-cartera `Super_v2_EQ` / `HRP` no mejora el `Sharpe`, `Calmar@10%vol` ni la mediana OOS de `CSCV` / `Bootstrap 20k` respecto a sus componentes individuales y a `Marco Sin Forward v1`.
2. Si el bloque limpio no-CME presenta `PBO > 0.50` o mediana OOS `<= 0` en `CSCV (12,870 splits)` en Kaggle.
