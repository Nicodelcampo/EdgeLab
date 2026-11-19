# CARRIL2-CRASH: filtro de crash definido de antemano (curva de VIX invertida) para la reversión corta (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Pedido de Nico:** «filtro de crash definido de antemano para la reversión corta». Sólo cuenta de broker (varios días).
- **Origen de la hipótesis (declarado):** `MIRADA_HUMANA_20261119.md`: IBS, Double Seven y el pico de VIX pierden concentrado en meses de
  crisis desde 2018 (meses elegidos mirando la historia). Por eso la prueba NO usa DESC 2018+: usa DESC 2011–2017 (primero) y REP (después).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC 2011-01 → 2017-12; EF4 en REP 2011-01 → 2025-07 (una lectura con LORD++ de `CARRIL2_A5`, sólo si T1 nomina y la
  potencia en días es ≥ 0,8, K49). **Familia:** `CARRIL2_A5`.
- **Herramienta:** `tools/carril2_crash.py desc|rep` sobre las operaciones ya calculadas del lote 1 (`OPS.csv.gz`: C2_IBS, C2_D7) y del lote 2
  (`OPS_LOTE2.csv.gz`: C2_VBB); VIX9D y VIX de `cboe_volatility_daily.parquet`. `registro_global.exigir_contada` al inicio.

Antecedentes: CARRIL2-LOTE1/LOTE2/CIERRE, RE_INDAGACION, MIRADA_HUMANA (episodios de crisis), F-COMPRESION-VOL-CRECE (VIX9D/VIX como estructura).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K48 causalidad, K49, K51, K55/K56).

Diagnóstico de mecanismo: una sola perilla fijada de antemano (VIX9D/VIX ≥ 1 al último cierre CBOE anterior a la sesión de entrada); sin
grilla de umbrales. Se publica la descomposición por meses (Episodios) de las operaciones filtradas y de las que quedan.

Potencia previa: IBS+D7+VBB en DESC 2011–2017 ≈ 650 operaciones; con backwardation en ≈ 10–20 % de las señales (≈ 70–130), ee del contraste
≈ 0,10–0,12 R: sólo detecta diferencias grandes (≈ 0,3 R). REP con su plan de potencia.

## Justificación económica
- La reversión corta compra ventas forzadas que se agotan en días. En un crash (curva de VIX invertida: la volatilidad de 9 días supera a la de
  30) las ventas son de desapalancamiento sistemático y siguen: comprar ahí es «agarrar el cuchillo». Con curva normal, la reversión funciona.

## Prueba
- **T1 (DESC 2011–2017, IBS+D7+VBB juntas, ES/NQ/YM/RTY/GC según cada regla):** contraste R neto (curva normal: VIX9D/VIX < 1) − R neto
  (invertida: ≥ 1) > 0; bootstrap por sesión, p unilateral < 0,05 → nominada. Se reporta además el R neto de la regla filtrada (sólo curva normal).
- **T2 (REP):** el mismo contraste, una vez, con LORD++, sólo si T1 nomina y hay potencia.
- **Cómo podría refutarse:** contraste ≤ 0 en DESC 2011–2017, o no confirmado en REP con potencia.
- **Contador:** 1 prueba en `CARRIL2_A5` (T1); T2 es la lectura de confirmación con el nivel LORD++ de la familia.
