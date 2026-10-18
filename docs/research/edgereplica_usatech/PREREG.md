# EdgeReplica (60 reglas) sobre USATECH CFD Dukascopy — pre-registro 2026-10-18

Pregunta: las 60 reglas horarias de `EdgeReplica` (hechas para MNQ/NQ, M1), aplicadas SIN cambios a USATECH (CFD Nasdaq-100, Dukascopy),
¿tienen expectativa neta de spread distinta de cero? ¿Su resultado diario correlaciona con el de MNQ?

Congelado antes de calcular:
- Reglas: `rules_v1.json` (idénticas a `tools/explo_edgereplica_mgc_20261006.py`). Semántica espejo de ese script (señal = signo del retorno de 15 min
  hasta el cierre de la barra b1; entrada al open de la barra siguiente a b2; salida al open de la barra siguiente al HOLD; libro neto; horas CT).
- Datos: `USATECHIDXUSD_m1.parquet` (bid/ask M1), 2023-01-01 → 2026-09-30. Holdout (>= 2026-10-01) no existe en el archivo ni se pide.
- Ejecución: largo entra al ask y sale al bid; corto entra al bid y sale al ask (spread real = único costo; sin comisión ni slippage extra: es un CFD).
  Variante de sensibilidad: +1 punto de slippage por ida y vuelta. Señal sobre mid.
- Guardas: se omite la señal si la barra de referencia (-15 min) está a más de 5 min de antigüedad o si faltan barras en la entrada/salida (> 5 min tarde).
  Se reporta cuántas se descartan.
- Métrica primaria: puntos netos por operación, agregado total y por año; IC95 bootstrap por sesión (20.000, semilla 20261018).
  Familia de 1 prueba primaria (total). Por año/por regla son descriptivos, sin p.
- Tramos: 2023-01→2026-09-10 (anterior a la publicación; las reglas se eligieron sobre datos de NQ cuyo rango exacto no está en este repo,
  por lo que NO es limpio fuera de muestra respecto de la selección, aunque sí es otro instrumento/proveedor), 2026-09-11→2026-09-30 (posterior).
- Correlación con MNQ: PnL diario USATECH (pts) vs EdgeReplica MNQ (USD por sesión, de `RESULTADOS_EXPLO_20261006.json`), solo sesiones 11-sep→30-sep (n pequeño, descriptivo).
- Lectura: SOBREVIVE si el límite inferior del IC total > 0; DECAYÓ si el superior < 0; si no, INCONCLUSO. Es un CFD: el neto real se confirma en futuros.
