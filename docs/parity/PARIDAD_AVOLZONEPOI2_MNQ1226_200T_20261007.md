# Paridad aVolZonePOI2 — MNQ 12-26, 200 tick (2026-10-07) — **PASS exacto**

- Oráculo NT8: `data/nt8_oracles/avolzonepoi_MNQ1226_200t_20260715_20260930.csv`, logger `LogPath` de
  `nt8/aVolZonePOI2.cs`, con los parámetros por defecto (bloque 10, ×2, gap 1, mín. 2, Suma, franja 15 min CT, p95,
  20 sesiones, mín. 20 muestras, OB 100 barras / 3 alturas / 8 ticks / 2 %).
- Réplica: `edgelab/bridge/indicators/avolzonepoi2.py`. Script: `tools/paridad_avolzonepoi2.py`. JSON:
  `paridad_avolzonepoi2_MNQ1226_200t_20261007.json`.

| | NT8 | Python | iguales |
|---|---|---|---|
| bloques (barra, hora, niveles, mejor score, franja, sesión) | 45.916 | 45.916 | 100 % |
| zonas (barra, bajo, alto, score, umbral) | 2.723 | 2.723 | 100 % |
| clasificación orderblock (estado y barra de decisión) | 2.722 (641 OB) | 2.722 (641 OB) | 100 % |

## Hallazgo del lado de los datos: el chart fusiona contratos
El chart está en **Merge back adjusted**: hasta el roll (sesión del 14-09, desde las 17:00 CT del 13-09) las barras son
del **09-26**, y sus precios están desplazados +299,75 puntos (offset único en todas las zonas anteriores al roll).
- Con sólo los ticks de 12-26, julio casi no tiene datos (era el contrato trasero) y la paridad falla. No es un error
  del indicador.
- La réplica arma la misma serie fusionada: 09-26 hasta el roll y 12-26 después. Los scores dependen sólo del volumen,
  así que el ajuste de precio no los cambia. Las zonas anteriores al roll se comparan sumando el offset.
- **Para research:** mientras se use un chart fusionado, los precios de zona anteriores al roll son precios ajustados,
  no los que se operaron.

## Incidente operativo
La primera corrida que cargó dos contratos completos a la vez coincidió con un cuelgue de la PC (16 GB). El script
ahora concatena sólo hora, precio y volumen.
