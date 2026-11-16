# Cartera con el período nuevo — resultado (2026-11-16)

Estado: RESULTADO. Pre-registros: `PREREGISTRO.md` (cartera) y `PREREGISTRO_PERDIDAS_CONCENTRADAS.md`. Datos: `BATERIA.json`,
`SELECCION.json` (commit `b5f01f5d`, antes de mirar noviembre), `NOVIEMBRE.json`, `PROP.json`, `PERDIDAS_CONCENTRADAS.json`,
`CORRELACION_DEV.json`, operaciones en `ops/`. 51 kernels (holdout sellado 2026-10-01 → 2026-11-13 de las 27 reglas con acta vigente +
desarrollo faltante de 11).

**Corrección previa a mirar noviembre (causa raíz):** en las campañas con `"estadistico": "R"` el motor ya devuelve el neto en R; dividirlo
otra vez por el riesgo achicaba su R ≈ 20 veces (TORI, DRC, CONF, CVGAP2) y rompía la contracción. Corregido en `_ops` antes de la selección.

## 1. Cartera congelada (regla §5, sólo desarrollo y octubre)

| Regla | Señal → ejecución | R/op desarrollo (IC90) | R contraído | Fricción R | R con fricción ×2 | Meses + | DD dev (R) | Ops/mes |
|---|---|---|---|---|---|---|---|---|
| CVGAP-ES-C | ES → ES | +0,35 (+0,17; +0,53) | +0,19 | 0,06 | +0,29 | 86 % | −3,3 | 8,5 |
| U1-RACIMOS-GRILLA-NQ | NQ → NQ | +0,17 (+0,05; +0,27) | +0,12 | 0,02 | +0,15 | 82 % | −1,9 | 4,9 |
| CONF-CVR-CFD-NQ-R | USATECH CFD → NQ | +0,14 (+0,07; +0,19) | +0,12 | 0,03 | +0,10 | 86 % | −2,2 | 5,1 |
| U1-ZONAS-BT2-ES | ES → ES | +0,10 (+0,05; +0,13) | +0,09 | 0,05 | +0,05 | 86 % | −1,3 | 4,6 |
| PREAPERTURA-NQ | NQ → NQ | +0,37 (+0,03; +0,73) | +0,09 | 0,04 | +0,34 | 71 % | **−18,1** | 10,3 |
| U1-ORO-GRILLA | XAU CFD → GC | +0,14 (−0,02; +0,28) | +0,09 | 0,05 | +0,09 | 58 % | −4,9 | 5,2 |
| U1-ZONAS-BT2-NQ | NQ → NQ | +0,09 (−0,03; +0,20) | +0,07 | 0,03 | +0,06 | 69 % | −3,9 | 8,3 |
| CVGAP-CFD-ES-C | USA500 CFD → ES | +0,07 (−0,02; +0,16) | +0,06 | 0,04 | +0,03 | 64 % | −2,1 | 5,4 |

≈ 52 operaciones por mes entre las 8; correlación diaria de desarrollo entre pares: máxima 0,05, media −0,02 (diversificación real).
Quedaron fuera por la regla: TORI-NQ-R y PREAPERTURA-ES (fricción 0,080 y 0,088 > 0,08), U1-ZONAS-ES/NQ y U1-RACIMOS-ES (réplica ≤ 0),
CVGAP-NQ y CVGAP-CFD-NQ (octubre en contra con t < −1,64), los DRC (fricción 0,15–0,30).

## 2. Prueba de noviembre (2 → 13, 10 sesiones que nadie miró) — lectura pre-registrada: **VERDE**
- Cartera en noviembre: **+0,73 R por sesión** (R total +7,3; t 0,95; p 0,19). Holdout completo (oct + nov, 30 sesiones): **+0,53 R por
  sesión** (R total +15,9; t 1,36; p 0,096).
- **Concentración:** PREAPERTURA-NQ hizo +9,5 R en 4 operaciones; sin ella, noviembre da −2,2 R. Por regla en noviembre: CVGAP-ES-C +0,8
  (5 ops), U1-ZONAS-BT2-NQ +0,5 (4), U1-ZONAS-BT2-ES −1,4 (5), U1-RACIMOS-NQ −2,1 (2); las tres con señal de CFD no tienen noviembre sellado.
- e-procesos del holdout por regla entre 0,94 y 1,63: ninguna regla tiene todavía evidencia individual (falta n).
- Lectura: dirección favorable en la única prueba limpia, sin significación y dependiente de una regla. Respalda empezar con riesgo chico; no
  es una confirmación.

## 3. Prop 50K (objetivo 3.000, pérdida máx. 2.000 con trailing de fin de día, 60 días; micros enteros)

| Riesgo por R | Operaciones no dimensionables | Pasa / quema (media contraída) | Pasa / quema (azar, media 0) |
|---|---|---|---|
| 100 USD | 109 de 716 | 33 % / 3 % | 8 % / 32 % |
| **200 USD** | 10 de 716 | **67 % / 21 %** | 25 % / 71 % |
| 300 USD | 1 de 716 | 64 % / 35 % | 28 % / 72 % |
| 400 USD | 0 | 58 % / 42 % | 27 % / 73 % |

Con 100 USD por R una sola micro ya arriesga más del doble en 15 % de las operaciones (U1-RACIMOS-NQ: 200 USD la micro); **200 USD por R es el
punto óptimo**: casi todo es dimensionable y la ventaja contra el azar es máxima (67 % contra 25 %). Los costos de micros cambian poco el R
(+0,33 → +0,33 en CVGAP-ES-C; −0,01 a −0,02 en general).

## 4. Dónde se concentran las pérdidas — lectura pre-registrada: **SÓLO FRICCIÓN**
- H1 (24 reglas no generadoras, 3.626 operaciones de desarrollo): el tercil de stop corto (causal, propio de cada regla) rinde **−0,11 R por
  operación menos** que el resto (p 0,015; 16 de 24 reglas; nominada por BH).
- H2: en **bruto la diferencia es 0,000** (p 0,50): el stop corto no está peor elegido; paga la misma fricción fija sobre un riesgo menor.
- H3: saltear ese tercil no suma R total con evidencia (−12,7 R sobre 1.090 operaciones; p 0,39).
- La fricción se come el 58 % del R bruto del conjunto (+0,197 → +0,083 R por operación).
- Consecuencia de diseño (no señal): **medir y filtrar por fricción en R por operación** (costo / riesgo), no por tercil. Es la palanca ya
  conocida «stop grande frente a la fricción», ahora medida en 24 reglas.
- Tamaño (descriptivo): con contrato fijo el t medio por regla sube de 1,38 a 1,77 (22/24 positivas contra 19/24): las operaciones con stop
  amplio llevan la ventaja. Mismo orden en noviembre.
- Descriptivo (hipótesis futura, no poda nada): por hora de entrada (NY) 09:30–10:30 +0,18 R/op, 10:30–14:00 +0,08, 14:00–16:15 +0,01,
  fuera de la rueda +0,03; por día, viernes ≈ 0 y domingo −0,05.

## 5. Mejoras (sólo desarrollo; cada una es una hipótesis nueva)
1. **Fricción**: (a) firma con la comisión más baja (el R canónico usa la máxima; en micros la diferencia por operación es chica); (b) filtro
   por fricción en R por operación — pre-registrar con corte causal y probar en noviembre/forward; (c) entradas límite donde la regla lo permita.
2. **Frecuencia**: transferir reglas a otros activos ya se probó y no funciona (`transferencia_multiactivo_20261108`, −0,07 R por sesión con
   5.673 operaciones). La frecuencia sale de sumar reglas poco correlacionadas: la cartera ya tiene ≈ 52/mes.
3. **Rentabilidad**: concentrar la operación en la primera hora (09:30–10:30) — hipótesis a pre-registrar; tamaño por contrato fijo o ∝ 1/√riesgo.
4. **Riesgo**: PREAPERTURA-NQ tiene DD de −18 R y racha de 13 perdedoras en desarrollo (pocas ganadoras grandes); en prop conviene pesarla a
   la mitad o ponerle tope diario — decisión de riesgo, no de señal.

## Qué falta
Sellar noviembre del spot (USATECH, USA500, XAU) y de GC para medir las 3 reglas con señal de CFD y las demás de octubre solamente.
Ejecución en vivo: las de señal CFD necesitan el feed de Dukascopy/MT5 además de NT8.

## Anexo (2026-11-16 04:2x UTC): noviembre con el spot sellado (versión 7 del dataset)
Antigravity selló el spot de Dukascopy hasta el 15-nov. Re-corridas las reglas con señal de spot (la primera re-corrida montó la versión 6 y
devolvió sólo octubre; se detectó por la cantidad de velas leídas y se relanzó con otro nombre de kernel). Selección sin cambios.
- Cartera en noviembre (10 sesiones): **+0,56 R por sesión** (antes +0,73 sin las 3 de spot; t 0,67, p 0,26). Holdout completo:
  **+0,47 R por sesión** (t 1,17, p 0,13). Lectura pre-registrada: sigue **VERDE**, más débil.
- Las nuevas en noviembre: CONF-CVR-CFD-NQ-R −1,0 R (1 operación), CVGAP-CFD-ES-C −0,7 R (9 operaciones). U1-ORO-GRILLA sin operaciones:
  se ejecuta en GC y el GC de noviembre todavía no está sellado. El resultado anterior quedó en `NOVIEMBRE_solo_futuros.json`.
