# VWAP banda 3 (reversión): mapa de régimen — resultado (2026-11-15)
Estado: RESULTADO. Pre-registro: `PREREGISTRO_REGIMEN_VWAPB.md`. Datos: `REGIMEN_VWAPB.json` (105.138 operaciones por día en Nasdaq, Dow,
S&P y DAX, 2012 → 2026-09; kernel `edgelab-vwapb-ops`).
## Veredicto: régimen NO detectable (refutación pre-registrada)
- Ninguna variable (rango nocturno, vol20, tendencia 60 d, DST) ordena el resultado de forma monótona en ≥ 3 tramos en ningún índice:
  los signos por estado cambian de tramo a tramo (p. ej. Nasdaq banda 3 / stop extremo, noche baja→alta: 2012–2019 −0,08/+0,16/+0,04;
  2020–2023 −0,43/+0,09/+0,13; 2024→2025-07 +0,18/−0,63/+0,06; 2025-08→2026-09 +0,02/+0,62/−0,13).
- Encendido walk-forward contra estados al azar: 1 de 32 combinaciones con p < 0,05 (Dow, stop banda 4, tendencia 60 d, p 0,008) —
  lo esperable por azar con 64 pruebas registradas.
- DAX: positivo en bruto en 2025-08→2026-09 en todos los estados (+0,35 a +0,69 R), sin orden por régimen (el rango nocturno no se calcula
  después de 2020 por el horario del CFD en H1).
- Lectura: la dosis banda 3 > banda 2 en bruto existe en 2012–2019 y en el último año, pero el cambio de signo de 2020–2025 no se explica
  con estas variables: no hay forma de saber a tiempo cuándo encenderla. Neta, en CFD, no paga.

## Corrección (auditoría 2026-11-16): el DAX estaba leído con 2–3 h de desfase
El CSV del DAX viene en UTC y se leyó como hora del servidor: sus «09:30–15:55 NY» eran otra ventana. Re-medido (`auditoria_corridas_20261116/
VWAPB_OPS_TZ.csv.gz`, banda 3, reversión): 2012–2019 bruto +0,106 · 2020–2023 **+0,197** · 2024→2025-07 +0,048 · **2025-08→2026-09 −0,092**
(antes +0,472). La frase «DAX positivo en bruto en 2025-08→2026-09 en todos los estados» queda **retirada**. NQ, S&P y Dow no cambian. El holdout
de la familia (NQ + YM) no usó el DAX.
