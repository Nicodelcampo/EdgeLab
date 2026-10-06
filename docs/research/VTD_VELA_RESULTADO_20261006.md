# VTD-VELA — resultado de la prueba única pre-registrada — 2026-10-06

Pre-registro: `VTD_VELA_PREREGISTRO_20261006.md` (commit `074b8461`, con enmiendas técnicas de datos). Kernels
`edgelab-vela-{es,ym,rty,mgc}` + `edgelab-vtd-vela-test-20261006`. JSON: `vtd_vela_20261006/VTD_VELA_RESULTADOS.json`.

**Datos:** ES, YM, RTY, MGC; 23 contratos; 6.495 marcas VTD (5.215 en RTH sin doji); 734 sesiones.

## Prueba formal: **DESCARTADA**
Media de signo(vela) × asim_adj_10 = **−0,013** (SE 0,009, MDE 0,022), p unilateral = 0,93. Acierto del lado: 49,6 %.

## Descriptivos
- Por instrumento:
  - ES −0,017 (n = 3.356);
  - YM −0,008;
  - RTY +0,008;
  - MGC −0,019.
  - Ninguno distinto de 0, y 3 de 4 negativos.
- H50: −0,001. Sin control de deriva: −0,010.
- Por régimen de amplitud: −0,019 / +0,002 / −0,021.

## Lectura
El indicio de MNQ (+0,044), visto después del fracaso formal, era ruido o deriva: en datos limpios la vela de la marca
**no** anticipa el lado (el MDE de 0,022 descarta incluso la mitad del efecto de MNQ). Con esto, **ningún predictor
probado** (lado y delta de AVCL, salida, EMA en 100 celdas, VWAP, desbalance, momentum, extremos, vela) anticipa el lado
del tramo largo después de un evento de volumen, a esta escala.
