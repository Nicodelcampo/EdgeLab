# Especificación Pre-Registrada: Familia `CONFLUENCIA-CVGAP-RACIMOS` (`2026-10-29`)

- **Módulo experimental:** `edgelab/research/confluencia_cvgap_racimos.py`
- **Origen en la Espiral (Olas 1–9):** Síntesis directa de las 6 campañas que alcanzaron `ACTA_HOLDOUT.json` (`CVGAP-NQ`, `CVGAP-CFD-NQ`, `U1-RACIMOS-GRILLA-NQ`, `U1-RACIMOS-GRILLA-ES`, `U1-ZONAS-BT2-ES`, `U1-ZONAS-BT2-NQ`) y las pistas ganadoras de `OTR930`.
- **Mecanismo económico:** Exige simultáneamente que el agotamiento tras la excursión desde la Caja Amarilla del corredor EMA (`EmaCorridorTrendVolW2`) ocurra sobre un **racimo denso de nodos de absorción/volumen (`AVZP2`/`BT2`)** con cuantiles invariantes de escala en los gaps barridos e imanes (`ZONAS-GAPS`), resolviendo la asimetría de densidad entre `NQ` y `ES`.
- **Cómo podría refutarse:** `0` celdas nominadas por FDR (`q <= 0,10`) en `DESC`, fallo ante placebo/latencia en `INTEGRIDAD`, o media neta `<= 0` en `OOS`/`HOLDOUT`.
