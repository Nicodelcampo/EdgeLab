# TRANSFER-RTY-EMD: Z (FundedSync) y compresión de volatilidad (VZ) en Russell y MidCap, sólo meses DESC (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Origen:** pendientes de la re-indagación (`../RE_INDAGACION_PISTAS_20261119.md`): Z nunca se midió en RTY ni EMD, y VZ (compresión de
  VIX+VIX9D, la única pista de Carril 2 que crece desde 2018) tampoco. La lectura de confirmación (REP) no tiene potencia hoy (K49); en cambio,
  los meses DESC de estos instrumentos son desarrollo nunca mirado para estas reglas: medir ahí la transferencia es exploración legítima y deja
  REP sellado para una confirmación posterior.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3** (DESC de A5 en instrumentos nuevos para estas reglas). **Familias:** `FUNDEDSYNC` (Z) y `CARRIL2_A5` (VZ).
- **Herramienta:** `tools/transfer_rty_emd.py z|vz` (Z: `neto_pistas._ms/_ops/_cfg/FABRICA` con el motor de la traducción de FundedSync; VZ:
  `carril2._senales2` sobre `sqx_catalogo.simular` calibrado K28, con RVX para RTY y VIX para EMD), `holdout.a5_bloque`, fricción canónica.
  `registro_global.exigir_contada` al inicio (K51).
- **Costos estimados declarados (K33):** EMD usa el spread ESTIMADO de 2 ticks y la comisión de `costos_canonicos.json`, sólo dentro de
  `costos.estimados_permitidos` citando este pre-registro. RTY tiene costo medido.

Antecedentes: NETO-PISTAS (Z INTERMEDIO, fábrica en pico), RE-INDAGACION (Z bruto + en las dos épocas; VZ −0,01 / +0,05 / +0,13 por época),
CARRIL2-LOTE2, m1_largo PREREGISTRO_INDICES (R y SOM en EMD+RTY: no concluyente).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K33, K36, K40, K48, K49, K51, K52, K53).

Potencia previa: Z ≈ 2,3 operaciones por mes por instrumento → ≈ 220 en DESC 2018-01 → 2025-07 (RTY+EMD); VZ ≈ 2,2 por mes → ≈ 200. Con ee
≈ 0,08 R, el efecto mínimo detectable al 80 % (α 0,05) es ≈ 0,23 R: esto es una exploración de transferencia, no una confirmación; un nulo no
mata la regla (se publica su MDE).

## Justificación económica
- **Z:** tendencia intradía de índice (eficiencia del día y EMA) — el mismo flujo de cobertura que mueve NQ debería moverse en los demás
  índices si el mecanismo es general y no un ajuste a NQ.
- **VZ:** la compresión de volatilidad implícita dispara compras de vol-control/vanna en todo el índice amplio, no sólo en S&P y Nasdaq.

## Reglas y decisión (fijas)
- **Z:** fábrica (cubeta 15, EMA 20, eficiencia 45) con stop de catástrofe 0,25 × ATR20 de la sesión previa aplicado con la MAE; R = (resultado
  − fricción)/(0,25 · ATR20). Ventana del régimen declarada **2018-01-01 → 2025-07-31**, sólo sesiones DESC de A5. Se reporta también 2008–2017.
- **VZ:** la regla de `CARRIL2-LOTE2` sin cambios (z de 6 barras de IV y VIX9D < −1; IV = RVX en RTY, VIX en EMD; stop 1,25 × ATR20; salida
  z ≥ −1; tope 10). Ventana 2011-01 (inicio de VIX9D) → 2025-07, entrada en DESC y **salida también en DESC** (se descarta si sale en REP,
  HOLDOUT o EMBARGO: REP queda limpio). Se reporta 2018–2025 aparte.
- **Prueba (una por regla, RTY+EMD juntos):** R neto medio > 0, bootstrap por sesión, p unilateral < 0,05 → `TRANSFIERE_DESC`; la siguiente
  etapa sería la lectura de REP de RTY+EMD con su plan de potencia K49. Si no: `SIN_TRANSFERENCIA` con MDE publicado (no refuta la regla en
  NQ/ES).
- **Cómo podría refutarse:** R neto ≤ 0 en los dos instrumentos con N suficiente; o positivo sólo por la fricción estimada de EMD.
- **Contador:** 1 prueba en `FUNDEDSYNC`, 1 en `CARRIL2_A5`.
