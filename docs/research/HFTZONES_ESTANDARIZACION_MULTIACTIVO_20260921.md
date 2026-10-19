# HFTZonesNQPureV4 en todos los activos — estado medido y decisión pendiente

> 2026-09-21. Target-free: solo conteos de zonas/candidatos de los bundles ya generados. Sin retornos, sin holdout.

## Lo que ya existe
- `edgelab/bridge/indicators/hftzones_universal.py` envuelve el motor congelado (`hftzones_nq.py`, espejo de `HFTZonesNQPureV4`) y
  expone un único perfil: `NQ_LITERAL_TRANSFER` (los umbrales de NQ tal cual).
- Los 11 activos ya tienen bundles con ese perfil (`tools/build_multiasset_25t_hft_bundles.py`), todos marcados
  `PARITY_ABSTAIN` y `PARAMETERS_UNCALIBRATED` (excepto NQ: `NQ_LITERAL_PROFILE`).
- Paridad certificada solo en NQ (HP-007 V2, 5.438/5.438, 38 campos). Ningún otro activo tiene oráculo NT8.

## Medido: el motor es portable, los umbrales no
Perfil NQ literal sobre todos los bundles (`viewer/nt8_bridge/bundles/*.manifest.json`, suma de sesiones):

| Activo | Ticks | Candidatos / 1k ticks | Zonas / 1k ticks | Aceptación | Filtro que más rechaza |
|:--|--:|--:|--:|--:|:--|
| ZB | 27,4 M | 48,9 | **12,90** | 26,4 % | pasos 70 % |
| 6J | 14,7 M | 163,5 | 5,45 | 3,3 % | pasos 74 % |
| MES | 168,0 M | 120,9 | 4,84 | 4,0 % | pasos 74 % |
| ES | 264,0 M | 73,1 | 4,78 | 6,5 % | pasos 55 % |
| 6B | 7,8 M | 200,5 | 4,59 | 2,3 % | pasos 82 % |
| 6E | 18,8 M | 174,0 | 4,27 | 2,5 % | pasos 77 % |
| MBT | 4,6 M | 273,1 | 2,47 | 0,9 % | pasos 92 % |
| MNQ | 334,8 M | 108,1 | 1,67 | 1,5 % | pasos 69 % |
| NQ | 113,5 M | 191,5 | 0,95 | 0,5 % | pasos 85 % |
| GC | 38,3 M | 244,0 | 0,82 | 0,3 % | pasos 90 % |
| YM | 21,2 M | 272,1 | 0,42 | 0,15 % | pasos 93 % |

La densidad de zonas por tick varía **30×** entre ZB y YM con los mismos umbrales. Con el mismo texto de indicador,
«zona HFT» no significa lo mismo en cada activo: los umbrales de tiempo (ms), volumen (contratos, contratos/s) y pasos
están en unidades de NQ. Eso vuelve incomparables las conclusiones entre activos y sesga cualquier campaña que las junte.

## Límites
- Sin oráculo NT8 por activo no hay paridad: solo se puede afirmar que el motor corre, no que iguale al indicador.
- Los conteos vienen de fragmentos y contratos distintos por activo; sirven para ver el orden de magnitud, no para calibrar.

## Decisión pendiente (Nico)
Cómo se define «el mismo indicador» en todos los activos. Ver la pregunta en la conversación del 2026-09-21.
