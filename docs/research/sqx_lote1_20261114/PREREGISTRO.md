# SQX lote 1 — pre-registro (2026-11-14)

Estado: VIGENTE, preparado y SIN LANZAR. Etapa EF2 (exploratorio, generación). North Star sha256
16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345. Infra: `docs/infra/SQX_MT5_EDGELAB_INFRA.md`; contrato de calidad:
`docs/infra/CONTRATO_CALIDAD_ESTRATEGIAS.md`. Manifiestos: `sqx/corridas/<id>/manifest.json`.

## Proyectos (cada real con su NULO gemelo: mismo Builder sobre la serie sintética del mismo activo, `sqx/nulos/`)
| Idea (banco) | Activo | TF | Plantilla | Real | Nulo |
|---|---|---|---|---|---|
| LIT-TSMOM | S&P (USA500) | D1 | TrendFollowing | LIT-TSMOM_SP_M1_dukas_D1_202611142222 | LIT-TSMOM_NULO_SP_M1_dukas_H1_s1_D1_202611142222 |
| LIT-TSMOM | S&P | H4 | TrendFollowing | LIT-TSMOM_SP_M1_dukas_H4_202611142222 | LIT-TSMOM_NULO_SP_M1_dukas_H1_s1_H4_202611142222 |
| LIT-TSMOM | Oro | D1 | TrendFollowing | LIT-TSMOM_XAUUSD_M1_dukas_D1_202611142222 | LIT-TSMOM_NULO_XAUUSD_M1_dukas_H1_s1_D1_202611142223 |
| LIT-TSMOM | Crudo WTI | H4 | TrendFollowing | LIT-TSMOM_LIGHTCMDUSD_H4_202611142223 | LIT-TSMOM_NULO_LIGHTCMDUSD_H1_s1_H4_202611142223 |
| SQX-PLANTILLA-REVERSION (línea de base) | S&P | H4 | Mean-Reversal | SQX-PLANTILLA-REVERSION_SP_M1_dukas_H4_202611142223 | SQX-PLANTILLA-REVERSION_NULO_SP_M1_dukas_H1_s1_H4_202611142223 |

## Diseño común (aplicado por `tools/sqx_corrida.py`, verificado en SQX)
Construcción 2012-01-20 → 2019-12-31 (OOS interno de SQX 2017–2019, sólo informativo); generación ALEATORIA; ≤ 3 condiciones; SL 2–5 ATR,
TP 2–8 ATR; riesgo fijo 1.000 USD por operación (R = P/L / 1.000); costos del instrumento Dukascopy (spread, swap); datos ≤ 2026-09-29.

## Ejecución
- Real y nulo corren con el MISMO total generado (K): se detienen al llegar a 20.000 estrategias generadas cada uno (o al tope de 6 h; si
  uno no llega, el otro se recorta a su K). `estado` vuelca K al contador global (familias SQX_<idea>).
- Se exportan TODAS las aceptadas por SQX (filtro de SQX laxo: sólo AvgTradesPerMonth > 0) del real y del nulo.

## Evaluación (fijada antes)
1. Umbral del nulo = p95 del máximo t (R por operación) entre las estrategias del NULO; ninguna estrategia real se mira sin él.
2. Candidatas = reales con t > umbral. Sobre ellas, el contrato de calidad completo: frecuencia, bloques, drawdown, concentración; después,
   UNA vez, el tramo reciente 2024-01 → 2025-07 y otros mercados de su clase sin re-optimizar; correlación y diversificación de cartera.
3. Línea de base: si LIT-TSMOM no supera a la plantilla genérica de reversión ni a su nulo, el mecanismo no agrega nada.

## Justificación económica y cómo podría refutarse
Ver fichas LIT-TSMOM y SQX-PLANTILLA-REVERSION en `docs/research/ideas/BANCO_IDEAS.md`. Refutación del lote: ninguna estrategia real
supera el p95 de su nulo, o las que lo superan fallan el tramo reciente.
