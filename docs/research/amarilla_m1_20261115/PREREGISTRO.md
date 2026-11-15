# LUXIMB-AMARILLA congelada sobre M1 de 12 años (pre-registro, 2026-11-15)
Estado: VIGENTE. EF4 (reglas CONGELADAS: `docs/research/luximb_amarilla_20261111/r2/CONGELADAS_20261111_845c37fc.json`; sin búsqueda).
North Star sha256 16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345. Módulo `edgelab.research.luximb_amarilla_r2` sin cambios,
cadena estándar (`tools/tablas.py lanzar`) sobre `M1DK:NQ_M1_dukas` (M1 de Dukascopy USATECH como ticks; costos de NQ). Ventanas:
2012-01 → 2019-12, 2020 → 2023, 2024-01 → 2025-07 y 2025-08 → 2026-09 (validación: comparable con las tablas sobre ticks reales de NQ).
Hipótesis (las 3 congeladas): ctrl|W2|amarilla|e2|DESPUES con objetivo 50 % y 75 % y stop en el extremo, y la de caja sin filtro con
objetivo 75 %, todas con filtro VWAP diario lejos y hacia él.
Criterio (fijado antes): 1) validación: en 2025-08 → 2026-09 la media y el signo de M1 coinciden con los de ticks dentro de ~1 error
estándar; si no, no se mide el largo. 2) El largo NO da de baja (edges actuales): sirve para el mapa de régimen (rango nocturno, vol20,
tendencia 60 d, DST) y el encendido walk-forward contra azar (`edgelab/research/papel_regimen.py`). 3 hipótesis × 4 variables = 12
pruebas de régimen (registradas). Limitación: volumen por nivel aproximado con volumen de ticks (la caja amarilla depende de él).
