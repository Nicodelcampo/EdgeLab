# Traspaso para la sesión de Antigravity (filtros / atlas de contexto) — 2026-11-05

Estado: VIGENTE. Rama `claude/vibrant-clarke-s9z6e2` (la rama `gemini/filtros-20261104` ya está integrada acá).

## 1. Qué pasó con el atlas de contexto y vetos (tu entrega)

- **Integrado**, con tres arreglos: el contexto común ya no tumba campañas (`try` en `grilla_generica.correr`, error en
  `contexto_comun_error`); kernels reconstruidos; contador global reencadenado.
- **Control bruto/neto** (212 MARGINALES, `contexto_bruto_neto/RESULTADO_BRUTO_NETO.md`): **todos los efectos confirmados eran fricción
  en R**: S3/T3, ATR y volumen relativos, NY 9:30–12 y el **imán** (`veto_muro=vetado`). En bruto conservan del 3 % al 31 % y ninguno
  confirma. **Sólo `veto_huida` en CONTINUACIÓN sobrevive en bruto** (pista, K = 13).
- Bug de evaluación: en las 11 reglas, U1-CRUZADO, TORI y CONF-CVR tenían **lado y TP inferidos**. Ver
  `programa_r_20261103/REVISION_ATLAS_CONTEXTO_FRICCION_20261104.md`.
- **Regla nueva:** todo filtro común se mide también en bruto. Cada corrida guarda `marginales_globales_bruto` (la etapa MARGINALES ya
  lo devuelve).
- **Piso de riesgo frente a la fricción** (`RESULTADO_PISO_RIESGO_20261104.md`): refutado según el pre-registro. u = 0,10 queda para
  validar desde noviembre.

## 2. Otras tareas de la sesión

- **CVGAP-2** (8 activos): sin edge. **DOBLE-RETROCESO**: sin candidatas; holdout forzado −0,30R.
- **Ejecución:** siempre en futuros. El CFD es sólo fuente de señal.
- **NT8:**
  - `nt8/strategies/EdgeLabCvgapESC.cs` v1.1 (CVGAP-ES-C nativa): paridad de señal 27/29 con niveles exactos y de ejecución 24/26
    (±1 pt). Abierto: los disparos extra de NT8 (correr desde el 01/01/2026). `nt8_replay/CVGAP-ES-C/PARIDAD_SENAL_V1.md`.
  - `nt8/strategies/EdgeLabSignalReplay.cs` v1.2 + `tools/senales_nt8.py` (Market Replay de señales congeladas). CVGAP-CFD-NQ, 15
    operaciones: slippage de entrada 0,60 pts, en el stop 0,61; costo ida y vuelta ≈ 1,1 pts contra 1,55 canónico (G3 conservador,
    cota optimista). `nt8_replay/CVGAP-CFD-NQ/replay_ago_v12/RESULTADO.md`.
  - Python llena la entrada SIG en la apertura de **k+2**: `senales.csv` usa `t_fill − 60`.
- **Tabla de colores:** columnas nuevas de R total y fricción en R (frágiles con ≥ 0,08R: DRC-NQ, AVCL-NQ, AVCL-ES, TORI).

## 3. Pendiente

1. Más Market Replay (unas 50 operaciones) para estimar la fricción.
2. CVGAP-ES-C en Sim101 con datos en vivo.
3. Strategy Analyzer de CVGAP-ES-C desde el 01/01/2026.
4. Chequeo de preflight «ejecución = futuro» (propuesto, falta el OK de Nico).
5. Validación hacia adelante desde noviembre: u = 0,10 y `veto_huida` en continuación.

**Edges promovidos: 0.**
