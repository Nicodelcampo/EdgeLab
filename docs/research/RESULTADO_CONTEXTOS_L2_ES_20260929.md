# Resultado contextos L2 ES (4 climas) — STOP por inestabilidad de semillas (2026-09-29)

Protocolo `PROTOCOLO_CONTEXTOS_L2_ES_MES_MNQ_20260929.md` + enmienda 1 (carga de archivos solapados). 48 sesiones NT8
(16 de entrenamiento, 32 de evaluación). Target-free. Reporte: `l2_contexts_ES/ES_gate_report_STOP.json`.

| Compuerta | Valor | Umbral | |
|---|---|---|---|
| Cobertura (evaluación) | 43.238/43.238 = 1,00 | ≥ 0,99 | PASS |
| Acuerdo entre semillas global | 0,614 | ≥ 0,80 | **STOP** |
| Por estado: calm / normal / volatile | 0,669 / 0,208 / 0,051 | ≥ 0,80 | **STOP** |
| Sólo-hora | 0,877 (mayoría 0,878) | < 0,90 | PASS |
| Máx. concentración en 2 h | normal 0,50 | ≤ 0,80 | PASS |

Evaluación: calm 37.960 min (mediana de racha 25,5), toxic 4.666 (7), volatile 505 (5), normal 107 (3).
**Veredicto: ES sin climas.** No se cambian parámetros ni split después del reporte. El STOP invalida esta configuración
(HMM 3 estados + overlay tóxico sobre ES jul–sep); que ES tenga dos regímenes reales (p. ej. calm/toxic) sería una
hipótesis nueva con validación propia — no se infiere de que normal/volatile hayan quedado casi vacíos.

Etiquetas de diagnóstico (NO climas validados, no filtrar operaciones con ellas), pedidas por el auditor:
`l2_contexts_ES/ES_labels_utc_STOP_diagnostico.parquet` (minuto a minuto, UTC y ART, entrenamiento y evaluación) y
`l2_contexts_ES/ES_intervalos_por_estado_STOP_diagnostico.csv` (1.509 rachas con sesión, estado, inicio/fin en hora de
Chicago, minutos, flag de evaluación). Datos NT8 propios; nada de Lucid.
Cobertura del dato: 11/08 (1.102 min elegibles, grabación incompleta) y 12/08 (1.021).
