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
- Real y nulo corren con el MISMO presupuesto: parada automática de SQX a las 6 h (`StopCondition time-limit`); el K de cada uno se lee de
  `get_project_status` y va al contador. Si los K difieren más del doble, el umbral del nulo se escala por √(2·ln K) (máximo de K normales).
- Enmienda antes de lanzar (2026-11-14): las plantillas traían `ExitOnFriday` activo (cerraba toda posición el viernes 23:00); se apagó
  junto con `ExitAtEndOfDay` en los 10 proyectos (macro = tenencia de varios días; requiere cuenta swing). Se activó
  `RealisticGapsHandling` (el stop atravesado por el gap del domingo se llena al precio después del gap) y el contrato suma el control de gaps. `estado` vuelca K al contador global (familias SQX_<idea>).
- Se exportan TODAS las aceptadas por SQX (filtro de SQX laxo: sólo AvgTradesPerMonth > 0) del real y del nulo.

## Evaluación (fijada antes)
1. Umbral del nulo = p95 del máximo t (R por operación) entre las estrategias del NULO; ninguna estrategia real se mira sin él.
2. Candidatas = reales con t > umbral. Sobre ellas, el contrato de calidad completo: frecuencia, bloques, drawdown, concentración; después,
   UNA vez, el tramo reciente 2024-01 → 2025-07 y otros mercados de su clase sin re-optimizar; correlación y diversificación de cartera.
3. Línea de base: si LIT-TSMOM no supera a la plantilla genérica de reversión ni a su nulo, el mecanismo no agrega nada.

## Justificación económica y cómo podría refutarse
Ver fichas LIT-TSMOM y SQX-PLANTILLA-REVERSION en `docs/research/ideas/BANCO_IDEAS.md`. Refutación del lote: ninguna estrategia real
supera el p95 de su nulo, o las que lo superan fallan el tramo reciente.

## Enmienda 2 (2026-11-14 22:4x UTC, decisión de Nico): nada abierto el fin de semana
Cierre obligatorio el viernes 23:00 (hora del servidor de datos, EST+07 = 16:00 NY) en los 10 proyectos; se mantiene la tenencia nocturna y el
llenado realista de gaps. El par S&P D1 ya lanzado se detuvo a los ~4 min (13.154 y 14.033 generadas, contadas como pruebas, databank
vaciado sin mirar) y se relanza con esta configuración.

## Enmienda 3 (2026-11-14, decisión de Nico, antes de lanzar los pares 2–5): parada a las 2 h
El máximo del nulo crece ~√(2·ln K): de ~400 mil a ~1,2 millones de generadas casi no cambia la vara. Los pares 2–5 paran a las 2 h (real y
nulo con el mismo presupuesto); el par 1 (S&P D1, ya corriendo) mantiene las 6 h pre-registradas. Los parciales vistos del par 1 no influyeron.

## Enmienda 4 (2026-11-14, decisión de Nico): se cancela el par S&P D1 de 6 h y se fija el orden por información
El par S&P D1 se detuvo a ~110.000 generadas por proyecto (contadas en el registro; databanks vaciados sin analizar) y pasa a 2 h. Orden de
lanzamiento (de más a menos informativo; un par a la vez, cada uno 2 h):
1. Ideas de la literatura directo en Kaggle (`docs/research/macro_literatura_20261114/`), en paralelo a SQX: lo más barato y de prior más alto.
2. LIT-TSMOM S&P D1: idea central y prueba de punta a punta del circuito SQX → EdgeLab.
3. LIT-TSMOM Oro D1: otra clase de activo (diversificación).
4. LIT-TSMOM Crudo WTI H4: tercera clase, otro marco temporal.
5. SQX-PLANTILLA-REVERSION S&P H4: línea de base (¿el mecanismo le gana a la búsqueda genérica?).
6. LIT-TSMOM S&P H4: el menos informativo (mismo activo que el 2).

## Nota (2026-11-15 06:3x): par crudo H4 FALLIDO
SQX se detuvo por «Exceeded memory limit» a los 44 min (313 y 330 generadas, contadas). No se evalúa; se relanza cuando SQX tenga más memoria (-Xmx) y la laptop no esté compartida.
