# VWAP banda 3 (reversión): mapa de régimen — pre-registro (2026-11-15)
Estado: VIGENTE. EF3. Familia M1_INTRADIA. Motivo: la reversión desde la banda 3 mostró dosis frente a la banda 2 en bruto en 2012–2019 y
2025-08 → 2026-09, y fue negativa en 2020–2023 (RESULTADO.md): comportamiento de régimen. Principio «edges actuales»: el pasado no mata.
Datos: operaciones por día de `vwap_banda` (mismas reglas) en Nasdaq, Dow, S&P y DAX (Russell fuera hasta corregir su spread).
Variables (las mismas de ASIA, fijadas antes; causales): rango nocturno relativo (tercil contra 250 días), vol20 (tercil), tendencia 60 d,
DST; para el DAX la «noche» es 18:00→09:30 NY igual que el resto (horario del servidor).
Pruebas: (a) mapa por estado, en bruto y neto, por tramo; (b) encendido walk-forward trimestral contra siempre y contra estados al azar
(`edgelab/research/papel_regimen.py`); variantes: REV con objetivo VWAP y stop extremo o banda 4, banda 3 y su control banda 2.
Multiplicidad: 4 variables × 4 variantes × 4 activos = 64 pruebas (registradas). Refutación: ningún estado ordena el resultado de forma
monótona en ≥ 3 tramos, o el encendido no supera al azar.
