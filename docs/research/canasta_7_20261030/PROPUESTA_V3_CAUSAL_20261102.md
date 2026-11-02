# Propuesta v3 de la canasta del holdout, con código causal (2026-11-02)

Estado: VIGENTE. **Firmada por Nico el 2026-11-02** en la sesión en la nube («firmo la canasta V3»). Reemplaza a `PREREGISTRO.md` (v2)
en la composición; todo lo demás de la v2 sigue igual. Apertura: `ACTA_APERTURA_V3_20261102.md`. Referente:
`docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Por qué
1. **La v2 se eligió con código que miraba el futuro.** `areas_expansion.disparos` (familia U1) cortaba áreas mirando hasta 500
   minutos adelante, y CVGAP tenía dos problemas de borde que en vivo daban disparos tardíos o ausentes. Ver
   `docs/research/HALLAZGO_LOOKAHEAD_DISPAROS_U1_20261102.md`.
2. **Hoy ninguna corrida puede mirar el futuro.** Ningún kernel se lanza sin un certificado de causalidad estricta (corte en la vela
   de cada disparo) para el código exacto que corre. Los 28 experimentos de las campañas están certificados
   (`config/causalidad_certificados.json`, `tests/research/test_causalidad_estricta.py`).

## Re-medición causal de las 7 reglas congeladas
Misma celda, mismos cortes y mismo tope del acta. Sólo DESC y réplica, nunca el holdout. Fuente:
`remedicion_causal_20261102/RESUMEN.json` (`tools/remedir_canasta_causal.py`). Media neta por operación, en puntos del instrumento
de ejecución.

| Regla | DESC causal (n, media, p) | Réplica antes | Réplica causal (n, media, IC90, p) |
|---|---|---|---|
| CVGAP-NQ | 108, +15,2, 0,022 | 88, +19,1 | 88, **+15,8**, [+0,5; +30,7], 0,040 |
| U1-RACIMOS-GRILLA-NQ | 48, +17,3, 0,0005 | 13, +19,8 | 16, **+14,8**, [−12,1; +39,2], 0,19 |
| CVGAP-CFD-NQ | 111, +17,8, 0,001 | 110, +10,5 | 110, **+5,8**, [−5,0; +16,2], 0,19 |
| U1-ZONAS-AVCL-NQ | 44, +5,6, 0,015 | (sin registro por celda) | 53, **+4,0**, [−2,0; +9,3], 0,12 |
| U1-ZONAS-NQ | 94, +22,2, 0,001 | 52, +10,7 | 65, **+2,9**, [−17,0; +21,3], 0,40 |
| U1-ORO-GRILLA | 44, +5,2, 0,001 | 17, +1,6 | 24, **−1,2**, [−5,4; +2,9], 0,70 |
| U1-YM-GRILLA | 196, +5,7, 0,22 | 32, +12,7 | 38, **−10,2**, [−42,8; +20,6], 0,70 |

## Propuesta
**Canasta v3: las 5 reglas con réplica causal positiva.** Son CVGAP-NQ, U1-RACIMOS-GRILLA-NQ, CVGAP-CFD-NQ, U1-ZONAS-AVCL-NQ y
U1-ZONAS-NQ.
- **Salen U1-ORO-GRILLA y U1-YM-GRILLA:** con código operable, su réplica es negativa.
- **Es otra selección mirando la réplica,** declarada como tal. Se agrega a la selección posterior que ya declaraba la v2, y la
  multiplicidad heredada no cambia.
- **Todo lo demás de la v2 se mantiene:**
  - prueba principal t por sesión de la canasta, con revisiones a 20, 40 y 60 sesiones y límites O'Brien-Fleming (t ≥ 2,39, 1,69 y
    1,38; α total 0,10);
  - estados por regla;
  - secundarios.

## Lista para abrir (comprobada, sin mirar el holdout)
- **Código:** las 5 reglas pasan el candado de causalidad.
- **Datos sellados en `edgelab-holdout-sellado`:**
  - NQ y GC, sesiones 2026-10-01 → 10-30, desde `<INST>_12-26` más el archivo diario del 30 de octubre;
  - CFD USATECH.
- **Lectura del sellado:** todos los lectores de ticks sellados leen todos los archivos del instrumento. Antes sólo leían el primero
  y se perdía el archivo diario.
- **Calentamiento de zonas** (U1-ZONAS-AVCL, U1-ZONAS-NQ, U1-RACIMOS): en el kernel sellado se adjunta también el almacén de zonas
  de desarrollo, que no usa resultados. Las zonas creadas antes de la frontera siguen vivas al abrir, como en vivo; las del holdout
  se calculan con los ticks sellados. Antes las primeras horas del holdout no tenían zonas.
- **Pendiente para abrir:**
  1. firma de esta v3;
  2. acta de apertura con reserva LORD++, registrada antes de lanzar (`holdout_ventanas`);
  3. lanzamiento con el embudo o el protocolo de apertura. Con 20 sesiones válidas (1 → 30 de octubre) se puede hacer la primera
     revisión de la v2.

## Re-medición causal de las 5 nominadas que quedaron afuera (2026-11-02, después de firmada la v3)
Fuente: `remedicion_causal_20261102/RESUMEN.json`.

| Regla | DESC causal (n, media, p) | Réplica antes | Réplica causal (n, media, p) |
|---|---|---|---|
| U1-ZONAS-BT2-ES | 36, +3,3, 0,0005 | 29, +2,5 | 29, **+2,5**, 0,037 |
| U1-ZONAS-BT2-NQ | 62, +4,5, 0,13 | 42, −17,5 | 46, **+5,1**, 0,19 |
| U1-ZONAS-ES | 60, +8,9, 0,0005 | 8 | 13, −0,1, 0,50 |
| U1-RACIMOS-GRILLA-ES | 85, +4,9, 0,0005 | 46, −0,5 | 64, −0,9, 0,64 |
| U1-ES-GRILLA | 421, +0,4, 0,29 | 39, −0,6 | 53, −1,5, 0,81 |

- **U1-ZONAS-BT2-NQ cambia de signo** con el código causal: réplica +5,1 (antes −17,5).
- **U1-ZONAS-BT2-ES** queda igual: +2,5, p 0,037.

Sumar alguna de las dos a la canasta sería otra selección mirando la réplica. Es una decisión de Nico, así que no se toca la v3
firmada.
