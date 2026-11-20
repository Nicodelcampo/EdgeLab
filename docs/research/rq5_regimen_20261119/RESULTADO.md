# RQ5-REGIMEN: la banda de ruido de Zarattini es un régimen robusto desde 2018 en cuatro de cinco índices; el holdout A5 no tiene potencia (resultado, 2026-11-20)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (3.569 pruebas en `RQ5_REGIMEN`, registradas antes de correr).
- Lectura con `tools/rq5_regimen.py`, commiteada antes de que existieran los desenlaces.
- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- Datos: `OPS_DESC_REP.csv.gz`, `EVENTOS.csv.gz`, `CALIBRACION.json` (310/324 celdas calibran contra ticks; la fábrica con corr 0,996) y
  `RESULTADO.json`.
- Decisión: meses DESC del régimen 2018-01 → 2025-07.

## Veredicto pre-registrado: REGIMEN_ROBUSTO (P1 y P2 pasan; P3 no se adopta)
| Prueba | Resultado | Umbral | Pasa |
|---|---|---|---|
| P1 fábrica (NQ+ES+YM+RTY) | +0,050 R/op (bruto +0,083, fricción/R 0,029), n 2.954, p 0,045 | R > 0, p < 0,05 | sí |
| P1 celdas positivas | 310/310 calibradas evaluables (100 %); mediana +0,037 | ≥ 70 % | sí |
| P1 vecinos a un paso | 10/10 positivos (+0,035 a +0,054) | ≥ 8/10 (75 %) | sí |
| P2 NQ | +0,082 (p 0,017; n 742) | | + |
| P2 ES | +0,093 (p 0,007; n 711) | | + |
| P2 YM | −0,022 (p 0,72; n 730) | | − |
| P2 RTY | +0,046 (p 0,099; n 771) | | + |
| P2 EMD (costo estimado; no vota) | +0,044 (p 0,10; n 741) | | + |
| P2 total | 3 de 4 votantes positivos | ≥ 3 | sí |
| P3 salida al cierre − tp 2 | −0,007 (p 0,77) | > 0 y p < 0,05 | no: la regla congelada es la fábrica |

**Por mes** (fábrica, NQ+ES+YM+RTY, meses DESC del régimen):
- 54,7 operaciones por mes;
- +2,71 R/mes;
- t mensual 1,94;
- 61 % de meses positivos.

**Épocas (fábrica, NQ+ES+YM+RTY):**

| Época | DESC | REP |
|---|---|---|
| 2006–2017 | −0,049 | −0,015 |
| 2018–2025 | +0,050 | +0,027 |

La REP de 2018–2025 de la fábrica estaba contaminada por la revisión del 19-nov; se informa pero no decide.

**Quiebre sup-F** (serie mensual DESC, sin elegir el corte): 2017-08, p 0,066. Coincide con la convención 2018 declarada.

Diagnóstico de grilla: 324 variantes; operaciones por celda 2270/2954/3594 (mín/mediana/máx); 0 celdas casi vacías (< 443 op.); número
efectivo de variantes 1,47; perillas inertes: L, s, tp; Spearman(operaciones, R) −0,552. Lectura:
- **Las 324 celdas son casi una sola regla:** el 100 % positivo y los 10/10 vecinos dicen que la regla no es un pico, pero no son 324
  confirmaciones.
- **La perilla que mueve es la severidad de la banda (m),** con dosis-respuesta: m 0,8 → +0,028; m 1,0 → +0,038; m 1,2 → +0,044. Menos
  operaciones dan más R por operación.
- **La hora de corte** va en el mismo sentido: 11:00 → +0,043; 12:00 → +0,032.

Episodios: media +0,050 (n 2954); sin los 3 peores meses +0,073; sin los 3 mejores +0,024. Peores: 2020-03 −21,4; 2022-01 −18,6;
2018-12 −13,8. Mejores: 2020-06 +32,6; 2020-09 +26,2; 2018-07 +20,8.
- **Lectura:** regla de cola derecha. Sin sus 3 mejores meses queda positiva pero la mitad de grande.

## Holdout A5: no se abre (K27)
Meses HOLDOUT 2018-01 → 2025-07, fábrica, los cinco índices: N = 1.454 operaciones (NQ 292, ES 294, YM 268, RTY 302, EMD 298).

| Efecto supuesto | Potencia (α 0,05) |
|---|---|
| El de desarrollo (+0,050) | 0,60 |
| La mitad (+0,025) | 0,24 |

- **Con el corte sup-F (desde 2017-08):** N 1.565, potencias 0,63 y 0,25.
- **Por qué no se abre:** `holdout_ventanas.registrar_apertura` exige potencia ≥ 0,8 para gastar la única apertura (K27/E8). Ninguna
  variante la alcanza; cambiar esa compuerta es decisión de Nico.
- **Forward secuencial a ≈ 97 operaciones por mes (cinco índices):**
  - con el efecto de desarrollo decide en ≈ 26 meses;
  - con la mitad, en ≈ 103 meses (supera el tope de 60).

## Justificación económica / cómo podría refutarse
- **Justificación:** el momentum intradía temprano (flujo de cobertura de gamma y de fondos de momentum) continúa más de lo que revierte.
  El neto aparece cuando la fricción relativa baja de ≈ 0,09 a ≈ 0,03 R (desde 2017–2018).
- **Cómo podría refutarse:** holdout o forward con media ≤ 0; que la ventaja dependa de unos pocos meses de crisis (sin los 3 mejores
  meses ya cae a la mitad).

Aporte al referente: una regla de ≈ 55 operaciones por mes que se había descartado por un promedio de épocas resulta robusta en el régimen
actual en cuatro índices, con un quiebre objetivo que coincide con el corte. Su confirmación limpia existe (holdout A5) pero no tiene
potencia: la decisión de cómo confirmarla es de Nico.
