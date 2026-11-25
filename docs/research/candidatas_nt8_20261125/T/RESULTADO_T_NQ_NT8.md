# T (`T_stop100_BE15R_calFalse`) en NQ: control en NT8 contra Python

Estado: RESULTADO (control de ejecución; no confirma ni refuta el edge)  
Fecha: 2026-11-25  
Corridas NT8 (`EdgeLabCandidataFS`, NQ, M1 ETH, 2019-01-02 → 2026-09-30, veto ±2 / FOMC ±5): `NT8_T_NQ_fijo1.csv` (1 contrato
fijo) y `NT8_T_NQ_riesgo2000.csv` (sizing por riesgo, 1R = $2.000). Referencia: `PY_T_stop100_BE15R_calFalse_NQ.csv`
(`tools/candidata_referencia.py`). Comparación: `COMPARACION.json` (`tools/comparar_candidata.py`, calentamiento 12 meses).

1. **Paridad** (sesiones DESC/REP de A5, jul-2020 → sep-2026): 988 de 1.004 entradas iguales al minuto y lado (98,4 %), 2 a
   ±1 min, 14 sólo NT8, 16 sólo Python; en las emparejadas la diferencia mediana de puntos es 0 (total +47 pts en 988).
   Puntos en las mismas sesiones: NT8 12.638, Python 13.314 (−5 %).
2. **Veto de noticias**: NT8 cerró 45 operaciones por `NEWS_VETO`; Python anula 57 y cierra 37 (7,6 % afectadas). En los
   cierres por veto el precio difiere 5–10 pts (NT8 cierra al cierre de la vela previa a la ventana; Python, a la apertura).
3. **Frecuencia**: 18,4 ops/mes en NT8 (todos los meses) y 13,4 en Python (sin los meses de holdout A5): iguales en
   las sesiones comparables.
4. **Sizing por riesgo**: riesgo real / objetivo mediana 1,00 todos los años (p10 0,72–0,92, p90 1,00–1,24); contratos 4
   en 2019 → 1 en 2026; ninguna operación queda afuera (el stop nunca pasa de 100 pts).
5. **Dependencia de la época (hallazgo)**: el stop de T está topeado en **100 pts fijos** (herencia del vendedor, igual en
   Python). Operaciones con el stop en el tope: 0 % (2019), 16 % (2020-21), 50 % (2022), 44 % (2025), **77 % (2026)**; el
   stop mediano pasa de 0,59 % del precio (2020) a 0,34 % (2026). La regla opera con stops relativos cada vez más chicos.
   Probar un tope relativo al precio es una variante nueva: requiere pre-registro y conteo antes de correrla.

Con 1 contrato fijo de NQ el riesgo por operación es $1.215 (2020) a $1.980 (2022): 1 mini es 6–10 veces 1R de $200;
en MNQ equivale a 1 micro ≈ $120–200.
