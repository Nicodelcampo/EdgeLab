# aVol tick formal — protocolo (2026-08-14)

Estado: `PREREGISTERED_NOT_RUN`
Spec: `specs/avolcluster_tick_formal_v0.json`

## Por qué este paso

La sonda M1 (`avolcluster_formal_v2_1`) terminó en `AVOL_UNDERPOWERED`:
ties 11,3% > 10% y MDE 0,31 para un efecto observado de +0,15. Los dos
constraints se resuelven con la misma corrida:

- **ties** → desempate por ticks (`tick_first_touch` de F2.7);
- **potencia** → 4 parquets canónicos en vez de un quarter (~4× zonas,
  SE zona esperada ≈ 0,05, MDE ≈ 0,15);
- **de yapa, P2**: el replay Python sobre 09-26 debe reproducir las 133 zonas
  del CSV NT8 (oráculo). Sin P2_PASS no hay formal: `ABSTAIN_P2`.

## Decisiones ya tomadas (no reabrir durante la corrida)

1. Benchmark primario = `control_random`. `nearest` es diagnóstico, no citable.
2. Detector v0.5 congelado. Un cambio de parámetro cierra la spec.
3. Ceros adentro. Ties resueltos por ticks. Categorías separadas.
4. Contraste pareado por sesión. HAC Bartlett.
5. Firewall 2026-06-30. Holdout, P&L y outcomes fuera.

## Pipeline

1. Verificar hashes de los 4 parquets (tabla en la spec). Mismatch → abortar.
2. `build_time_bars(ticks, minutes=1)` + `build_footprints` + `p1a_gate`.
3. Kernel v0.5 por sesión: bloques de 10 barras anclados al inicio de sesión
   (bloque parcial final descartado), celdas = volumen por tick de precio del
   bloque, bucket SessionRelative 30 min, historia = sesiones completas previas
   (lookback 20), cuantil empírico sin interpolar, un cluster por bloque.
4. **P2** sobre 09-26 con ventana [2026-04-10, 2026-06-30], warmup vacío al
   inicio (como NT8). Diff fila a fila contra el oráculo.
5. Si P2_PASS: carrera primer pasaje con lifecycle reflejado sobre las 4
   puntas, controles random (primario) y nearest (diagnóstico), etiquetas.
6. Un solo JSON + informe markdown. HEAD y hashes en el informe.

## Prohibido

Tocar el kernel, relajar gates, barrer parámetros, cruzar con otras familias,
abrir holdout, mirar P&L, promover etiquetas por narrativa (la etiqueta la
emite `decide_labels`, como siempre).
