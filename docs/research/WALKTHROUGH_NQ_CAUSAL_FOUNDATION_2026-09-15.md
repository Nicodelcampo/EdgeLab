# Walkthrough: Cierre de la Base Causal NQ v1

Se ha completado la ejecución técnica de las fases preliminares, de inventario, compuerta de elegibilidad de sesiones, reproducción del look-ahead y memo de decisión metodológica sobre la rama de trabajo `work/nq-causal-foundation-v1-20260915`.

---

## 1. Integridad y Seguridad de Datos

- **Rama creada:** `work/nq-causal-foundation-v1-20260915` (ramificada desde `foundation/f0b-compatibility-probe`).
- **Holdout (2026-07-01 $\rightarrow$ 2026-12-31):** Intacto. Cero filas leídas en holdout.
- **Outcomes y P&L:** Cerrados y no tocados.
- **Archivos existentes:** Ninguna base SQLite, CSV ni manifiesto previo fue borrado, renombrado ni sobrescrito.

---

## 2. Entregables Generados

### Entregable 1: Informe de Inventario de Datos
* **Archivo:** `docs/research/INFORME_INVENTARIO_DATOS_NQ0626_2026-09-15.md`
* **Parquet Local:** `data/nt8/NQ_parquet/NQ_06-26_ticks.parquet`
  * Tamaño: `675,240,935` bytes (**Exacto**)
  * SHA-256: `3de249b9b8d8ada01c5b485aa893ccdf1315ae3f7bbebcaf72024de12e1b25f6` (**Exacto $\rightarrow$ PASS**)
  * Ticks: `34,203,535`
  * Rango: `2026-03-12 03:02:25 UTC` a `2026-06-18 13:29:55 UTC`
  * Cobertura NT8: `C:\Users\Usuario\Documents\NinjaTrader 8\db\tick\NQ 06-26` cubre del 3 al 11 de junio de 2026 en su totalidad.

### Entregable 2: Manifiesto del Oráculo NT8
* **Archivo:** `docs/research/MANIFIESTO_ORACULO_NT8_NQ0626_2026-09-15.json`
* **Especificación:**
  * Instrumento: `NQ 06-26`
  * Fechas: `2026-06-03` a `2026-06-11` inclusive.
  * Chart: `25 ticks`.
  * Parámetros: Defaults del indicador `HFTClusterZonesNQ` v2.0.0 (hash: `b9437f3f4b4045d45f3b01f91a19f347ec6de7615e46b2ddaf24943472ebef07`), configurando:
    * `SoloLogEnVivo = false`
    * `EnableDbLogging = true`
    * `DbPath = C:\LoggerHFT\data\oraculo_clusters_NQ0626_20260915.sqlite`
    * `EnableEventCsv = true`
    * `EventLogPath = C:\LoggerHFT\data\oraculo_clusters_NQ0626_20260915.csv`
  * Declaración explícita de semántica: `historical_realtime_semantics = DIVERGENT`, `historical_double_count = true`.

### Entregables 6 y 7: Compuerta Causal de Sesiones (`NQ_SESSION_ELIGIBILITY_GATE_V1`)
* **Código:** `edgelab/data/nq_session_gate.py`
* **Tests unitarios:** `tests/data/test_nq_session_gate.py`
* **Resultado de pruebas:** 12 tests pasados exitosamente.
  * `2026-05-25` (Memorial Day) $\rightarrow$ `FAIL` con motivo explícito `EARLY_CLOSE_HOLIDAY_Memorial Day`.
  * `2026-06-15` NQ 06-26 $\rightarrow$ `FAIL` (post-roll, 26.9% del volumen mediano).
  * `2026-06-16` NQ 06-26 $\rightarrow$ `FAIL` (post-roll, 13.7% del volumen mediano).
  * `2026-06-03` a `2026-06-11` (las 7 sesiones pre-roll) $\rightarrow$ `PASS` (volumen entre 113% y 192% de la mediana).
  * Fin de semana $\rightarrow$ `FAIL`.
  * Fecha desconocida fuera de calendario $\rightarrow$ `ABSTAIN` (nunca `PASS` automático).

### Entregables 8 y 9: Look-Ahead en Runners
* **Tests:** `tests/research/test_lookahead_runners.py` (5 tests pasados exitosamente). Demuestran que entregar la zona al inicio (`idx_start // ticks_por_barra`) inyecta información de ticks posteriores a esa barra, ya que las características completas (`total_vol`, `cvd`, bordes) recién existen al finalizar el streak (`idx_end // ticks_por_barra`).
* **Parche propuesto:** `patches/runners_zone_delivery_timing.patch`. Parche git-compatible aislado que aplica `barra_de_entrega` y `barra_de_nacimiento` sin aplicarlo sobre la rama viva ni volver a correr hipótesis.

### Entregable 10: Memo de Decisión Histórico vs Realtime
* **Archivo:** `docs/research/MEMO_DECISION_HISTORICO_VS_REALTIME_2026-09-15.md`
* **Conclusión:** Se recomienda la **Alternativa A** (adoptar semántica en tiempo real desactivando el consumo adicional por barra cuando existe la serie de ticks) para preservar la transferibilidad a live trading y la coherencia física causal. Se mantiene el `.cs` intacto a la espera de la decisión explícita de Nico.

---

## 3. Próximo Paso (Fase 2 y 3)

Nico debe abrir NinjaTrader 8 y exportar el oráculo con la configuración indicada:
* Gráfico: `NQ 06-26`, `25 ticks`, sesiones del `2026-06-03` al `2026-06-11`.
* Indicador: `HFTClusterZonesNQ` con `SoloLogEnVivo=false`, `EnableDbLogging=true`, `DbPath=C:\LoggerHFT\data\oraculo_clusters_NQ0626_20260915.sqlite`, `EnableEventCsv=true`, `EventLogPath=C:\LoggerHFT\data\oraculo_clusters_NQ0626_20260915.csv`.

Una vez exportado, ejecutaremos inmediatamente:
```powershell
python tools/paridad_hftclusterzones.py --instrumento "NQ 06-26" --parquet "data/nt8/NQ_parquet/NQ_06-26_ticks.parquet" --db "C:\LoggerHFT\data\oraculo_clusters_NQ0626_20260915.sqlite" --out "docs/research/paridad_clusters_nq_20260915"
```
para emitir el informe de paridad final.
