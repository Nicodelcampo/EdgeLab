# Pre-registro — U1-CONFIRMA: U1 sobre EURUSD con confirmación cruzada desde GBPUSD

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-26.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Campaña `U1-6E-CONFIRMA-GBP` (familia `U1_6E_CONFIRMA_GBP`), embudo automático. Etapa: **EF2/EF3** (DESC → … → OOS); confirmación en el
holdout a N fijo. Aprobada por Nico el 2026-10-26 («apruebo»), junto con `U1-6B-GRILLA` y `U1-6B-FUT-GRILLA`.

## 1. Justificación económica
Un movimiento que comparten EURUSD y GBPUSD es del dólar (factor común: noticias de EE. UU., flujo macro) y debería sostenerse; uno propio
del euro se parece más a ruido de liquidez y debería revertir antes. Si U1 (regreso a racimos de huecos LUX-IMB) tiene algo en EURUSD,
la confirmación cruzada debería separar dónde.

## 2. Grilla
La de U1-CFD (`PREREGISTRO_U1_CFD.md` §2, 4.478.976 celdas) × eje `confirma` (eq_any, 4 celdas: común / propio / GBP lidera /
cualquiera = sin filtro) → **17.915.904 celdas por canal**. Definición exacta y causal en `edgelab/research/u1_confirma.py`
(L = 15 min, retornos en unidades del rango M1 mediano de la sesión anterior de cada instrumento; umbrales ½ fijados antes de correr).
El eje se eligió ANTES de mirar la réplica de U1-6E-GRILLA (cuyo DESC sí se miró: 0 candidatas, 20 pistas), y no se ajusta después.

## 3. Datos, ejecución y costos
Sensor y ejecución DK:EURUSD (como U1-6E-GRILLA; costos de 6E de `edgelab/costos.py`), confirmador DK:GBPUSD. DESC 2024-01-02 →
2026-03-31; réplica/OOS 2026-04-01 → 2026-09-30; holdout desde 2026-10-01 (no se toca).

## 4. Multiplicidad y linaje
Hereda el linaje de `U1_6E_GRILLA` (LINAJES.jsonl): su DESC ya se miró. Cuenta en el registro global vía el embudo (PREFLIGHT).

## 5. Cómo podría refutarse
Ninguna celda nominada por FDR q 0,10 ni pista confirmada en lote a réplica; o, en la réplica, las celdas «común» y «propio» no se
distinguen entre sí ni de «cualquiera» (la confirmación no agrega nada): muere para U1 sobre EURUSD con GBPUSD como confirmador —
no para la confirmación cruzada en general ni para otros pares.
