# AUDITORIA-EXCLUSIONES: las fechas fijas del vendedor sacaban días malos de T (sesgo chico, −0,005 R) y no inflan R (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (1 prueba en `FUNDEDSYNC`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `RESULTADO.json`, `OPS.csv.gz`. NQ, M1 de NT8, desarrollo.

| Módulo | Días excluidos con operación | R de esos días | Percentil vs días al azar (2020–26) | R medio 2021–26 sin → con | Veredicto |
|---|---|---|---|---|---|
| T (FtmEngine) | 24 (16 «datos degradados», 8 vencimientos) | −5,39 (−0,22 por día; degradados −0,26, vencimientos −0,16) | **4,7 %** | +0,186 → **+0,181** | **SESGO_VENDEDOR** (percentil < 10 %) |
| R (AtrPhase, stop 0,25 × ATR20) | 8 (3 días normales, 5 feriados/medias jornadas) | +1,80 (días normales +1,92 / +0,99 / +0,38; feriados −1,03, +1,02, −1,02, −1,02, +0,56) | 32,5 % | +0,520 → +0,508 | INOCUA |

- **T:** el vendedor excluye días que en nuestros datos no están degradados, y esos días fueron peores que el azar. En vivo no se puede saber
  de antemano que un día tendrá «datos degradados»: la versión operable los incluye. **Corrección:** T 2021–2026 = **+0,181 R/op** (antes
  +0,186). No cambia el veredicto de régimen (la diferencia es 0,005 R, 3 % del efecto).
- **R:** los tres bloqueos de días normales sacaban días GANADORES; no hay sesgo a favor. Los feriados sí se pueden excluir en vivo con el
  calendario (regla aplicable).
- **Forward:** las listas no tienen fechas posteriores a 2026-07-31; REGIMEN-FORWARD no se ve afectado.
- **Lección:** toda estrategia externa con listas de fechas fijas se audita así antes de confiar en su backtest (posible selección del
  vendedor con el diario del lunes).

## Anexo: riesgo de T en los archivos del CFD (verificación, 2026-11-19)
- `cadena/FUNDEDSYNC_OPS.csv.gz` (desarrollo en USATECH) y `cadena/FUNDEDSYNC_HOLDOUT_OPS.csv` traen operaciones de T con riesgo ≈ 0 (p. ej.
  2024-01-08: 0,009 contra 90,6 en futuros): son anteriores a la corrección de la auditoría del 16-nov (`stop_price` era el stop activo al
  salir). Con ellos el R de T en el CFD sale +0,65 / +1,97 (2012–20 / 2021–26) contra −0,04 / +0,18 en futuros: **no usar el R de T de esos
  archivos**. El kernel vigente (`tools/kaggle_grilla/fundedsync_main.py::operaciones`) ya usa clip(rango 09:30–09:45 × 1,25, 2, 100), así que el
  forward de REGIMEN-FORWARD sale corregido, y `regimen_forward.py` frena si aparece un riesgo de T < 2. Los análisis de Lucid usan USD, no ese
  riesgo. Lado y P&L en puntos coinciden con futuros en 94 % de los días comunes desde 2021 (correlación de R 0,63 por el riesgo roto).
