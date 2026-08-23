# GATE — Checklist de integración en EdgeLab

**model_id congelado:** `gate_tf_causal_bal_v2_feat10_sticky90_vpin055`  
**config_sha256:** ver `gate_model_id_frozen.json`  
**Fecha:** 2026-08-23

---

## A. Gobernanza de repo

- [ ] Rama dedicada (ej. `research/gate-regime-context`) — no mezclar con fix de NT8
- [ ] **Prohibido** modificar `.cs` del indicador para meter régimen
- [ ] Patrón fijo: export NT8 → labels GATE offline → trial
- [ ] Holdout del lab **intacto**
- [ ] Todo artefacto lleva `run_id`, `seed`, `model_id`, `commit`, `schema_version`

## B. Pasos 1–4 (pre-outcomes)

- [ ] **Paso 1:** labels reales con `gate_adapter.label_events_at_t0` y `as_of_ok`
- [ ] **Paso 2:** target-free en datos reales
  - [ ] veredicto corr(ancho) = `OK_LOW_CORR`
  - [ ] cobertura sesiones/celda reportada
- [ ] **Paso 3:** `H-ES-CTX-3_PREREGISTRO.md` → `PREREGISTERED_READY_TO_RUN` (OK Nico + estimando primario fijado)
- [ ] **Paso 4:** incremental vs `pct_rv` solo **después** de congelar CTX-3

## C. model_id (Paso 5)

- [x] Config inmutable en `gate_model_id_frozen.json`
- [x] Features (10), sticky, VPIN, causal-only, focal balanceado
- [x] Política: cualquier cambio de hiperparámetro → **nuevo** `model_id`
- [ ] Hash verificado en CI o script local antes de cada corrida formal

## D. Producción de labels

- [ ] Detector corre solo sobre barras con features **causales**
- [ ] Atención bi-dir **prohibida** en path de labels (solo cota offline histórica)
- [ ] Fail-closed si falta barra ≤ t0
- [ ] Export parquet/JSONL conforme `gate_context_schema_v1`

## E. Cuando el régimen gatea trades (opcional, más adelante)

- [ ] Señal bajo contrato EdgeLab (`idx`, `dirs` solo pasado)
- [ ] Costos ES reales
- [ ] Gauntlet: MCPT, PBO/CSCV, DSR, walk-forward
- [ ] No declarar edge solo por CTX-3 positivo

## F. Definición de “complemento aplicable”

GATE es complemento aplicable cuando:

1. Produce labels versionados sobre eventos reales del lab  
2. Pasa target-free (corr ancho + cobertura)  
3. Entra a un trial pre-registrado (CTX-3)  
4. (Opcional) Demuestra valor incremental vs `pct_rv`  

Hasta 1–3 en datos reales: prototipo alineado, no aún complemento en producción de research.

---

## Archivos del roadmap

| Archivo | Paso |
|---------|------|
| `GATE_ROADMAP.md` | Índice |
| `gate_context_schema_v1.json` + `gate_adapter.py` | 1 |
| `gate_target_free.py` | 2 |
| `H-ES-CTX-3_PREREGISTRO.md` | 3 |
| `gate_incremental_vs_pctrv.py` | 4 |
| `gate_model_id_frozen.json` + este checklist | 5 |
