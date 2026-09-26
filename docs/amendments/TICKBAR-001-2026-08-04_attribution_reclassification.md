# Enmienda TICKBAR-001 — reclasificación H2 → H3

**Fecha:** 2026-08-04  
**Estado:** APROBADA POR NICO en chat, después de observar el oráculo.  
**Naturaleza:** enmienda post-oráculo explícita; no se presenta como preregistro original.

## Evidencia ya observada

- stream NT8/Python idéntico: 309.939 eventos y digest `9639232233418205644`;
- OHLC idéntico en 30.994/30.994 barras;
- `n_events` por barra difiere en 81,6%;
- PRED-003 refutada: 3,91% en K=25 y 81,78% en K=10.

## Corrección semántica

H2 se decide exclusivamente con identidad directa de barras primarias (OHLC y,
cuando esté disponible, límites autoritativos). `n_events`, `seq_first/last`,
volumen y digest del footprint son mediciones de atribución H3. Nunca vuelven a
usarse como proxy de cortes.

El clasificador gastado se conserva. La corrección se publica como
`tools/tickbar_diag_v2.py`, con `classifier_contract=v2_ohlc_cuts`.

## Consecuencia

La evidencia clasifica el incidente como H3 `ATTRIBUTION_MISMATCH`. El lado
Python queda congelado. El arreglo debe ocurrir en la asociación BIP1→barra
primaria de `BigTrap2.cs` y no puede usar outcomes.
