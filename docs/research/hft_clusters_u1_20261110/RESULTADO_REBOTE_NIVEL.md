# REBOTE_NIVEL_SESION — resultado (banco de eventos, réplica abr → sep 2026)

Estado: RESULTADO (2026-11-11). Pre-registro: `PREREGISTRO_REBOTE_NIVEL.md`. Banco: `docs/research/banco_eventos/REBOTE_NIVEL_SESION/`
(HIPOTESIS_CONGELADAS.json, RESULTADO.json, RECOMENDACIONES.md). Tabla: `HFTC_niveles_replica.csv` (no mirada antes del banco). El
kernel se construyó con la versión 72c936f5 de `niveles_sesion.py`; la versión actual da filas idénticas para niveles «reloj»
(verificado en 3 sesiones sintéticas; aceptado con justificación en el JSON).

## Muestra
29.560 primeros regresos a niveles de la sesión (cada 600 s): NQ 12.087, GC 7.334, YM 3.722, RTY 3.713, ES 2.704; 604 sesiones.
Mitades: A 14.671 eventos (301 sesiones), B 14.889 (303). Calibración del método sobre esta tabla: 1/40 permutaciones con alguna
nominada (2,5 %).

## Un nivel de la sesión NO rebota (con potencia)
Rebote medio (−rompe, carrera ±X): **−0,007** (2/5 bloques, p 0,90); NQ −0,026, GC −0,001, ES +0,004, RTY +0,013, YM +0,013. Con
casi 30.000 eventos el error es ≈ 0,006: un rebote de +0,08 como el del control de los clusters en DESC queda descartado.

## «Sin zonas» no cambia nada (hipótesis previas, toda la tabla)
| Previa (rebote) | n | Estimación | se | p | vs resto | Bloques |
|---|---|---|---|---|---|---|
| sin zona a ≤ 1 X en 30 min | 8.518 | −0,017 | 0,010 | 0,96 | −0,013 | 1/5 |
| sin zona en 60 min | 5.447 | −0,023 | 0,013 | 0,97 | −0,019 | 1/5 |
| sin cluster vivo cerca | 25.149 | −0,005 | 0,006 | 0,81 | +0,014 | 1/5 |
Por estrato de distancia a zonas (30 min): < 0,5 X −0,005; 0,5–1 X +0,014; > 1 X −0,017. Nada monótono.

## Exploración y mitad B
2.116 celdas en A; las 3 elegidas y el modelo aditivo, en B: nada (máximo +0,026, p 0,23). Las «mejores» de A son de +0,05 en el
sentido de ruptura o celdas de 3–20 eventos: ruido con 2.116 celdas.

## Lectura
1. El rebote del control de los clusters en DESC (+0,07–0,10) **no se transporta** a niveles de reloj en abr–sep. O era propio de
   aquellos pseudo-clusters/período, o era azar de DESC; el banco lo descarta con potencia para este evento.
2. La distancia a las zonas HFT (espacio × tiempo) no modula el rebote: el mecanismo propuesto («la liquidez pasiva defiende salvo
   que las zonas la hayan consumido») no aparece.
3. OP-1 pierde su premisa: su análisis se corre igual (pre-registrado) pero se espera ≈ 0 bruto y negativo neto.
4. Queda en pie lo que decide la confirmación congelada de «no defiende» (real − control con clusters), que es otro contraste.
