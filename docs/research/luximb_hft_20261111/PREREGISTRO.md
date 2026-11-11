# LUXIMB-HFT — impulsos del visor de LUX-IMB en NQ con ZONAS HFT en su 25 % inicial (cantidad como parámetro)

Estado: PRE-REGISTRO (2026-11-11, pedido de Nico). Escrito antes de generar ninguna tabla. Etapa **EF2 exploratoria**.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `LUXIMB_HFT`; linaje: `LUXIMB_GRILLA` (el objeto del impulso) y `HFT_CLUSTERS_INFO` (el detector de zonas HFT); hereda su
multiplicidad. Módulo `edgelab/research/luximb_hft.py` (cadena estándar; preflight en verde; tests `tests/research/test_luximb_hft.py`).

## Qué cambia respecto del visor
Mismo impulso (detector ESPEJO-IND en M1, marca en tiempo real, amplitud ≥ max(percentil causal, 60 pts), regla de cruce entero de
`luximb_grilla.marcas_segmento`) y misma operación (fade hacia el origen A). Las zonas son **HFT individuales** (`Z_CERT`, el mismo
detector y filtro que los clusters HFT: `niveles_sesion.zonas_del_dia`, sobre los ticks de cada día), no OG/VI.
**Parámetro:** n = 1, 2, 3, 5, 8, 12 zonas HFT atravesadas en el 25 % inicial del rango (y ≥ 50 % del total ahí); n = 0 es el
CONTROL (el mismo impulso sin condición de zonas). Detector D3_20 (el del visor) y D2_20 (impulso más chico); amplitud p60 y p80.

## Espacio de eventos
El de LUXIMB-HVN (`../luximb_hvn_20261111/PREREGISTRO.md` §2): se mide la marca en tiempo real (entrada al confirmar) y la vuelta
tras extenderse; el control sin zonas separa «impulso grande» de «impulso que nace en actividad HFT».

## Ejecuciones (motor único)
MERCADO stop 0,2 / 0,35 / 0,5 · D, objetivo 0,5 / 1,0 · D, sin o con BE a 0,25 · D (12); VUELTA e = 0,1 / 0,25, r = 0,1 / 0,2,
b = 0,1, objetivo A o mitad (8). Celdas: 28 definiciones × 20 = 560 por corte (`tablas.conteo`), registradas como
`luximb_hft/desarrollo` (× 2 cortes).

## Datos
NQ 2025-08-05 → 2026-03-31 (DESC) y 2026-04-01 → 2026-09-25 (REP), los dos ya mirados por el linaje (otras reglas). Lo que aparezca
sobre el nulo de la búsqueda y en los dos períodos se congela y se confirma en forward / holdout desde 2026-10-23 (una apertura).

## Hipótesis previa (antes de ver tablas)
- **H-HFT:** con stop 0,5·D y objetivo 1,0·D, D3_20 con n ≥ 3 rinde más R neto que su control (n = 0). Dirección esperada:
  incierta — la pista viva de HFT (`F-HFT-CLUSTER-GRANDE-NO-DEFIENDE-D`) dice que donde hubo actividad HFT el precio atraviesa más
  (el fade empeoraría); se informa en los dos sentidos.

## Justificación económica y cómo podría refutarse
- **Justificación:** las zonas HFT marcan dónde algoritmos rápidos intercambiaron mucho en poco tiempo; un impulso que nace
  atravesándolas podría ser flujo informado (continúa) o barrido de liquidez (revierte hacia A).
- **Refutación:** real − control ≈ 0 para toda n con potencia, o nada sobre el nulo de la búsqueda en DESC y REP.
- Limitación declarada: los datos sintéticos del preflight no producen zonas HFT; la causalidad de las zonas se prueba en
  `test_zonas_en_velas_causal`.
