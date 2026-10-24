# Resultados M8 — franjas adelante/atras del impulso: desbalance de zonas OG/VI (+ ML acotado)

Estado: MEDIDO. Veredicto: **SIN EFECTO** (Parte A: Holm >= 0,68 en las 4 vidas; Parte B: no pasa).
Manifiesto `MANIFIESTO_M8_FRANJAS_DESBALANCE_LUXIMB_20261020.md` (+ enmienda pre-desenlace `4631c7ac`). Codigo
`luximb_m8_features.py`, `luximb_m8_analisis.py`; variables `desc_m8/feat_NQ_ES.csv`; salida `RESULTADOS_M8.json`.
NQ desarrollo: 5.421 impulsos, 176 dias (P(vuelta 50 %) = 0,442). ES externo: 6.469, 192 dias (0,450).

## Parte A — desbalance (adelante vs atras), ajustado por vol_pre x franja horaria x tamano
| vida (velas) | NQ: P(vuelta) adelante - atras | IC 95 % | Holm | MDE80 | ES (descriptivo) |
|---|---|---|---|---|---|
| 100 | -0,4 pp | [-4,8, +4,1] | 1,0 | 6,4 pp | -3,5 pp [-8,3, +1,3] |
| 200 | +2,9 pp | [-1,2, +7,0] | 0,68 | 5,9 pp | 0,0 pp [-4,5, +4,3] |
| 500 | +0,2 pp | [-4,2, +4,6] | 1,0 | 6,3 pp | -2,2 pp [-6,6, +2,2] |
| 1000 | +1,4 pp | [-3,0, +5,5] | 1,0 | 6,0 pp | -1,8 pp [-5,7, +2,1] |
Ninguna vida separa; los signos no coinciden entre NQ y ES. Un desbalance que mueva la vuelta >= 6 pp queda descartado.

## Parte B — GBM con franjas vs GBM solo contexto (log-loss)
- NQ (CV por bloques de dias con purga): mejora -0,0013 [-0,0051, +0,0026] — las franjas **empeoran** levemente.
- ES externo (modelo congelado): +0,0034 [-0,0011, +0,0080] — no distinguible de 0.
- Log-loss de referencia (tasa base) 0,686: el contexto tampoco predice casi nada la vuelta.
B1 **no pasa**. Parte C (economica) no corresponde.

## Alcance
Muere: el desbalance de zonas OG/VI adelante/atras (franjas de 1R, vidas 100-1000) como predictor de la vuelta del 50 %
del impulso, en NQ y ES descubrimiento, con o sin ML acotado. Holdout y replicaciones intactos.

Aporte al referente: descarta con potencia (MDE ~6 pp, dos instrumentos, ML incluido) que la disposicion de OG/VI
arriba/abajo prediga la vuelta del impulso.
