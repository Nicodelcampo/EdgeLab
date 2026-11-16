# Mejoras de la cartera — resultado y cartera v2 (2026-11-16)

Estado: RESULTADO. Pre-registro `PREREGISTRO_MEJORAS.md` (commit `87596aab`, antes de calcular). Datos: `MEJORAS.json`, `CARTERA_V2.json`,
`CARTERA_V2_OPERATIVA.json`. Confirmación en G (desarrollo de las 3 generadoras, fuera del análisis que propuso las mejoras) ∪ H (holdout
oct + nov de las 27 reglas, nunca mirado por fricción, hora ni tamaño).

## Hipótesis (k = 3, BH q 0,10)
| | G ∪ H | G | H | BH | ¿entra en v2? |
|---|---|---|---|---|---|
| **M1** no operar si fricción > 0,08 R | Δ −0,33 R (p 0,050; 129 salteadas; R total de las salteadas −43 R; 5/8 reglas) | −0,17 | −0,52 | sí | **sí** |
| M2 no entrar 14:00–16:15 NY | Δ −0,06 R (p 0,16) | −0,13 | **+0,08** | no | no |
| **M3** micros fijos por regla | t 1,46 → **2,42** (Δt +0,96; p 0,026; 235 sesiones) | +1,11 | +0,94 | sí | **sí** |

- M1: saltear las operaciones con stop menor que el piso de fricción sube el R por operación de +0,027 a +0,097 en G ∪ H.
- M2 no se sostiene en el holdout (va al revés): queda descartada; la franja tardía no se poda.
- M3: con micros fijos por regla (riesgo mediano ≈ 200 USD) las operaciones de stop amplio, que llevan la ventaja, pesan más.

## Cartera v2 contra v1 (prop 50K, micros enteros)
| | Desarrollo (302 sesiones) | Holdout oct+nov (31) | Pasa / quema (media contraída) | Pasa / quema (azar) |
|---|---|---|---|---|
| v1 (riesgo fijo 200 USD/R) | +29.515 USD, t 4,25, DD −1.849 | +2.827, t 1,24, DD −851 | 67 % / 21 % | 25 % / 71 % |
| v1 + A1 (comisión mínima) + A2 (PREAPERTURA-NQ ×0,5) | +23.823, t 5,18, DD −1.233 | +2.390, t 1,41, DD −508 | 63 % / 3 % | 13 % / 49 % |
| **v2 = + M1 + M3** | +24.159, **t 5,33, DD −1.214** | **+3.339, t 1,77, DD −476** | **62 % / 3 %** | 14 % / 50 % |

Lectura: la v2 casi no cambia la probabilidad de pasar, pero **la de quemar la cuenta cae de 21 % a 3 %** y en el holdout (no usado para
elegir nada de esto) gana más con menos drawdown. La mayor parte del cambio en quema viene de A2 (PREAPERTURA-NQ a la mitad); M1 y M3 suben
el t del holdout de 1,41 a 1,77. Con el azar la quema es 50 %: la ventaja contra el azar se mantiene.

## Cartera v2 operativa (`CARTERA_V2_OPERATIVA.json`)
| Regla | Señal | Ejecuta | Micros fijos | No operar si el stop < (pts) |
|---|---|---|---|---|
| CVGAP-ES-C | ES | MES | 2 | 11,1 |
| U1-RACIMOS-GRILLA-NQ | NQ | MNQ | 1 | 19,3 |
| CONF-CVR-CFD-NQ-R | USATECH (CFD) | MNQ | 2 | 19,3 |
| U1-ZONAS-BT2-ES | ES | MES | 2 | 11,1 |
| PREAPERTURA-NQ | NQ | MNQ | 1 (×0,5) | 19,3 |
| U1-ORO-GRILLA | XAU (CFD) | MGC | 1 | 7,6 |
| U1-ZONAS-BT2-NQ | NQ | MNQ | 2 | 19,3 |
| CVGAP-CFD-ES-C | USA500 (CFD) | MES | 2 | 11,1 |

Firma: la de comisión más baja entre las que admiten algoritmos (A1 asume operar ahí). Lo demás de cada regla (entrada, stop, objetivo,
horario) no cambia. Seguimiento: e-proceso por regla y de la cartera desde el 2026-11-16. Operar con dinero real lo decide Nico.

## Límites
M1 y M3 se eligieron después de ver el desarrollo de 24 reglas; G ∪ H no las vio, pero G son sólo 3 reglas y H son 31 sesiones. La v2 es la
mejor versión que los datos permiten hoy, no una confirmación: el forward la decide.
