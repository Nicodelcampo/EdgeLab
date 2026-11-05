# Holdout de octubre en R (2026-11-02)

Estado: VIGENTE (descriptivo). Pedido de Nico: «calculá cuánto R se obtendría si hubiese corrido todas las estrategias en el período del
holdout, y cuánto R en promedio por operación». Herramienta: `tools/holdout_en_r.py`.

**Método.** Se re-corrieron las mismas 16 reglas congeladas (código causal) sobre el sellado 10-01 → 10-30, guardando el riesgo inicial
de cada operación (entrada real a stop). R = neto (con fricción) / riesgo. Cuentan sólo las sesiones válidas. El P&L coincide con la
apertura conjunta.

| Regla | Operaciones | R total | R por operación |
|---|---|---|---|
| CVGAP-NQ | 20 | −5,29 | −0,26 |
| CVGAP-CFD-NQ | 16 | −6,84 | −0,43 |
| U1-ES-GRILLA | 11 | −3,84 | −0,35 |
| U1-ZONAS-ES | 2 | −0,14 | −0,07 |
| CVGAP-ES-C | 6 | +0,39 | +0,06 |
| U1-ZONAS-AVCL-ES-C | 7 | +0,50 | +0,07 |
| U1-ZONAS-AVCL-NQ | 7 | +0,62 | +0,09 |
| U1-ZONAS-BT2-ES | 5 | +0,66 | +0,13 |
| U1-ZONAS-NQ | 17 | +0,78 | +0,05 |
| CVGAP-CFD-ES-C | 3 | +1,04 | +0,35 |
| U1-ZONAS-BT2-NQ | 10 | +1,07 | +0,11 |
| U1-YM-GRILLA | 3 | +1,45 | +0,48 |
| U1-ORO-GRILLA | 3 | +1,71 | +0,57 |
| U1-RACIMOS-GRILLA-NQ | 5 | +2,20 | +0,44 |
| U1-CRUZADO | 18 | +2,39 | +0,13 |
| U1-RACIMOS-GRILLA-ES | 9 | +2,58 | +0,29 |
| **Total (16 reglas)** | **142** | **−0,72** | **−0,005** |

**Lectura.**
- **Corriendo todas a 1R por operación, octubre termina en −0,7R:** casi cero.
- **Las tres reglas en alerta (CVGAP-NQ, CVGAP-CFD-NQ y U1-ES) suman −16,0R. Las otras 13 suman +15,3R** (95 operaciones, ≈ +0,16R por
  operación).
- **U1-ZONAS-NQ** pierde en puntos (−248) pero da +0,8R: sus pérdidas fueron en operaciones de riesgo grande. Medido en R pesa menos
  que en puntos.
- **Cautela:** es un mes y 142 operaciones. No decide ninguna regla (cada acta decide a su N fijo), y separar las 3 en alerta después
  de verlas es una mirada posterior, no una regla.
