# Handoff Auditor — Paridad aVolClusterPOI (NQ 06-26, 120t)

> **Fecha:** 2026-09-03  
> **Rama:** `research/avolcluster-nq-parity-oracle-20260901`  
> **Referente:** `docs/NORTH_STAR.md`  
> **Acta canónica:** `docs/research/PARIDAD_AVOLCLUSTERPOI_NQ0626_20260902.md`  
> **Estado vivo:** `docs/CURRENT.md`  

---

## 1. Resumen para el Siguiente Auditor

Este documento resume el estado exacto de la paridad de `aVolClusterPOI v0.5` sobre `NQ 06-26` (gráfico de 120 ticks) para que cualquier agente entrante pueda retomar sin desvíos ni duplicación de trabajo.

### Estado Técnico Certificado

```text
KERNEL_PARITY_ON_EQUAL_INPUT    = EXACT (23.339/23.339 bloques idénticos, 100,00 %)
BLOCK_REPLAY_PARITY             = 203 / 203 zonas emparejadas (100,00 % PASS/WARN)
END_TO_END_TICK_PARITY          = 201 / 203 zonas emparejadas (99,01 %)
GEOMETRY_DIFF (pares emparejados)= 0 ticks
TIMESTAMP_DIFF                  = 0 ms
BAR_MODEL_NT8                   = 120 transacciones estrictas / barra (Count, no Volume)
CAMPAIGN_OUTCOMES_OPENED        = false
HOLDOUT_INTEGRITY               = PRESERVADO
```

---

## 2. Causas Raíz Resueltas en el Repositorio

1. **Alineación de Inicio de Sesión (`session_begin_ns`):**
   - El parquet canónico `NQ_06-26_ticks.parquet` arranca el 12 de marzo de 2026; el chart de NT8 arranca el 31 de marzo (Sesión 0, 19:00 ART / 22:00 UTC).
   - Solución en `edgelab/bridge/bars.py`: `build_resolved_tick_bars` sincroniza el puntero de ticks al inicio de sesión CME exacto.
2. **Modelo de Avance de Barras NT8 (120t):**
   - NinjaTrader 8 avanza barras en gráficos de ticks contando estrictamente **120 transacciones por barra** (1 trade = 1 tick), no acumulando contratos.
   - Solución en `edgelab/bridge/bars.py`: avance de `ticks_per_bar` exacto. Auditado 10/10 barras contra `BARPROFILE_20260902.csv` con coincidencia 100,00% en Low y High.
3. **Contaminación de Memoria en Footprints:**
   - Solución en `edgelab/bridge/bars.py`: inicialización de `tick_bar_idx` con `-1` (`np.full(len(ticks), -1, np.int64)`) y verificación de límites en `build_footprints`.
4. **Alimentación Directa de Bloques (`run_diag_blocks`):**
   - Implementado en `edgelab/bridge/indicators/avolclusterpoi.py` y soportado vía `--diag-blocks` en `tools/paridad_oraculo.py`.

---

## 3. Cómo Reproducir la Validación

### A. Corrida Local con Oráculo y Diagnósticos
```powershell
python tools/paridad_oraculo.py `
  --indicador avolclusterpoi `
  --oraculo data/nt8_oracles/avolcluster_v05_NQ0626_120t_20260407_20260612_v2.csv `
  --parquet data/canonical/NQ_06-26_ticks.parquet `
  --chart-tz America/Argentina/Buenos_Aires `
  --barras tick:120 `
  --sesiones-warmup 20 `
  --barprofile data/nt8_oracles/avolcluster_v05_NQ0626_120t_BARPROFILE_20260902.csv `
  --diag-blocks data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_BLOCKS_20260902.csv `
  --out reporte_paridad.json
```

### B. Corrida en Kaggle (Kernel Inmutable)
- Runner canónico: `notebooks/kaggle/avolclusterpoi_parity_nq0626_runner.py`
- Kernel Kaggle: `nicolasbuttaro/avolclusterpoi-parity-nq0626`
- Versión 21 ejecutada y completa: emite 201/203 zonas emparejadas con `0 ticks` de diferencia geométrica y `0 ms` de diferencia temporal.

### C. Simulador y Visores de Gráficos Locales
- **Visor interactivo con backend en vivo:**
  ```powershell
  python tools/visor_server.py --port 8777
  ```
  Acceso en navegador: `http://127.0.0.1:8777`
- **Visor estático de corridas previas:**
  ```powershell
  python -m http.server -d runs 8778
  ```
  Acceso en navegador: `http://127.0.0.1:8778`

---

## 4. Próximos Pasos y Restricciones Estrictas

1. **NO abrir outcomes ni barridos de P&L:**
   - La certificación de paridad es una condición necesaria pero no suficiente para ejecutar un sweep económico.
   - Todo barrido de parámetros u optimización requiere:
     - Manifiesto de campaña formal;
     - Declaración del número efectivo de hipótesis;
     - Preservación del holdout (`2026-07-01 → 2026-12-31`);
     - Aprobación explícita de Nico.
2. **Si se trabaja en otra rama o worktree:**
   - Mantener la regla de un solo escritor por directorio (`AGENTS.md`).
   - Consultar `docs/BRANCH_REGISTRY_2026-08-24.md` antes de mergear o alterar cualquier rama.

---

## Aporte al referente

Queda formalizada la transferencia completa de la paridad de `aVolClusterPOI` v0.5. El siguiente auditor encuentra el código fuente verificado, los oráculos trazables con SHA-256, los visores locales documentados y los resultados de paridad certificados sin comprometer el firewall de outcomes.
